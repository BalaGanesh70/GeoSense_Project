from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from backend.config import OPENAI_API_KEY
import json
from typing import Any

llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, temperature=0.3)

CORE_HAZARDS = ["Cyclone", "Rainfall", "Landslide", "Deforestation", "Earthquake"]

prompt = PromptTemplate(
    input_variables=["data"],
    template="""
    You are a disaster analysis expert.

    You will receive an input JSON with:
    - regions: list of objects with keys zone and damage
    - context: a string with retrieved background knowledge

    Input JSON:
    {data}

    Return ONLY valid JSON (no markdown, no commentary) with these keys:
    disaster_name (string)
    affected_regions (list of objects with keys zone and damage_percent)
    reasons (list of objects with keys title and description)
    precautions (object with keys before, during, after; each is a list of strings)
    future_impact (list of objects with keys zone and risk_level)
    previous_prevention (list of strings)
    summary (string)
    core_disaster_snapshot (object): must contain exactly these five keys as property names:
    Cyclone, Rainfall, Landslide, Deforestation, Earthquake.
    Each property value must be an object with:
    zone_impacts: array of objects with zone and impact_percent (number 0-100).
    Include one entry per zone from the input regions, same zone names, ordered as in input.
    impact_percent means inferred relative contribution or exposure of THAT hazard type in THAT zone
    (higher where that hazard is more likely to dominate damage for that zone).
    plot_notes: array of exactly 4 strings for that hazard.
    Each string must contain at least two lines: use a newline between line 1 and line 2 inside the string.
    Point 1: how to read the bar chart (tallest zones and what that implies).
    Point 2: how to read the donut (percent shares and what they sum to).
    Point 3: compare two zones or rank them using both plots.
    Point 4: caveats, uncertainty, or what to verify with local data or imagery.
    """
)


def _extract_first_json_object(text: str) -> Any:
    """
    Best-effort extraction of the first JSON object from an LLM response.
    """
    if not text:
        raise ValueError("Empty LLM response.")
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Could not find JSON object in LLM response.")
    snippet = text[start : end + 1]
    return json.loads(snippet)


def _four_multiline_plot_notes(notes: Any, fallback_four: list[str]) -> list[str]:
    """Ensure exactly 4 plot note strings; pad from fallback. Each should contain two lines when possible."""
    raw: list[str] = []
    if isinstance(notes, list):
        raw = [str(x).strip() for x in notes if str(x).strip()]
    out: list[str] = []
    for i in range(4):
        if i < len(raw):
            out.append(raw[i])
        elif i < len(fallback_four):
            out.append(fallback_four[i])
        else:
            out.append(
                "This point summarizes chart context.\n"
                "Refer to the bar and donut figures for numeric values."
            )
    return out[:4]


def _default_core_disaster_snapshot(regions: list) -> dict:
    """Deterministic hazard–zone view derived from zone damage when the LLM omits snapshot."""
    out = {}
    zones = [str(r.get("zone", "")) for r in regions if isinstance(r, dict)]
    vals = [float(r.get("damage", 0) or 0) for r in regions if isinstance(r, dict)]
    for i, hazard in enumerate(CORE_HAZARDS):
        # Slight per-hazard shaping so plots differ while staying tied to observed zone damage.
        phase = 0.72 + (i * 0.07) % 0.36
        zi = []
        for z, v in zip(zones, vals):
            p = min(100.0, max(0.0, v * phase))
            zi.append({"zone": z, "impact_percent": round(p, 1)})
        out[hazard] = {
            "zone_impacts": zi,
            "plot_notes": [
                f"The bar chart ranks zones by inferred {hazard} impact percentage (0–100%).\n"
                f"Taller bars mean this hazard is modeled as relatively stronger in that zone for the current image.",
                f"The donut shows each zone’s share of total modeled {hazard} impact across all zones.\n"
                f"Slice size matches the bar values proportionally when all zones are included.",
                f"Compare the highest bar to the largest slice: they should refer to the same dominant zone.\n"
                f"Zones with similar bar heights will have similar donut shares.",
                f"These values are inferred from the pipeline and context, not ground-truth field measurements.\n"
                f"Validate with local reports, weather data, and higher-resolution hazard layers when available.",
            ],
        }
    return out


def _merge_core_disaster_snapshot(raw: Any, regions: list) -> dict:
    base = _default_core_disaster_snapshot(regions)
    if not isinstance(raw, dict):
        return base
    merged = dict(base)
    for hazard in CORE_HAZARDS:
        block = raw.get(hazard) or raw.get(hazard.lower())
        if not isinstance(block, dict):
            continue
        zi = block.get("zone_impacts") or block.get("zones")
        notes = block.get("plot_notes") or block.get("insights") or block.get("notes")
        zone_names = [str(r.get("zone", "")) for r in regions if isinstance(r, dict)]
        if isinstance(zi, list) and zi:
            by_zone = {}
            for item in zi:
                if not isinstance(item, dict):
                    continue
                z = str(item.get("zone", ""))
                try:
                    p = float(item.get("impact_percent", item.get("percent", 0)))
                except (TypeError, ValueError):
                    p = 0.0
                by_zone[z] = min(100.0, max(0.0, p))
            rebuilt = []
            for z in zone_names:
                rebuilt.append({"zone": z, "impact_percent": round(by_zone.get(z, 0.0), 1)})
            if rebuilt:
                merged[hazard] = {**merged[hazard], "zone_impacts": rebuilt}
        merged[hazard]["plot_notes"] = _four_multiline_plot_notes(
            notes if isinstance(notes, list) else [],
            base[hazard]["plot_notes"],
        )
    return merged


def generate_report(data: dict) -> dict:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set. Set it in your environment variables.")
    formatted_prompt = prompt.format(data=json.dumps(data, ensure_ascii=False))
    response = llm.invoke(formatted_prompt)
    content = getattr(response, "content", str(response))
    regions = data.get("regions", []) if isinstance(data, dict) else []
    try:
        parsed = _extract_first_json_object(content)
        if isinstance(parsed, dict):
            parsed["core_disaster_snapshot"] = _merge_core_disaster_snapshot(
                parsed.get("core_disaster_snapshot"), regions
            )
        return parsed
    except Exception:
        # Fallback: keep the app running even if the model output isn't strict JSON.
        return {
            "disaster_name": "Unknown disaster",
            "affected_regions": [
                {"zone": r.get("zone", ""), "damage_percent": r.get("damage", 0)}
                for r in regions
                if isinstance(r, dict)
            ],
            "reasons": [],
            "precautions": {"before": [], "during": [], "after": []},
            "future_impact": [],
            "previous_prevention": [],
            "summary": content[:1200],
            "raw_report": content,
            "core_disaster_snapshot": _default_core_disaster_snapshot(regions),
        }


def answer_question(question: str, context: dict) -> str:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is not set. Set it in your environment variables.")

    chat_prompt = PromptTemplate(
        input_variables=["question", "context"],
        template="""
You are a helpful disaster-response assistant.

Use the provided analysis context JSON to answer the user question.
If the answer is not present in the context, say you don't have enough information.

Context (JSON):
{context}

Question:
{question}

Answer:
""",
    )

    formatted = chat_prompt.format(
        question=question,
        context=json.dumps(context, ensure_ascii=False),
    )
    response = llm.invoke(formatted)
    content = getattr(response, "content", str(response))
    return content.strip()
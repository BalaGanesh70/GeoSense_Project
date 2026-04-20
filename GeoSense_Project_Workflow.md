# GeoSense Project Workflow (End-to-End)

## 1) High-level Overview
GeoSense is an end-to-end disaster analysis app with:
- A **Streamlit frontend** for uploading an image, viewing results, and asking questions in an in-page Q&A UI.
- A **FastAPI backend** that:
  - Converts the uploaded image into **4 analysis zones** with a per-zone damage score (demo logic).
  - Uses **RAG (FAISS)** to fetch relevant background knowledge.
  - Uses an **LLM (OpenAI via LangChain)** to generate a structured disaster report in **JSON**.
- A **/chat** endpoint that answers follow-up questions using the provided context JSON.

The frontend stores the backend response in `st.session_state.analysis_data` so the report can be explored across multiple pages without re-running the pipeline.

---

## 2) Tech Stack

### Frontend
- **Streamlit** (multi-page)
- **Plotly** (interactive charts)
- **OpenCV + NumPy** (image enhancement / preprocessing)
- **Pytesseract** + **difflib** (OCR + fuzzy matching for Indian states/UTs from green labels)
- **requests** (calls backend `/analyze` and `/chat`)
- **Optional**: pandas (used if available for some tables/frames)

### Backend
- **FastAPI** (API server)
- **LangChain** + **LangChain OpenAI**:
  - `ChatOpenAI` for report generation and chat answering
  - `OpenAIEmbeddings` + **FAISS** for retrieval
- **OpenAI API** (LLM + embeddings)
- **OpenCV + NumPy** (image processing demo)
- **(Defined but currently not used in routes)** SQLAlchemy + Postgres (database model exists)

---

## 3) Repository Components

### Frontend
- `frontend/app.py`: upload + OCR setup + “Analyze” button + navigation to result pages
- `frontend/pages/`
  - `1_Affected_Regions.py`
  - `2_Reasons.py`
  - `4_Precautions.py`
  - `5_Recovery.py`
  - `6_Future_Impact.py`
- `frontend/report_common.py`: shared UI + chat helpers (in-page Q&A pattern, plot helpers, zone mapping constants)

### Backend
- `backend/main.py`: FastAPI app + router mount
- `backend/routes/analysis.py`: `/analyze` and `/chat` endpoints
- `backend/services/`
  - `cv_service.py`: image -> 4 zones with damage scores (demo logic)
  - `rag_service.py`: FAISS retrieval for background knowledge
  - `llm_service.py`: structured JSON report generation and chat answering
  - `langgraph_flow.py`: orchestration/pipeline (calls CV -> RAG -> LLM)
- `backend/config.py`: `OPENAI_API_KEY`, `DATABASE_URL`

---

## 4) End-to-End Workflow (Step-by-step)

### Step A: User opens the app (frontend)
Run:
```bash
streamlit run app.py
```
From inside `frontend/`.

### Step B: User uploads a satellite image
- UI element: `st.file_uploader("Upload Satellite Image")`
- Stored in session:
  - `st.session_state.upload_bytes`
  - `st.session_state.upload_name`

Optional OCR/preview:
- Toggle: `Convert to clearer human-view style before analysis`
  - Enhancement uses CLAHE + filtering + sharpening
- Buttons:
  - “Detect States in Green Boxes”
  - “Show India States/UTs Table”

### Step C: User clicks **Analyze**
UI element:
```python
requests.post("http://localhost:8000/analyze", files=files, timeout=120)
```
Backend call sends the image bytes (as `multipart/form-data`).

When the response returns successfully:
- Stored in session:
  - `st.session_state.analysis_data = data`
  - `st.session_state.view = "results"`

From this point:
- The user navigates to pages via Streamlit’s sidebar/page links.

---

## 5) Backend Pipeline Details

### Endpoint: `POST /analyze`
**Input**
- `file: UploadFile` (image bytes)

**Processing pipeline**
1. `run_pipeline(image_bytes)` (from `backend/services/langgraph_flow.py`)
2. `detect_change(image_bytes)` (from `backend/services/cv_service.py`)
   - Splits the image into **4 quadrants**
   - Produces zones:
     - `Zone-00`, `Zone-01`, `Zone-10`, `Zone-11`
   - Assigns a random `damage` score for each zone (demo behavior)
3. RAG retrieval:
   - Builds a query like: `Disaster analysis: {sorted_regions}`
   - `rag_service.get_context(query)` returns concatenated relevant snippets from FAISS
4. LLM report generation:
   - `llm_service.generate_report({ regions, context })`
   - LLM output must be **ONLY valid JSON** with specific keys

**Backend output**
The `/analyze` response is the pipeline output:
- `regions`
- `context`
- `report` (structured JSON)

The frontend later uses:
- `analysis_data.get("report", {})`
- `analysis_data.get("regions", [])`

---

### Endpoint: `POST /chat`
**Input**
- Request body:
  - `question: str`
  - `context: Dict[str, Any]`

The frontend uses `report_common.call_chat()` which sends:
- `context = {"analysis_data": <full analysis_data>, "tab_key": <page key>}`
- question is typically:
  - the user’s typed question or selected suggested question
  - plus extra page context text (`context_text`) when using in-page Q&A helpers

**Processing**
- `llm_service.answer_question(question, context)`:
  - uses a second prompt that includes the serialized `context` JSON
  - returns the LLM text answer

**Output**
- JSON with:
  - `{ "answer": "<assistant response>" }`

---

## 6) Structured Final Output Schema (LLM Report)

The LLM (`backend/services/llm_service.py`) is instructed to output JSON with at least these keys:

- `disaster_name: string`
- `affected_regions: list of { zone: string, damage_percent: number 0-100 }`
- `reasons: list of { title: string, description: string }`
- `precautions: { before: list[str], during: list[str], after: list[str] }`
- `future_impact: list of { zone: string, risk_level: string }`
- `previous_prevention: list[str]`
- `summary: string`
- `core_disaster_snapshot`:
  - exactly these hazard keys as property names:
    - `Cyclone`, `Rainfall`, `Landslide`, `Deforestation`, `Earthquake`
  - each hazard value contains:
    - `zone_impacts: [{ zone: string, impact_percent: number }]`
    - `plot_notes: [string, string, string, string]`
      - each should include newline between line 1 and line 2

If the model fails to return strict JSON, the backend falls back to a deterministic report with empty lists and default `core_disaster_snapshot`.

---

## 7) Pages: Inputs, Features, and Outputs

### Page 1: `1_Affected_Regions.py`
**Purpose**
- Show zone-wise damage charts and zone/state mapping.
- Provide an in-page Q&A about the selected zone.

**Inputs**
- Uses `get_report()` from `frontend/report_common.py`
  - `analysis_data` from session
  - `regions` from analysis_data

**Key UI features**
- Zone screenshot previews (Zone-00/01/10/11)
- Zone-wise damage visualizations:
  - bar
  - donut
  - radar
  - gauges
- “Zone ↔ state linkage” section:
  - grouped states/UTs per model zone
  - download as CSV
- Zone selector:
  - shows a larger cropped screenshot for the selected zone
  - (optional checkboxes exist for states/UTs)
- In-page Q&A:
  - same pattern as Precautions page:
    - suggested questions
    - typed question input
    - orange “Click here to get the answer” button
    - chat history

**Output**
- Charts + linkage info and a Q&A answer string returned from backend `/chat`.

---

### Page 2: `2_Reasons.py`
**Purpose**
- Show the “Core Disaster Snapshot” and a disaster comparison infographic.

**Inputs**
- `report` and `regions` from `get_report()`

**Key UI features**
- Hazard selector inside “Core Disaster Snapshot”
- Plotly hazard charts with plot-note guidance
- “Disaster Type Comparison” infographic (Plotly radial + side tiles)

**Chat**
- Chat is removed from this page (by your instruction).

**Output**
- Visualizations only.

---

### Page 4: `4_Precautions.py`
**Purpose**
- Stage-based precautions Q&A (Before / During / After) using an in-page chat pattern.

**Inputs**
- `report.precautions` provides:
  - `before`, `during`, `after` lists
- Selectors:
  - disaster dropdown: Cyclone, Earthquake, Flood, Landslide
  - zone screenshot strip (fixed 4 images)
  - stage radio: Before/During/After

**Key UI features**
- Suggested questions depend on stage:
  - `_possible_questions(disaster, stage)` returns stage-specific queries
- Typed question input
- Orange action button:
  - “Click here to get the answer”
- Chat history stored in `st.session_state.chat_messages[chat_key]`

**Answer formatting**
- The prompt instructs the LLM to output:
  - pointwise format
  - YouTube link
  - reference links
  - with required point counts and “no emojis”

**Output**
- Each Q&A answer is displayed in markdown and saved to chat history.

---

### Page 5: `5_Recovery.py`
**Purpose**
- Visual demo of recovery timeline + death-cause breakdown with in-page Q&A.

**Inputs**
- UI selectors:
  - disaster selector
  - recovery window buttons:
    - `0-2`, `2-5`, `5-10`
  - “Disaster for death-cause split”
  - “Select death-cause scenario”

**Key UI features**
- Plotly timeline road with milestone markers
- Year detail cards:
  - injured / died / recovered
  - small bar chart per year
- Death-cause flow analysis:
  - time variation bar chart for the chosen cause
  - center donut “count”
  - right bar chart comparing causes

**Chat**
- In-page Q&A is included using the same shared helper pattern.

**Output**
- Visualizations + a `/chat` answer string based on the page’s context.

---

### Page 6: `6_Future_Impact.py`
**Purpose**
- “Future impact” projection by disaster + zone, plus a roadmap timeline.

**Inputs**
- Selectors:
  - disaster dropdown
  - zone dropdown (Zone-00/01/10/11)
- Risk hint is extracted from `report["future_impact"]` by zone.

**Key UI features**
- Zone screenshot strip
- Precautions and post-cautions shown as:
  - 5 disaster+zone-specific lines per box
  - dropdown lists that display all 5 lines
- Future projection text:
  - “0 to 2 years”
  - “2 to 5 years”
- Roadmap visualization:
  - shows via a button (“Show road timeline”)
  - horizontal road-style Plotly chart
- Full-width two-column “key points” section below the roadmap

**Chat**
- In-page Q&A included using the shared helper.

**Output**
- Zone/disaster-specific text + roadmap + Q&A answers.

---

## 8) Inputs and Final Outputs (Quick Reference)

### Frontend inputs
- `Upload Satellite Image` (image file)
- OCR setup:
  - optional enhanced preview
  - optional green box state detection (OCR + fuzzy matching)
- User selects:
  - disaster type
  - zone
  - stage (Precautions)
  - time window (Recovery)

### Backend inputs
- `POST /analyze`: uploaded image bytes
- `POST /chat`: `{ question, context }`

### Final outputs
- `POST /analyze` returns:
  - `regions`, `context`, `report`
- Report JSON contains:
  - disaster name, reasons, precautions, future impact, previous prevention, summary, and core snapshot data
- `POST /chat` returns:
  - `{ "answer": "<text response>" }`

---

## 9) Run/Deploy Notes
- Backend must be running for the app to work:
  - backend listens on `http://localhost:8000`
  - endpoints used: `/analyze` and `/chat`
- Streamlit frontend stores analysis in `st.session_state` so navigation across pages works without re-analysis.


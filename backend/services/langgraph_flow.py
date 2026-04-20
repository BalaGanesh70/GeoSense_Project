from backend.services.cv_service import detect_change
from backend.services.llm_service import generate_report
from backend.services.rag_service import get_context

def run_pipeline(image_bytes):
    regions = detect_change(image_bytes)

    sorted_regions = sorted(regions, key=lambda x: x['damage'], reverse=True)

    # Create query for RAG
    query = f"Disaster analysis: {sorted_regions}"

    context = get_context(query)

    # Combine context with data
    final_input = {
        "regions": sorted_regions,
        "context": context
    }

    report = generate_report(final_input)

    return {
        "regions": sorted_regions,
        "context": context,
        "report": report
    }
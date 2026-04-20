from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.services.langgraph_flow import run_pipeline
from backend.services.llm_service import answer_question
from pydantic import BaseModel
from typing import Any, Dict

router = APIRouter()

class ChatRequest(BaseModel):
    question: str
    context: Dict[str, Any]

@router.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty upload.")

    try:
        result = run_pipeline(content)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(req: ChatRequest):
    try:
        answer = answer_question(req.question, req.context)
        return {"answer": answer}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

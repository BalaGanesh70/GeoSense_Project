from pydantic import BaseModel

class AnalysisResponse(BaseModel):
    result: str

from sqlalchemy import Column, Integer, String, Text
from backend.database import Base

class Analysis(Base):
    __tablename__ = "analysis"

    id = Column(Integer, primary_key=True, index=True)
    result = Column(Text)
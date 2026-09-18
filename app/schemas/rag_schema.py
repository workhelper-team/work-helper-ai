"""순수 RAG 검색 테스트 및 벡터 검색 전용 스키마."""

from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.consultation_schema import LegalReference

class RAGSearchRequest(BaseModel):
    query: str = Field(..., description="검색 쿼리")
    top_k: int = Field(3, description="반환 청크 개수")


class RAGSearchResponse(BaseModel):
    query: str
    results: List[LegalReference]
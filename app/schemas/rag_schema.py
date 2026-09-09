from typing import List, Optional

from pydantic import BaseModel, Field


class RAGQueryRequest(BaseModel):
    """법령/판례 검색 질의 요청 스키마."""

    query: str = Field(..., description="검색하고자 하는 자연어 질의")
    top_k: int = Field(default=5, ge=1, le=50, description="반환할 최대 검색 결과 수")
    collection: Optional[str] = Field(
        default=None, description="검색 대상 Vector DB 컬렉션 (미지정 시 기본 컬렉션 사용)"
    )


class RAGSearchResultItem(BaseModel):
    """개별 검색 결과 항목."""

    title: str = Field(..., description="법령/판례 제목")
    content: str = Field(..., description="관련 본문 내용 발췌")
    source: Optional[str] = Field(default=None, description="출처 (예: 법령명, 판례번호)")
    score: float = Field(..., description="유사도 점수")


class RAGQueryResponse(BaseModel):
    """법령/판례 검색 결과 응답 스키마."""

    query: str
    results: List[RAGSearchResultItem] = Field(default_factory=list)

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

class ConsultationMessage(BaseModel):
    """이전 대화 이력 메시지 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    role: str = Field(..., description="메시지 발화 주체 (user 또는 assistant)")
    content: str = Field(..., description="메시지 내용")


class LegalReference(BaseModel):
    """답변의 근거로 사용된 법률 자료 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    precedent: str = Field(..., description="판례 구분 (예: 근로기준법)")
    article: Optional[str] = Field(None, description="조항 번호 또는 판례 일련번호 (예: 제55조)")
    content: str = Field(..., description="인용된 법률 조항 원문 또는 요약")


class StructuredConsultationResult(BaseModel):
    """구조화된 법률 분석 결과 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    issues: List[str] = Field(default_factory=list, description="도출된 핵심 노동법 쟁점 목록")
    references: List[LegalReference] = Field(default_factory=list, description="근거 법령 및 판례 목록")
    follow_up_questions: List[str] = Field(default_factory=list, description="추가 사실관계 확인 질문")
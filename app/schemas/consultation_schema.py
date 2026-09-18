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
    law: str = Field(..., description="법령명 또는 판례 구분 (예: 근로기준법)")
    article: Optional[str] = Field(None, description="조항 번호 또는 판례 일련번호 (예: 제55조)")
    content: str = Field(..., description="인용된 법률 조항 원문 또는 요약")


class StructuredConsultationResult(BaseModel):
    """구조화된 법률 분석 결과 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    issues: List[str] = Field(default_factory=list, description="도출된 핵심 노동법 쟁점 목록")
    references: List[LegalReference] = Field(default_factory=list, description="근거 법령 및 판례 목록")
    follow_up_questions: List[str] = Field(default_factory=list, description="추가 사실관계 확인 질문")


class ConsultationRequest(BaseModel):
    """INT-AI-001 노동법 상담 요청 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    case_context: Optional[str] = Field(None, description="사건 기본 맥락 정보")
    chat_history: List[ConsultationMessage] = Field(default_factory=list, description="이전 대화 메시지 이력")
    question: str = Field(..., description="사용자 질문 또는 상황 설명")


class ConsultationResponse(BaseModel):
    """INT-AI-001 노동법 상담 응답 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    answer: str = Field(..., description="AI 법률 상담 종합 답변")
    structured_result: StructuredConsultationResult = Field(..., description="구조화된 쟁점/근거/질문 결과")
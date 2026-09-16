from typing import List, Optional
from pydantic import BaseModel, Field


class ConsultationRequest(BaseModel):
    """AI 법률 상담 요청 DTO"""
    question: str = Field(
        ..., 
        description="사용자의 자연어 질문 또는 노동 사건 상황 설명",
        examples=["주휴수당을 3개월째 못 받았는데 받을 수 있는 기준이 어떻게 되나요?"]
    )
    case_id: Optional[str] = Field(
        None, 
        description="연계된 사건 식별자 (Spring Boot에서 관리하는 사건 ID)"
    )


class LegalReference(BaseModel):
    """답변의 근거로 사용된 법률 자료 DTO"""
    law: str = Field(..., description="법령명 또는 판례 구분 (예: 근로기준법, 대법원 판례)")
    article: Optional[str] = Field(None, description="조항 번호 또는 판례 일련번호 (예: 제55조)")
    content: str = Field(..., description="인용된 법률 조항 원문 또는 요약")


class ConsultationResponse(BaseModel):
    """AI 법률 상담 구조화 응답 DTO"""
    answer: str = Field(..., description="AI 법률 상담 종합 답변")
    issues: List[str] = Field(
        default_factory=list, 
        description="상황에서 도출된 핵심 노동법 쟁점 목록"
    )
    references: List[LegalReference] = Field(
        default_factory=list, 
        description="판단 근거로 사용된 법조문 및 판례 목록"
    )
    follow_up_questions: List[str] = Field(
        default_factory=list, 
        description="정확한 법률 검토를 위해 사용자에게 추가로 확인해야 할 사실관계 질문"
    )
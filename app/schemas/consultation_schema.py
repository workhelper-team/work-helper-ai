from typing import List
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

## Field 객체 파라미터 설명
# ... : 값이 필수로 존재해야 함 -> 값이 없으면 ValidataionError 발생
# None : 값이 없어도 됨

class ConsultationMessage(BaseModel):
    """이전 대화 이력 메시지 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    role: str = Field(..., description="메시지 발화 주체 (user 또는 assistant)")
    content: str = Field(..., description="메시지 내용")

class Precedents(BaseModel):
    """답변과 유사한 판례 데이터 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    case_number: str = Field(..., description="사건번호 (예: 2024도20470)")
    case_name: str = Field(..., description="사건명 (예: 근로기준법위반)")
    court_name: str = Field(..., description="법원명 (예: 대법원, 서울고등법원 등)") 
    judgment_date: str = Field(None, description="선고일자 (예: 2024-11-12)")
    judgment_type: str = Field(None, description="판결 유형 (판결, 결정 등 비어있을 경우 기각 또는 취소)")
    content: str = Field(..., description="판결 전문 (LLM 요약)")

class ConsultationRequest(BaseModel):
    """구조화된 법률 분석 요청 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    chat_history: List[ConsultationMessage] = Field(None, description="채팅 기록 (사람, AI)")
    question: str = Field(..., description="사용자가 한 질문")

class ConsultationResponse(BaseModel):
    """구조화된 법률 분석 결과 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    answer: str = Field(..., description="AI 답변 (분석 요약, 법령에 근거한 해석, 핵심 쟁점, 의뢰인 상황 적용 및 유의사항)")
    precedents: List[Precedents] = Field(default_factory=list, description="유사 판례 목록")
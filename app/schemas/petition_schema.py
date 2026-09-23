from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from app.schemas.consultation_schema import ConsultationMessage


# ---------------------------------------------------------------------------
# 공통 Enum 정의
# ---------------------------------------------------------------------------
class BusinessType(str, Enum):
    """사업체 구분"""
    BUSINESS = "BUSINESS"          # 사업장
    CONSTRUCTION = "CONSTRUCTION"  # 공사현장


class EmploymentStatus(str, Enum):
    """재직/퇴직 여부"""
    EMPLOYED = "EMPLOYED"  # 재직
    RESIGNED = "RESIGNED"  # 퇴직


class ContractType(str, Enum):
    """근로계약 체결 방법"""
    WRITTEN = "WRITTEN"  # 서면
    VERBAL = "VERBAL"    # 구두

def empty_str_to_none(v):
    """빈 문자열("")이나 공백이 들어오면 None으로 변환하여 Pydantic 날짜 검증 에러 방지"""
    if isinstance(v, str) and not v.strip():
        return None
    return v

# ---------------------------------------------------------------------------
# 1. 도메인 공통 엔티티 (진정인, 피진정인, 근로사실관계)
# ---------------------------------------------------------------------------
class ComplainantData(BaseModel):
    """진정인(근로자) 정보"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    name: str = Field(..., description="진정인 성명")
    birth_date: date | None = Field(default=None, description="생년월일 (YYYY-MM-DD)")
    address: str | None = Field(default=None, description="주소")
    phone: str | None = Field(default=None, description="유선전화번호")
    mobile_phone: str | None = Field(default=None, description="휴대전화번호")
    email: str | None = Field(default=None, description="전자우편주소")
    receive_status: bool = Field(default=True, description="처리상황 수신여부")
    
    @field_validator("birth_date", mode="before")
    @classmethod
    def validate_birth_date(cls, v):
        return empty_str_to_none(v)


class RespondentData(BaseModel):
    """피진정인(사업주) 정보"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    company_name: str = Field(..., description="사업장명(회사명)")
    name: str | None = Field(default=None, description="대표자 성명")
    phone: str | None = Field(default=None, description="대표자 또는 사업장 연락처")
    address: str | None = Field(default=None, description="사업장 주소(실근무장소)")
    business_type: BusinessType = Field(default=BusinessType.BUSINESS, description="사업체 구분")
    employee_count: str | None = Field(default=None, description="상시 근로자 수 (예: 5인 미만, 10인 등)")


class EmploymentFacts(BaseModel):
    """근로 조건 및 체불 기본 정보"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    hire_date: date | None = Field(default=None, description="입사일 (YYYY-MM-DD)")
    resignation_date: date | None = Field(default=None, description="퇴사일 (YYYY-MM-DD)")
    employment_status: EmploymentStatus = Field(default=EmploymentStatus.RESIGNED, description="재직/퇴직 여부")
    job_description: str | None = Field(default=None, description="담당 업무내용")
    pay_day: str | None = Field(default=None, description="정기 임금 지급일 (예: 매월 25일)")
    contract_type: ContractType = Field(default=ContractType.WRITTEN, description="근로계약 체결 형태")

    # 금액 정보 (미입력 시 0 또는 AI 추론)
    unpaid_wages: int = Field(default=0, description="체불 기본임금 (원)")
    unpaid_severance_pay: int = Field(default=0, description="체불 퇴직금 (원)")
    unpaid_other_amount: int = Field(default=0, description="기타 체불금 (주휴, 연차, 가산수당 등) (원)")
    
    @field_validator("hire_date", "resignation_date", mode="before")
    @classmethod
    def validate_dates(cls, v):
        return empty_str_to_none(v)


# ---------------------------------------------------------------------------
# 2. 백엔드 -> AI 요청 (Request)
# ---------------------------------------------------------------------------
class EvidenceDocumentSet(BaseModel):
    """증거 문서 분석 결과 DTO."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    extracted_text: str
    analysis_summary: str


class PetitionDraftRequest(BaseModel):
    """진정서 초안 작성 요청 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    case_id: int = Field(..., description="백엔드 사건 고유 식별자")
    chat_history: List[ConsultationMessage]
    evidence_document: Optional[EvidenceDocumentSet] = None


# ---------------------------------------------------------------------------
# 3. AI -> 백엔드 응답 (Response)
# ---------------------------------------------------------------------------
class GeneratedPetitionContent(BaseModel):
    """AI가 완성/보정한 진정 내용 상세"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    claim_reason: str = Field(..., description="고용노동부 서식용 진정 이유 (육하원칙 상세 경위 전문)")
    target_labor_office: str | None = Field(default=None, description="추천 관할 고용노동(지)청")
    total_unpaid_amount: int = Field(..., description="합산된 총 체불금액 (원)")


class PetitionDraftResponse(BaseModel):
    """진정서 초안 작성 응답 DTO"""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    success: bool = Field(default=True, description="성공 여부")
    case_id: int = Field(..., description="사건 고유 식별자")
    complainant: ComplainantData = Field(..., description="진정인 정보 (그대로 반환)")
    respondent: RespondentData = Field(..., description="보정된 피진정인 정보 (OCR 보완 반영)")
    facts: EmploymentFacts = Field(..., description="보정된 근로 사실관계 (OCR 보완 반영)")
    content: GeneratedPetitionContent = Field(..., description="AI 생성 진정 사유 및 결과")
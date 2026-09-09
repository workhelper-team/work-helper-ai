from typing import List, Optional

from pydantic import BaseModel, Field


class PetitionCreateRequest(BaseModel):
    """진정서 자동 작성을 위한 입력 데이터 스키마."""

    case_id: str = Field(..., description="사건/케이스 식별자")
    petitioner_name: str = Field(..., description="진정인 이름")
    respondent_name: Optional[str] = Field(default=None, description="피진정인 이름")
    summary: str = Field(..., description="사건 개요 (사용자가 입력한 원본 텍스트)")
    ocr_texts: List[str] = Field(
        default_factory=list, description="OCR을 통해 추출된 증빙 문서 텍스트 목록"
    )
    additional_context: Optional[str] = Field(
        default=None, description="추가로 참고할 문맥 정보"
    )


class PetitionDocument(BaseModel):
    """완성된 진정서 문서 스키마."""

    title: str = Field(..., description="진정서 제목")
    body: str = Field(..., description="진정서 본문 전체 내용")
    legal_references: List[str] = Field(
        default_factory=list, description="본문에 인용된 법령/판례 목록"
    )


class PetitionCreateResponse(BaseModel):
    """진정서 생성 결과 응답 스키마."""

    case_id: str
    document: PetitionDocument
    success: bool = True
    message: Optional[str] = None

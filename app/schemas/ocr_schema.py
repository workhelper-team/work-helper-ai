from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from pydantic.alias_generators import to_camel


class OCRDocumentType(str, Enum):
    """OCR 대상 문서 종류."""

    IMAGE = "IMAGE"
    PDF = "PDF"


class EvidenceAnalysisRequest(BaseModel):
    """증거 문서 분석 요청 DTO."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    file_url: str
    user_context: Optional[str] = None


class EvidenceAnalysisResponse(BaseModel):
    """증거 문서 분석 결과 DTO."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    extracted_text: str
    analysis_summary: str


class OCRRequest(BaseModel):
    """Spring Boot로부터 전달받는 OCR 요청 스키마."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    document_id: str = Field(..., description="원본 문서 식별자")
    file_url: str = Field(..., description="OCR 대상 파일에 접근 가능한 URL")
    document_type: OCRDocumentType = Field(
        default=OCRDocumentType.IMAGE, description="문서 종류 (IMAGE, PDF)"
    )


class OCRResponse(BaseModel):
    """OCR 처리 결과 응답 스키마."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    document_id: str
    extracted_text: str
    preprocessed_data: dict | None = Field(
        default=None, description="OCR 텍스트에서 전처리 및 추출된 정형 데이터"
    )
    confidence: Optional[float] = Field(
        default=None, description="추출 텍스트에 대한 신뢰도 점수 (0.0 ~ 1.0)"
    )
    success: bool = True
    message: Optional[str] = None

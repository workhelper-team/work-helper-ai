from typing import Optional
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


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

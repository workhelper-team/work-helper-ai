from fastapi import APIRouter

from app.schemas.consultation_schema import ConsultationRequest, ConsultationResponse
from app.services.rag_service import generate_legal_consultation

router = APIRouter()


@router.post("/search", response_model=ConsultationResponse, summary="법령/판례 유사도 검색")
async def search_legal_documents(request: ConsultationRequest) -> ConsultationResponse:
    """질의와 관련된 법령/판례를 Vector DB에서 검색합니다."""
    return await generate_legal_consultation(request)

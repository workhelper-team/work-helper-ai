from fastapi import APIRouter, HTTPException, status
from app.schemas.rag_schema import ConsultationRequest, ConsultationResponse
from app.services.rag_service import generate_legal_consultation

router = APIRouter()


@router.post(
    "/chat",
    response_model=ConsultationResponse,
    status_code=status.HTTP_200_OK,
    summary="노동법 법률 상담 질의응답 (RAG)",
    description="사용자의 자연어 질문을 바탕으로 pgvector에서 법률 근거를 검색하고, 구조화된 법률 소견을 반환합니다."
)
async def consult_legal_question(request: ConsultationRequest) -> ConsultationResponse:
    try:
        response = await generate_legal_consultation(request)
        return response
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"법률 상담 생성 중 오류가 발생했습니다: {str(e)}"
        )
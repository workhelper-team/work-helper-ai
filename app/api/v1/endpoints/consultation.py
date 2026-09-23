from fastapi import APIRouter, HTTPException, status
from app.schemas.consultation_schema import ConsultationRequest, ConsultationResponse
from app.services.consultation_service import labor_rag_pipeline

router = APIRouter()


@router.post(
    "",
    response_model=ConsultationResponse,
    status_code=status.HTTP_200_OK,
    summary="노동법 법률 상담 질의응답 (RAG)",
    description="사용자의 자연어 질문을 바탕으로 pgvector에서 법률 근거를 검색하고, 구조화된 법률 소견을 반환합니다."
)
async def consult_legal_question(request: ConsultationRequest) -> ConsultationResponse:
    try:
        response = await labor_rag_pipeline(request.question)
        return response
    except Exception as e:
        print(f"법률 상담 생성 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="법률 상담 생성 중 오류가 발생했습니다."
        )
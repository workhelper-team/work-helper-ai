from fastapi import APIRouter, HTTPException, status
from app.schemas.petition_schema import (
    PetitionDraftRequest,
    PetitionDraftResponse,
)
from app.services.petition_service import petition_service

router = APIRouter()


@router.post(
    "",
    response_model=PetitionDraftResponse,
    status_code=status.HTTP_200_OK,
    summary="고용노동부 임금체불 진정서 초안 작성",
    description="대화 이력과 선택적으로 제공된 증거 문서를 바탕으로 진정서 초안을 작성합니다.",
)
async def handle_create_petition(
    request: PetitionDraftRequest,
) -> PetitionDraftResponse:
    try:
        return await petition_service.generate_draft(request)

    except Exception as e:
        print(f"진정서 초안 생성 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="진정서 초안 생성 중 오류가 발생했습니다.",
        )
from fastapi import APIRouter, HTTPException, status
from app.schemas.petition_schema import (
    PetitionDraftRequest,
    PetitionDraftResponse,
    GeneratedPetitionContent,
)
from app.services.petition_service import petition_service

router = APIRouter()


@router.post(
    "",
    response_model=PetitionDraftResponse,
    status_code=status.HTTP_200_OK,
    summary="고용노동부 임금체불 진정서 초안 작성",
    description="진정인/피진정인 정형 데이터, 사용자 정황 서술, OCR 증거 텍스트를 결합하여 진정서 상세 서식 및 진정 사유를 완성합니다.",
)
async def handle_create_petition(
    request: PetitionDraftRequest,
) -> PetitionDraftResponse:
    try:
        # TODO: 2~4단계(OCR 후처리, 결측치 보정, LLM 진정 사유 생성 체인) 로직 호출부 연결 예정
        # 실제 서비스 호출로 대체
        return await petition_service.generate_draft(request)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진정서 초안 생성 중 오류가 발생했습니다: {str(e)}",
        )
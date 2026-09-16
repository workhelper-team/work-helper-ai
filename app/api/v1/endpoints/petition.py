from fastapi import APIRouter

from app.schemas.petition_schema import PetitionCreateRequest, PetitionCreateResponse
from app.services.workflow_service import create_petition

router = APIRouter()


@router.post("", response_model=PetitionCreateResponse, summary="진정서 자동 작성")
async def create_petition(request: PetitionCreateRequest) -> PetitionCreateResponse:
    """OCR 및 법령/판례 검색 결과를 취합하여 진정서 초안을 생성합니다."""
    return await create_petition(request)

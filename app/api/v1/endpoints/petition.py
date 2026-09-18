from fastapi import APIRouter, HTTPException, status
from app.schemas.petition_schema import (
    PetitionDraftRequest,
    PetitionDraftResponse,
    GeneratedPetitionContent,
)

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
        # 임시 스텁 응답 생성 (총 체불액 단순 계산 및 기본 구조 반환)
        total_amount = (
            request.facts.unpaid_wages
            + request.facts.unpaid_severance_pay
            + request.facts.unpaid_other_amount
        )

        dummy_content = GeneratedPetitionContent(
            claim_reason="[초안 생성 대기] 전달받은 정황 및 증거 문서를 바탕으로 고용노동부 제출용 육하원칙 진정 사유가 생성될 예정입니다.",
            target_labor_office="관할 노동관서 자동 판별 대기",
            total_unpaid_amount=total_amount,
            inferred_facts=None,
        )

        return PetitionDraftResponse(
            success=True,
            case_id=request.case_id,
            complainant=request.complainant,
            respondent=request.respondent,
            facts=request.facts,
            content=dummy_content,
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진정서 초안 생성 중 오류가 발생했습니다: {str(e)}",
        )
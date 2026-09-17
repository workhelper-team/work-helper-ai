from fastapi import APIRouter, HTTPException, status
from app.schemas.petition_schema import (
    DocumentDraftRequest,
    DocumentDraftResponse,
    PetitionCreateRequest,
)
from app.services.workflow_service import create_petition

router = APIRouter()


@router.post(
    "",
    response_model=DocumentDraftResponse,
    status_code=status.HTTP_200_OK,
    summary="대응 문서 초안 생성",
    description="사건 정보 및 OCR 추출 텍스트를 기반으로 노동청 제출용 대응 문서 초안을 작성합니다.",
)
# 함수 이름을 엔드포인트 전용 핸들러명으로 변경하여 서비스 함수와 충돌 방지
async def handle_create_petition(
    request: DocumentDraftRequest,
) -> DocumentDraftResponse:
    try:
        # 명세 DTO(DocumentDraftRequest)를 기존 서비스 파이프라인 입력(PetitionCreateRequest)으로 변환
        petition_request = PetitionCreateRequest(
            case_id=request.case_id or "",
            petitioner_name=(request.additional_context or {}).get("petitioner_name", ""),
            respondent_name=(request.additional_context or {}).get("respondent_name"),
            summary=request.summary,
            ocr_texts=list(request.ocr_texts),
            additional_context=str(request.additional_context) if request.additional_context else None,
        )
        result = await create_petition(petition_request)
        # 서비스 결과(PetitionCreateResponse)를 명세 규격(DocumentDraftResponse)으로 변환
        return DocumentDraftResponse(
            document_type=request.document_type,
            content=result.document.body,
            success=result.success,
            message=result.message or "대응 문서 초안 생성이 완료되었습니다.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"진정서 생성 중 오류가 발생했습니다: {str(e)}",
        )

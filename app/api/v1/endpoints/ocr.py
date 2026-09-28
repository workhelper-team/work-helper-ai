from fastapi import APIRouter, HTTPException, status

from app.schemas.ocr_schema import EvidenceAnalysisRequest, EvidenceAnalysisResponse
from app.services.ocr_service import analyze_evidence

router = APIRouter()


@router.post(
    "",
    response_model=EvidenceAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="증거 서류 분석",
    description="증거 파일 URL과 사용자 정황을 바탕으로 OCR 및 법적 쟁점 분석을 수행합니다.",
)
async def analyze_evidence_endpoint(
    request: EvidenceAnalysisRequest,
) -> EvidenceAnalysisResponse:
    try:
        return await analyze_evidence(request)
    except Exception as e:
        print(f"증거 서류 분석 오류: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="증거 서류 분석 중 서버 내부 오류가 발생했습니다.",
        ) from e
from fastapi import APIRouter

from app.schemas.ocr_schema import OCRRequest, OCRResponse
from app.services.ocr_service import extract_text_from_document

router = APIRouter()


@router.post("/extract", response_model=OCRResponse, summary="문서 OCR 텍스트 추출")
async def extract_text(request: OCRRequest) -> OCRResponse:
    """이미지/PDF 파일에서 텍스트를 추출합니다."""
    return await extract_text_from_document(request)

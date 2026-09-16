"""이미지/PDF 파일에서 텍스트를 추출하는 OCR 서비스."""

from app.core.config import settings
from app.schemas.ocr_schema import OCRDocumentType, OCRRequest, OCRResponse


async def extract_text_from_document(request: OCRRequest) -> OCRResponse:
    """파일 URL로부터 텍스트를 추출합니다.

    TODO: 실제 OCR 엔진(Tesseract, Naver Clova OCR 등) 연동 예정.
    """
    engine_name = settings.OCR_ENGINE

    if request.document_type == OCRDocumentType.PDF:
        extracted_text = f"[{engine_name} PDF 텍스트] '{request.file_url}' 본문 내용입니다."
    else:
        extracted_text = f"[{engine_name} 이미지 텍스트] '{request.file_url}' 본문 내용입니다."

    return OCRResponse(
        document_id=request.document_id,
        extracted_text=extracted_text,
        confidence=0.95,
        success=True,
        message="OCR 처리가 완료되었습니다 (더미 구현).",
    )
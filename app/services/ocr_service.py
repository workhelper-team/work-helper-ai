"""이미지/PDF 파일에서 텍스트를 추출하는 OCR 서비스 뼈대."""

from app.core.config import settings
from app.schemas.ocr_schema import OCRDocumentType, OCRRequest, OCRResponse


class OCRService:
    """OCR 엔진 호출을 담당하는 서비스 클래스."""

    def __init__(self, engine: str = settings.OCR_ENGINE):
        self.engine = engine

    async def extract_text(self, request: OCRRequest) -> OCRResponse:
        """파일 URL로부터 텍스트를 추출합니다.

        TODO: 실제 OCR 엔진(Tesseract, Naver Clova OCR, Google Vision 등) 연동으로 교체합니다.
        """
        if request.document_type == OCRDocumentType.PDF:
            extracted_text = f"[더미 PDF 텍스트] '{request.file_url}'에서 추출된 본문 내용입니다."
        else:
            extracted_text = f"[더미 이미지 텍스트] '{request.file_url}'에서 추출된 본문 내용입니다."

        return OCRResponse(
            document_id=request.document_id,
            extracted_text=extracted_text,
            confidence=0.95,
            success=True,
            message="OCR 처리가 완료되었습니다 (더미 구현).",
        )


ocr_service = OCRService()

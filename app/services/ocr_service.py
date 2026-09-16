"""OCR 텍스트 추출 서비스 인터페이스 및 실행 파이프라인."""

from app.core.config import settings
from app.schemas.ocr_schema import OCRDocumentType, OCRRequest, OCRResponse


def _run_tesseract(file_bytes: bytes | None = None, file_url: str | None = None) -> str:
    # TODO: Tesseract 연동 로직
    return "[Tesseract] 추출 텍스트 목업: 근로계약서 - 임금 2,500,000원, 주 40시간 근무"


def _run_paddleocr(file_bytes: bytes | None = None, file_url: str | None = None) -> str:
    # TODO: PaddleOCR 연동 로직
    return "[PaddleOCR] 추출 텍스트 목업: 카카오톡 대화 캡처 - 5월분 주휴수당 미지급 확인"


async def extract_text_from_document(
    request: OCRRequest | None = None,
    file_bytes: bytes | None = None,
    filename: str = "document",
    document_type: OCRDocumentType = OCRDocumentType.IMAGE,
) -> OCRResponse:
    """엔진 설정(settings.OCR_ENGINE)에 따라 적절한 OCR 모듈을 호출합니다.
    
    workflow_service(OCRRequest 기반)와 API 엔드포인트(파일 바이트 기반) 호출을 모두 지원합니다.
    """
    engine = settings.OCR_ENGINE.lower()

    # 1. OCRRequest 객체로 전달된 경우 파라미터 보정
    if request is not None:
        doc_id = request.document_id
        doc_type = request.document_type
        target_url = request.file_url
    else:
        doc_id = filename
        doc_type = document_type
        target_url = None

    # 2. 엔진별 추출 로직 분기
    if "paddle" in engine:
        extracted_text = _run_paddleocr(file_bytes=file_bytes, file_url=target_url)
    elif "tesseract" in engine:
        extracted_text = _run_tesseract(file_bytes=file_bytes, file_url=target_url)
    else:
        extracted_text = f"[{engine}] '{doc_id}' 텍스트 추출 완료 (목업 데이터)"

    return OCRResponse(
        document_id=doc_id,
        extracted_text=extracted_text,
        confidence=0.95,
        success=True,
        message=f"{engine} 엔진을 통한 텍스트 추출이 완료되었습니다.",
    )
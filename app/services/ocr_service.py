"""OCR 텍스트 추출 서비스 인터페이스 및 통합 파이프라인."""

import io
import logging
import os
from typing import Callable

import pymupdf
from PIL import Image, ImageEnhance
import pytesseract

from app.core.config import settings
from app.schemas.ocr_schema import OCRDocumentType, OCRRequest, OCRResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tesseract 바이너리 경로 보정 (Windows 환경 기본 경로)
# ---------------------------------------------------------------------------
DEFAULT_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(DEFAULT_TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESSERACT_PATH

# ---------------------------------------------------------------------------
# PaddleOCR 엔진 싱글톤 (필요 시 지연 로딩)
# ---------------------------------------------------------------------------
_paddle_engine = None


def _get_paddle_engine():
    """PaddleOCR 인스턴스를 싱글톤으로 로드합니다."""
    global _paddle_engine
    if _paddle_engine is None:
        try:
            from paddleocr import PaddleOCR
            logger.info("Initializing PaddleOCR engine...")
            # PaddleOCR 3.x: use_angle_cls -> use_textline_orientation로 대체됨
            # enable_mkldnn 여부는 settings.OCR_PADDLE_ENABLE_MKLDNN(.env)로 제어
            _paddle_engine = PaddleOCR(
                use_textline_orientation=True,
                lang="korean",
                enable_mkldnn=settings.OCR_PADDLE_ENABLE_MKLDNN,
            )
        except ImportError as e:
            logger.error(f"PaddleOCR 패키지가 설치되지 않았습니다: {e}")
            raise
    return _paddle_engine


# ---------------------------------------------------------------------------
# 개별 엔진 추론 로직 (단일 PIL Image 대상)
# ---------------------------------------------------------------------------
def _infer_tesseract(image: Image.Image) -> str:
    """Tesseract 엔진 단일 이미지 추론 (전처리 적용)"""
    # 1. 흑백 변환 및 2배 확대 (해상도 보정)
    processed = image.convert("L")
    w, h = processed.size
    processed = processed.resize((w * 2, h * 2), Image.Resampling.BICUBIC)

    # 2. 명암 대비 강화
    enhancer = ImageEnhance.Contrast(processed)
    processed = enhancer.enhance(1.8)

    # 3. OCR 수행 (단일 블록 및 한영 복합 인식)
    custom_config = r"--oem 3 --psm 6"
    return pytesseract.image_to_string(processed, lang="kor+eng", config=custom_config).strip()


def _infer_paddleocr(image: Image.Image) -> str:
    """PaddleOCR 엔진 단일 이미지 추론"""
    import numpy as np

    ocr = _get_paddle_engine()
    img_np = np.array(image.convert("RGB"))

    # PaddleOCR 3.x: ocr.ocr()은 제거되었고 predict()가 OCRResult 객체 리스트를 반환
    result = ocr.predict(img_np)
    if not result:
        return ""

    extracted_lines = result[0].get("rec_texts", [])
    return "\n".join(extracted_lines).strip()


# ---------------------------------------------------------------------------
# 공통 파이프라인 (PDF/이미지 전처리 및 디스패처)
# ---------------------------------------------------------------------------
def _execute_ocr_pipeline(
    file_bytes: bytes,
    document_type: OCRDocumentType,
    infer_func: Callable[[Image.Image], str],
) -> str:
    """파일 바이트를 처리하여 텍스트를 추출하는 공통 파이프라인"""
    extracted_chunks: list[str] = []

    # 1. PDF 문서: PyMuPDF로 페이지별 이미지 렌더링 후 추론
    if document_type == OCRDocumentType.PDF:
        with pymupdf.open(stream=file_bytes, filetype="pdf") as doc:
            for idx, page in enumerate(doc):
                pix = page.get_pixmap(dpi=150)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                text = infer_func(img)
                if text:
                    extracted_chunks.append(f"--- [Page {idx + 1}] ---\n{text}")
    # 2. 일반 이미지 (PNG, JPG 등)
    else:
        img = Image.open(io.BytesIO(file_bytes))
        text = infer_func(img)
        if text:
            extracted_chunks.append(text)

    return "\n\n".join(extracted_chunks)


# ---------------------------------------------------------------------------
# 공개 서비스 인터페이스
# ---------------------------------------------------------------------------
async def extract_text_from_document(
    request: OCRRequest | None = None,
    file_bytes: bytes | None = None,
    filename: str = "document",
    document_type: OCRDocumentType = OCRDocumentType.IMAGE,
) -> OCRResponse:
    """settings.OCR_ENGINE 설정값에 따라 적절한 엔진으로 텍스트를 추출합니다."""
    engine_name = (settings.OCR_ENGINE or "tesseract").lower()

    logger.info(
        "OCR_ENGINE resolved to '%s' (raw OS env var: %r)",
        engine_name,
        os.environ.get("OCR_ENGINE"),
    )

    if request is not None:
        doc_id = request.document_id
        doc_type = request.document_type
    else:
        doc_id = filename
        doc_type = document_type

    if not file_bytes:
        return OCRResponse(
            document_id=doc_id,
            extracted_text="",
            confidence=0.0,
            success=False,
            message="추출할 파일 데이터가 비어 있습니다.",
        )

    # 엔진 선택
    if "paddle" in engine_name:
        infer_func = _infer_paddleocr
        selected_engine = "paddleocr"
    elif "tesseract" in engine_name:
        infer_func = _infer_tesseract
        selected_engine = "tesseract"
    else:
        return OCRResponse(
            document_id=doc_id,
            extracted_text=f"[{engine_name}] 지원하지 않는 OCR 엔진입니다.",
            confidence=0.0,
            success=False,
            message=f"지원하지 않는 OCR_ENGINE 설정: {engine_name}",
        )

    try:
        extracted_text = _execute_ocr_pipeline(
            file_bytes=file_bytes,
            document_type=doc_type,
            infer_func=infer_func,
        )
        is_success = bool(extracted_text.strip())
        return OCRResponse(
            document_id=doc_id,
            extracted_text=extracted_text,
            confidence=0.85 if is_success else 0.0,
            success=is_success,
            message=(
                f"{selected_engine} 엔진을 통한 텍스트 추출이 완료되었습니다."
                if is_success
                else "텍스트를 추출하지 못했습니다."
            ),
        )
    except Exception as e:
        logger.exception(f"OCR 추출 실패 ({selected_engine}): {e}")
        return OCRResponse(
            document_id=doc_id,
            extracted_text="",
            confidence=0.0,
            success=False,
            message=f"OCR 처리 중 오류가 발생했습니다: {str(e)}",
        )
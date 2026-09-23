"""OCR 텍스트 추출 서비스 인터페이스 및 통합 파이프라인."""

import io
import logging
import mimetypes
import os
import re
from datetime import date
from typing import Callable
from urllib.parse import urlparse

import httpx
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

DATE_PATTERN = r"(\d{4})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?"
PAY_DAY_PATTERN = r"(?:지급일\s*[:：]?\s*)?(?:매\s*월|매\s*달|매\s*주)\s*(\d{1,2}\s*일?|말일)"
COMPANY_NAME_PATTERN = (
    r"(?:상\s*호|회사명|사업장명|\(갑\))\s*[:：\-]?\s*"
    r"(?P<company>[가-힣A-Za-z0-9][가-힣A-Za-z0-9()（）\s]{1,30}?)(?=\s*(?:\(?\s*"
    r"(?:대표자|대표이사|주소|사업장|사무실|전화|휴대폰|이메일|사업자|등록|근무|직무|고용형태|계약)|$))"
)
REPRESENTATIVE_PATTERN = (
    r"(?:대표자|대표이사|사용자|사업주)\s*[:：\-]?\s*(?:\()?"
    r"(?P<name>[가-힣A-Za-z]{2,8})(?=\s*(?:\)|\]|\}|,|;|\n|$|(?:주소|사업장|사무실|전화|휴대폰|이메일|등록|고용형태|계약|근무|직무)))"
)
WORKER_NAME_PATTERN = (
    r"(?:\[\s*근로자\s*\]|\(을\)|근로자|피진정인|성\s*명)\s*"
    r"(?:\([가-힣]+\))?\s*(?:[:：\-]|\)|\])?\s*"
    r"(?P<name>[가-힣]{2,5})(?=\s*(?:\)|\]|\}|,|;|\n|$|\(인\)|\(명\)|\s*\([가-힣]+\)))"
)


def _sanitize_extracted_value(value: str) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip()
    cleaned = cleaned.strip(" \t\n\r()[]{}（）")
    return cleaned


def preprocess_ocr_text(text: str) -> tuple[str, dict[str, str]]:
    """OCR 원문을 정리하고 진정서 입력에 활용할 필드를 추출합니다."""
    cleaned_text = re.sub(r"[ \t]+", " ", text)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()
    extracted: dict[str, str] = {}

    patterns = {
        "complainant_name": WORKER_NAME_PATTERN,
        "representative_name": REPRESENTATIVE_PATTERN,
        "company_name": COMPANY_NAME_PATTERN,
    }
    group_names = {
        "complainant_name": "name",
        "representative_name": "name",
        "company_name": "company",
    }
    for field_name, pattern in patterns.items():
        match = re.search(pattern, cleaned_text)
        if match:
            value = _sanitize_extracted_value(match.group(group_names[field_name]))
            if value:
                extracted[field_name] = value

    pay_day_match = re.search(PAY_DAY_PATTERN, cleaned_text)
    if pay_day_match:
        extracted["pay_day"] = pay_day_match.group(0).strip()

    date_match = re.search(DATE_PATTERN, cleaned_text)
    if date_match:
        year, month, day = map(int, date_match.groups())
        try:
            extracted["hire_date"] = date(year, month, day).isoformat()
        except ValueError:
            pass

    return cleaned_text, extracted


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


async def _download_file(file_url: str) -> tuple[bytes, str]:
    """S3 presigned URL에서 파일 바이트와 응답 MIME 타입을 가져옵니다."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        response = await client.get(file_url)
        response.raise_for_status()
        return response.content, response.headers.get("content-type", "")


def _detect_document_type(
    file_bytes: bytes,
    filename: str = "",
    content_type: str = "",
) -> OCRDocumentType:
    """파일 내용과 메타데이터를 이용해 PDF 또는 이미지 유형을 판별합니다."""
    if file_bytes.startswith(b"%PDF-"):
        return OCRDocumentType.PDF

    normalized_content_type = content_type.split(";", 1)[0].lower().strip()
    if normalized_content_type == "application/pdf":
        return OCRDocumentType.PDF

    suffix = os.path.splitext(urlparse(filename).path)[1].lower()
    guessed_type = normalized_content_type or mimetypes.guess_type(suffix)[0] or ""
    if guessed_type.startswith("image/"):
        return OCRDocumentType.IMAGE

    try:
        with Image.open(io.BytesIO(file_bytes)) as image:
            image.verify()
    except (Image.UnidentifiedImageError, OSError):
        raise ValueError("PDF 또는 지원되는 이미지 파일이 아닙니다.")
    return OCRDocumentType.IMAGE


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

    content_type = ""
    if request is not None:
        doc_id = request.document_id
        filename = request.file_url
        if file_bytes is None:
            file_bytes, content_type = await _download_file(request.file_url)
    else:
        doc_id = filename

    if not file_bytes:
        return OCRResponse(
            document_id=doc_id,
            extracted_text="",
            confidence=0.0,
            success=False,
            message="추출할 파일 데이터가 비어 있습니다.",
        )

    doc_type = _detect_document_type(
        file_bytes=file_bytes,
        filename=filename,
        content_type=content_type,
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
        extracted_text, preprocessed_data = preprocess_ocr_text(extracted_text)
        is_success = bool(extracted_text.strip())
        return OCRResponse(
            document_id=doc_id,
            extracted_text=extracted_text,
            preprocessed_data=preprocessed_data,
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
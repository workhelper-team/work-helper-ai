"""OCR 텍스트 추출 서비스 인터페이스 및 통합 파이프라인."""

import io
import logging
import mimetypes
import os
import re
from enum import Enum
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

import httpx
import pymupdf
from PIL import Image, ImageEnhance
import pytesseract
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from starlette.concurrency import run_in_threadpool

from app.prompts.ocr_prompt import OCR_ANALYSIS_SYSTEM_PROMPT, OCR_ANALYSIS_USER_PROMPT
from app.schemas.ocr_schema import EvidenceAnalysisRequest, EvidenceAnalysisResponse

logger = logging.getLogger(__name__)
load_dotenv(Path(__file__).resolve().parents[2] / ".env")

# ---------------------------------------------------------------------------
# Tesseract 바이너리 경로 보정 (Windows 환경 기본 경로)
# ---------------------------------------------------------------------------
DEFAULT_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(DEFAULT_TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESSERACT_PATH


class OCRDocumentType(str, Enum):
    IMAGE = "IMAGE"
    PDF = "PDF"


# ---------------------------------------------------------------------------
# PaddleOCR 엔진 싱글톤 (필요 시 지연 로딩)
# ---------------------------------------------------------------------------
_paddle_engine = None

def clean_text(text: str) -> str:
    """OCR 텍스트의 연속 공백과 과도한 개행을 정리합니다."""
    cleaned_text = re.sub(r"[ \t]+", " ", text)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text).strip()
    return cleaned_text


def _get_paddle_engine():
    """PaddleOCR 인스턴스를 싱글톤으로 로드합니다."""
    global _paddle_engine
    if _paddle_engine is None:
        try:
            from paddleocr import PaddleOCR
            logger.info("Initializing PaddleOCR engine...")
            # PaddleOCR 3.x: use_angle_cls -> use_textline_orientation로 대체됨
            # enable_mkldnn 여부는 OCR_PADDLE_ENABLE_MKLDNN 환경변수(.env)로 제어
            _paddle_engine = PaddleOCR(
                use_textline_orientation=True,
                lang="korean",
                enable_mkldnn=os.getenv("OCR_PADDLE_ENABLE_MKLDNN", "false").lower()
                in {"1", "true", "t", "yes", "y", "on"},
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

    # PaddleOCR 3.x: predict()가 OCRResult 객체 리스트를 반환
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


def _create_analysis_llm() -> ChatOpenAI | ChatOllama:
    """환경 설정에 따라 문서 분석용 LLM을 생성합니다."""
    temperature = 0.2
    if os.getenv("USE_LOCAL_LLM", "true").lower() in {"1", "true", "t", "yes", "y", "on"}:
        return ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("OLLAMA_MODEL_NAME", "gemma2:2b"),
            temperature=temperature,
            reasoning=False,
        )
    return ChatOpenAI(
        api_key=os.getenv("OPENAI_API_KEY", "test"),
        model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"),
        temperature=temperature,
    )


async def analyze_document_context(
    extracted_text: str,
    user_context: str | None = None,
) -> str:
    """OCR 텍스트와 사용자가 제공한 정황을 비교해 법적 쟁점을 요약합니다."""
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", OCR_ANALYSIS_SYSTEM_PROMPT),
            ("human", OCR_ANALYSIS_USER_PROMPT),
        ]
    )
    analysis_chain = prompt | _create_analysis_llm() | StrOutputParser()
    analysis_summary = await analysis_chain.ainvoke(
        {
            "extracted_text": extracted_text,
            "user_context": user_context or "제공되지 않음",
        }
    )
    analysis_summary = analysis_summary.strip()
    if not analysis_summary:
        raise RuntimeError("LLM이 문서 분석 요약을 생성하지 못했습니다.")
    return analysis_summary


async def analyze_evidence(
    request: EvidenceAnalysisRequest,
) -> EvidenceAnalysisResponse:
    """파일을 OCR 처리하고 사용자 정황과 대조해 분석 결과를 반환합니다."""
    file_bytes, content_type = await _download_file(request.file_url)
    if not file_bytes:
        raise ValueError("다운로드한 증거 파일 데이터가 비어 있습니다.")

    document_type = _detect_document_type(
        file_bytes=file_bytes,
        filename=request.file_url,
        content_type=content_type,
    )

    engine_name = (os.getenv("OCR_ENGINE") or "tesseract").lower()
    logger.info(
        "OCR_ENGINE resolved to '%s' (raw OS env var: %r)",
        engine_name,
        os.environ.get("OCR_ENGINE"),
    )

    if "paddle" in engine_name:
        infer_func = _infer_paddleocr
        selected_engine = "paddleocr"
    elif "tesseract" in engine_name:
        infer_func = _infer_tesseract
        selected_engine = "tesseract"
    else:
        raise ValueError(f"지원하지 않는 OCR_ENGINE 설정: {engine_name}")

    try:
        extracted_text = await run_in_threadpool(
            _execute_ocr_pipeline,
            file_bytes=file_bytes,
            document_type=document_type,
            infer_func=infer_func,
        )
    except Exception:
        logger.exception("OCR 추출 실패 (%s)", selected_engine)
        raise

    extracted_text = clean_text(extracted_text)
    if not extracted_text:
        raise ValueError("문서에서 분석할 텍스트를 추출하지 못했습니다.")

    analysis_summary = await analyze_document_context(
        extracted_text=extracted_text,
        user_context=request.user_context,
    )
    return EvidenceAnalysisResponse(
        extracted_text=extracted_text,
        analysis_summary=analysis_summary,
    )
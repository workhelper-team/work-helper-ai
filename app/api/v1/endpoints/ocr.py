from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.ocr_schema import EvidenceAnalysisResponse, OCRDocumentType
from app.services.ocr_service import extract_text_from_document

router = APIRouter()


@router.post(
    "",
    response_model=EvidenceAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="증거 서류 텍스트 추출 (OCR)",
    description="근로계약서, 임금명세서, 카카오톡 캡처 이미지(또는 PDF)를 업로드받아 텍스트를 추출합니다.",
)
async def extract_document_text(
    file: UploadFile = File(..., description="업로드할 증거 서류 파일 (PNG, JPG, JPEG, PDF)"),
    document_type: OCRDocumentType = Form(
        OCRDocumentType.IMAGE,
        description="문서 유형 (image 또는 pdf)",
    ),
) -> EvidenceAnalysisResponse:
    # 1. 지원 확장자 검증
    allowed_extensions = ["png", "jpg", "jpeg", "pdf"]
    filename = file.filename or "unknown_file"
    file_ext = filename.split(".")[-1].lower() if "." in filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"지원하지 않는 파일 형식입니다. 지원 형식: {', '.join(allowed_extensions)}",
        )

    try:
        # 2. 파일 바이트 읽기
        file_bytes = await file.read()

        if len(file_bytes) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="업로드된 파일이 비어 있습니다.",
            )

        # 3. OCR 파이프라인 수행
        result = await extract_text_from_document(
            file_bytes=file_bytes,
            filename=filename,
            document_type=document_type,
        )
        # 내부 OCR 결과를 명세 규격(EvidenceAnalysisResponse)으로 변환
        return EvidenceAnalysisResponse(
            extracted_text=result.extracted_text,
            analysis_result={"confidence": result.confidence, "document_id": result.document_id},
            success=result.success,
            message=result.message or "증거 이미지 분석이 완료되었습니다.",
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OCR 텍스트 추출 중 서버 내부 오류가 발생했습니다: {str(e)}",
        )
    finally:
        # 메모리 누수 방지를 위한 파일 핸들 정리
        await file.close()
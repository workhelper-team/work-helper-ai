"""OCR + 검색 데이터 취합 후 최종 진정서 포맷팅 파이프라인."""

from langchain_core.output_parsers import StrOutputParser

from app.prompts.petition_prompt import build_petition_user_prompt
from app.schemas.ocr_schema import OCRDocumentType, OCRRequest
from app.schemas.petition_schema import (
    PetitionCreateRequest,
    PetitionCreateResponse,
    PetitionDocument,
)
from app.schemas.consultation_schema import ConsultationRequest
from app.services.llm_service import get_llm
from app.services.rag_service import generate_legal_consultation
from app.services.ocr_service import extract_text_from_document


async def create_petition(request: PetitionCreateRequest) -> PetitionCreateResponse:
    """진정서 생성 전체 파이프라인을 수행합니다."""
    ocr_texts = list(request.ocr_texts)

    # 1. RAG 파이프라인 실행
    rag_response = await generate_legal_consultation(
        ConsultationRequest(question=request.summary)
    )
    legal_references = [item.law for item in rag_response.structured_result.references]

    # 2. 진정서 프롬프트 구성
    user_prompt = build_petition_user_prompt(
        summary=request.summary,
        ocr_texts=ocr_texts,
        legal_references=legal_references,
        additional_context=request.additional_context,
    )

    # 3. LLM 호출 (LangChain 표준 ainvoke 및 파서 사용)
    llm = get_llm()
    chain = llm | StrOutputParser()
    draft_body = await chain.ainvoke(user_prompt)

    # 4. 문서 포맷팅
    document = PetitionDocument(
        title=f"진정서 - {request.petitioner_name}",
        body=draft_body,
        legal_references=legal_references,
    )

    return PetitionCreateResponse(
        case_id=request.case_id,
        document=document,
        success=True,
        message="진정서 초안이 생성되었습니다.",
    )


async def process_document_then_create_petition(
    request: PetitionCreateRequest,
    file_urls: list[str],
) -> PetitionCreateResponse:
    """첨부 파일 OCR 처리 후 진정서를 생성하는 확장 파이프라인."""
    for index, file_url in enumerate(file_urls):
        ocr_result = await extract_text_from_document(
            OCRRequest(
                document_id=f"{request.case_id}-{index}",
                file_url=file_url,
                document_type=OCRDocumentType.IMAGE,
            )
        )
        request.ocr_texts.append(ocr_result.extracted_text)

    return await create_petition(request)
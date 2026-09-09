"""OCR + 검색 데이터 취합 후 최종 진정서 포맷팅 파이프라인."""

from app.prompts.petition_prompt import build_petition_user_prompt
from app.schemas.ocr_schema import OCRDocumentType, OCRRequest
from app.schemas.petition_schema import (
    PetitionCreateRequest,
    PetitionCreateResponse,
    PetitionDocument,
)
from app.schemas.rag_schema import RAGQueryRequest
from app.services.llm_service import llm_service
from app.services.ocr_service import ocr_service
from app.services.rag_service import rag_service


class WorkflowService:
    """OCR, RAG, LLM 서비스를 조합하여 진정서를 생성하는 워크플로우 서비스."""

    async def create_petition(self, request: PetitionCreateRequest) -> PetitionCreateResponse:
        """진정서 생성 전체 파이프라인을 수행합니다.

        1. (필요 시) 첨부 문서 OCR 처리
        2. 사건 개요를 바탕으로 관련 법령/판례 검색 (RAG)
        3. 취합된 정보로 LLM 프롬프트 구성 및 초안 생성
        4. 최종 진정서 문서 포맷팅
        """
        ocr_texts = list(request.ocr_texts)

        rag_response = await rag_service.search(
            RAGQueryRequest(query=request.summary, top_k=5)
        )
        legal_references = [item.title for item in rag_response.results]

        user_prompt = build_petition_user_prompt(
            summary=request.summary,
            ocr_texts=ocr_texts,
            legal_references=legal_references,
            additional_context=request.additional_context,
        )

        draft_body = await llm_service.generate_petition_draft(user_prompt)

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
        self,
        request: PetitionCreateRequest,
        file_urls: list[str],
    ) -> PetitionCreateResponse:
        """첨부 파일 OCR 처리 후 진정서를 생성하는 확장 파이프라인 예시."""
        for index, file_url in enumerate(file_urls):
            ocr_result = await ocr_service.extract_text(
                OCRRequest(
                    document_id=f"{request.case_id}-{index}",
                    file_url=file_url,
                    document_type=OCRDocumentType.IMAGE,
                )
            )
            request.ocr_texts.append(ocr_result.extracted_text)

        return await self.create_petition(request)


workflow_service = WorkflowService()

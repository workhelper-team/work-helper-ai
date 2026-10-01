import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from app.schemas.petition_schema import (
    ComplainantData,
    EmploymentFacts,
    GeneratedPetitionContent,
    PetitionDraftRequest,
    PetitionDraftResponse,
    RespondentData,
)
from app.prompts.petition_prompt import get_petition_prompt
from app.db.retriever import search_similar_chunks

load_dotenv(Path(__file__).resolve().parents[2] / ".env")


class _ExtractedPetitionData(BaseModel):
    complainant: ComplainantData
    respondent: RespondentData
    facts: EmploymentFacts
    user_summary: str


class PetitionProcessingService:
    def __init__(self):
        self.prompt = get_petition_prompt()

    def _is_empty(self, value: str | None) -> bool:
        """값이 None이거나 공백, 또는 Swagger 더미값('string')인 경우 비어있다고 판별"""
        if value is None:
            return True
        val_str = str(value).strip()
        return val_str == "" or val_str.lower() == "string"

    def _create_llm(self) -> ChatOllama | ChatOpenAI:
        """환경 설정에 따라 로컬 Ollama 또는 OpenAI 모델을 생성합니다."""
        model_name = os.getenv("OLLAMA_MODEL_NAME", "gemma2:2b")
        temperature = 0.2
        if os.getenv("USE_LOCAL_LLM", "true").lower() in {"1", "true", "t", "yes", "y", "on"}:
            ollama_args = {
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                "model": model_name,
                "temperature": temperature,
            }
            if "qwen" in model_name.lower():
                try:
                    return ChatOllama(**ollama_args, reasoning=False)
                except TypeError:
                    return ChatOllama(**ollama_args)
            return ChatOllama(**ollama_args)

        return ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY", "test"),
            model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"),
            temperature=temperature,
        )

    async def _extract_petition_data(
        self, request: PetitionDraftRequest
    ) -> _ExtractedPetitionData:
        conversation = "\n".join(
            f"[{message.role}] {message.content}" for message in request.chat_history
        )
        evidence_hint = "증거 문서가 제공되지 않았습니다."
        if request.evidence_document:
            evidence_hint = (
                f"정제된 문서 텍스트:\n{request.evidence_document.extracted_text}\n"
                f"문서 분석 요약:\n{request.evidence_document.analysis_summary}"
            )

        extraction_prompt = (
            "대화와 증거 문서를 바탕으로 진정서 작성에 필요한 정보를 추출하세요. "
            "대화에 없는 사실은 추측하지 말고, 모르는 문자열은 빈 문자열, 날짜 및 선택값은 null, "
            "금액은 0으로 설정하세요. complainant.name과 respondent.company_name도 모르면 빈 문자열로 두세요. "
            "user_summary에는 사용자가 설명한 주요 피해 경위를 간결하게 요약하세요.\n\n"
            f"[대화 기록]\n{conversation}\n\n[참고 증거 문서]\n{evidence_hint}"
        )
        llm = self._create_llm()
        extractor = llm.with_structured_output(_ExtractedPetitionData)
        return await extractor.ainvoke(extraction_prompt)

    def _build_legal_search_query(
        self,
        facts: EmploymentFacts,
        user_statement: str,
        evidence_texts: list[str],
    ) -> str:
        evidence_summary = "\n".join(evidence_texts)
        return (
            "임금체불 진정 사건의 법률 근거를 검색한다.\n"
            f"사용자 진술: {user_statement}\n"
            f"근무 기간: {facts.hire_date or '미상'} ~ {facts.resignation_date or '미상'}\n"
            f"고용 상태: {facts.employment_status.value}\n"
            f"담당 업무: {facts.job_description or '미상'}\n"
            f"급여일: {facts.pay_day or '미상'}\n"
            f"체불 임금: {facts.unpaid_wages:,}원, "
            f"체불 퇴직금: {facts.unpaid_severance_pay:,}원, "
            f"기타 체불액: {facts.unpaid_other_amount:,}원\n"
            f"증거 문서 내용 및 분석: {evidence_summary or '없음'}"
        )

    def _retrieve_legal_context(
        self,
        facts: EmploymentFacts,
        user_statement: str,
        evidence_texts: list[str],
    ) -> str:
        query = self._build_legal_search_query(facts, user_statement, evidence_texts)
        retrieved_chunks = search_similar_chunks(query, top_k=4)

        if not retrieved_chunks:
            return "관련 법령 및 판례 검색 결과가 없습니다."

        return "\n\n".join(
            f"[참고] {index}\n{chunk.get('content', '')}"
            for index, chunk in enumerate(retrieved_chunks, start=1)
            if chunk.get("content")
        ) or "관련 법령 및 판례 검색 결과가 없습니다."

    def _build_fallback_claim_reason(
        self,
        complainant_name: str,
        resp: RespondentData,
        facts: EmploymentFacts,
        user_statement: str,
        evidence_texts: list[str],
        total_amount: int,
    ) -> str:
        complainant = complainant_name.strip() if not self._is_empty(complainant_name) else "[확인 필요: 진정인 성명]"
        company_name = resp.company_name if not self._is_empty(resp.company_name) else "[확인 필요: 회사명]"
        representative_name = resp.name if not self._is_empty(resp.name) else "[확인 필요: 대표자명]"
        company_address = resp.address if not self._is_empty(resp.address) else "[확인 필요: 사업장 주소]"
        hire_date = str(facts.hire_date) if facts.hire_date else "[확인 필요: 입사일]"
        resignation_date = str(facts.resignation_date) if facts.resignation_date else "[확인 필요: 퇴사일]"
        pay_day = facts.pay_day if not self._is_empty(facts.pay_day) else "[확인 필요: 급여일]"
        evidence_summary = (
            "\n".join(evidence_texts) if evidence_texts else "제출된 증거 서류가 확인되지 않았습니다."
        )
        user_summary = user_statement.strip() if not self._is_empty(user_statement) else "임금 체불로 인한 진정 제기"

        return (
            f"진정인 {complainant}은 피진정인 {company_name}(대표자 {representative_name}, 주소: {company_address}) 소속으로 "
            f"{hire_date}부터 {resignation_date}까지 근무하였고, 정기 급여일은 {pay_day}이며, "
            f"체불 금액은 총 {total_amount:,}원으로 확인된다. 진정인은 {user_summary}라고 주장하며, "
            f"제출된 증빙자료({evidence_summary[:200]}...)를 근거로 하여 피진정인의 임금 및 퇴직금 지급 의무 이행을 요구한다."
        )

    async def _generate_claim_reason_llm(
        self,
        complainant: ComplainantData,
        resp: RespondentData,
        facts: EmploymentFacts,
        user_statement: str,
        total_amount: int,
        legal_context: str,
        evidence_texts: list[str],
    ) -> str:
        try:
            llm = self._create_llm()
            chain = self.prompt | llm | StrOutputParser()

            input_payload = {
                "complainant_name": complainant.name if not self._is_empty(complainant.name) else "[확인 필요: 진정인 성명]",
                "company_name": resp.company_name if not self._is_empty(resp.company_name) else "[확인 필요: 회사명]",
                "representative_name": resp.name if not self._is_empty(resp.name) else "[확인 필요: 대표자명]",
                "company_address": resp.address if not self._is_empty(resp.address) else "[확인 필요: 사업장 주소]",
                "hire_date": str(facts.hire_date) if facts.hire_date else "[확인 필요: 입사일]",
                "resignation_date": str(facts.resignation_date) if facts.resignation_date else "[확인 필요: 퇴사일]",
                "employment_status": facts.employment_status.value,
                "job_description": facts.job_description if not self._is_empty(facts.job_description) else "일반 업무",
                "pay_day": facts.pay_day if not self._is_empty(facts.pay_day) else "[확인 필요: 급여일]",
                "unpaid_wages": f"{facts.unpaid_wages:,}",
                "unpaid_severance_pay": f"{facts.unpaid_severance_pay:,}",
                "unpaid_other_amount": f"{facts.unpaid_other_amount:,}",
                "total_amount": f"{total_amount:,}",
                "user_statement": user_statement if not self._is_empty(user_statement) else "임금 체불로 인한 진정 제기",
                "legal_context": legal_context,
                "complainant_details": json.dumps(complainant.model_dump(mode="json", by_alias=True), ensure_ascii=False),
                "respondent_details": json.dumps(resp.model_dump(mode="json", by_alias=True), ensure_ascii=False),
                "facts_details": json.dumps(facts.model_dump(mode="json", by_alias=True), ensure_ascii=False),
                "evidence_document": "\n".join(evidence_texts) or "제공된 증거 문서가 없습니다.",
            }

            raw_response = await chain.ainvoke(input_payload)
            response_text = str(raw_response).strip() if raw_response is not None else ""

            if not response_text:
                return self._build_fallback_claim_reason(
                    complainant.name, resp, facts, user_statement, evidence_texts, total_amount
                )
            return response_text
        except Exception:
            return self._build_fallback_claim_reason(
                complainant.name, resp, facts, user_statement, evidence_texts, total_amount
            )

    async def generate_draft(
        self, request: PetitionDraftRequest
    ) -> PetitionDraftResponse:
        extracted = await self._extract_petition_data(request)
        evidence_texts = []
        if request.evidence_document:
            evidence_texts = [
                f"정제된 문서 텍스트: {request.evidence_document.extracted_text}",
                f"문서 분석 요약: {request.evidence_document.analysis_summary}",
            ]

        legal_context = await run_in_threadpool(
            self._retrieve_legal_context,
            extracted.facts,
            extracted.user_summary,
            evidence_texts,
        )
        total_amount = (
            extracted.facts.unpaid_wages
            + extracted.facts.unpaid_severance_pay
            + extracted.facts.unpaid_other_amount
        )
        claim_reason = await self._generate_claim_reason_llm(
            complainant=extracted.complainant,
            resp=extracted.respondent,
            facts=extracted.facts,
            user_statement=extracted.user_summary,
            total_amount=total_amount,
            legal_context=legal_context,
            evidence_texts=evidence_texts,
        )

        return PetitionDraftResponse(
            success=True,
            case_id=request.case_id,
            complainant=extracted.complainant,
            respondent=extracted.respondent,
            facts=extracted.facts,
            content=GeneratedPetitionContent(
                claim_reason=claim_reason,
                target_labor_office=None,
                total_unpaid_amount=total_amount,
            ),
        )


petition_service = PetitionProcessingService()

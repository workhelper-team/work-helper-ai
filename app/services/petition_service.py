from langchain_core.output_parsers import StrOutputParser

from app.core.llm import get_llm
from app.schemas.petition_schema import (
    PetitionDraftRequest,
    PetitionDraftResponse,
    GeneratedPetitionContent,
    RespondentData,
    EmploymentFacts,
)
from app.prompts.petition_prompt import get_petition_prompt
from app.db.retriever import search_similar_chunks


class PetitionProcessingService:
    def __init__(self):
        self.prompt = get_petition_prompt()

    def _is_empty(self, value: str | None) -> bool:
        """값이 None이거나 공백, 또는 Swagger 더미값('string')인 경우 비어있다고 판별"""
        if value is None:
            return True
        val_str = str(value).strip()
        return val_str == "" or val_str.lower() == "string"

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
            f"증거 문서 내용: {evidence_summary or '없음'}"
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

    def enrich_petition_data(
        self, request: PetitionDraftRequest
    ) -> tuple[dict, RespondentData, EmploymentFacts, dict]:
        comp_dict = request.complainant.model_dump()
        return (
            comp_dict,
            request.respondent,
            request.facts,
            {},
        )

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
        complainant_name: str,
        resp: RespondentData,
        facts: EmploymentFacts,
        user_statement: str,
        total_amount: int,
        evidence_texts: list[str] | None = None,
    ) -> str:
        try:
            legal_context = self._retrieve_legal_context(
                facts,
                user_statement,
                evidence_texts or [],
            )
            llm = get_llm()
            chain = self.prompt | llm | StrOutputParser()

            input_payload = {
                "complainant_name": complainant_name if not self._is_empty(complainant_name) else "[확인 필요: 진정인 성명]",
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
            }

            print(f"[DEBUG LLM INPUT] >>> {input_payload}")
            raw_response = await chain.ainvoke(input_payload)
            response_text = str(raw_response).strip() if raw_response is not None else ""
            print(f"[DEBUG LLM OUTPUT] >>> raw: {repr(raw_response)}")

            if not response_text:
                print("[DEBUG LLM FALLBACK] >>> 빈 응답 감지, 안전한 대체 문안을 사용합니다.")
                return self._build_fallback_claim_reason(
                    complainant_name,
                    resp,
                    facts,
                    user_statement,
                    evidence_texts or [],
                    total_amount,
                )

            return response_text
        except Exception as e:
            print(f"[DEBUG LLM ERROR] >>> {e}")
            import traceback
            traceback.print_exc()
            return self._build_fallback_claim_reason(
                complainant_name,
                resp,
                facts,
                user_statement,
                evidence_texts or [],
                total_amount,
            )

    async def generate_draft(
        self, request: PetitionDraftRequest
    ) -> PetitionDraftResponse:
        enriched_comp_dict, enriched_resp, enriched_facts, inferred_facts = self.enrich_petition_data(request)

        total_amount = (
            enriched_facts.unpaid_wages
            + enriched_facts.unpaid_severance_pay
            + enriched_facts.unpaid_other_amount
        )

        claim_reason = await self._generate_claim_reason_llm(
            complainant_name=enriched_comp_dict.get("name", ""),
            resp=enriched_resp,
            facts=enriched_facts,
            user_statement=request.user_statement,
            total_amount=total_amount,
            evidence_texts=request.evidence_texts,
        )

        from app.schemas.petition_schema import ComplainantData
        return PetitionDraftResponse(
            success=True,
            case_id=request.case_id,
            complainant=ComplainantData(**enriched_comp_dict),
            respondent=enriched_resp,
            facts=enriched_facts,
            content=GeneratedPetitionContent(
                claim_reason=claim_reason,
                target_labor_office=None,
                total_unpaid_amount=total_amount,
                inferred_facts=inferred_facts if inferred_facts else None,
            ),
        )


petition_service = PetitionProcessingService()
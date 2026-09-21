import re
from datetime import date
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


class PetitionProcessingService:
    DATE_PATTERNS = [
        r"(\d{4})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?",
    ]
    PAY_DAY_PATTERN = r"(?:지급일\s*[:：]?\s*)?(?:매\s*월|매\s*달|매\s*주)\s*(\d{1,2}\s*일?|말일)"
    REPRESENTATIVE_PATTERN = r"(?:대표자?|대표이사|사용자|사업주)\s*[:：\-]?\s*\(?([가-힣]{2,4})\)?"
    COMPANY_NAME_PATTERN = r"(?:상\s*호|회사명|사업장명|\(갑\))\s*[:：\-]?\s*([가-힣A-Za-z0-9\(\)\（\）\s]{2,20})"
    WORKER_NAME_PATTERN = r"(?:근로자|피진정인|성\s*명|\(을\))\s*(?:\([가-힣]+\))?\s*[:：\-]?\s*([가-힣]{2,4})"

    def __init__(self):
        self.prompt = get_petition_prompt()

    def _is_empty(self, value: str | None) -> bool:
        """값이 None이거나 공백, 또는 Swagger 더미값('string')인 경우 비어있다고 판별"""
        if value is None:
            return True
        val_str = str(value).strip()
        return val_str == "" or val_str.lower() == "string"

    def _clean_ocr_text(self, text: str) -> str:
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def _parse_date(self, text: str) -> date | None:
        for pattern in self.DATE_PATTERNS:
            match = re.search(pattern, text)
            if match:
                year, month, day = map(int, match.groups())
                try:
                    return date(year, month, day)
                except ValueError:
                    continue
        return None

    def _extract_pay_day(self, text: str) -> str | None:
        match = re.search(self.PAY_DAY_PATTERN, text)
        if match:
            return match.group(0).strip()
        return None

    def _extract_representative_name(self, text: str) -> str | None:
        match = re.search(self.REPRESENTATIVE_PATTERN, text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_worker_name(self, text: str) -> str | None:
        match = re.search(self.WORKER_NAME_PATTERN, text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_company_name(self, text: str) -> str | None:
        match = re.search(self.COMPANY_NAME_PATTERN, text)
        if match:
            return match.group(1).strip()
        return None

    def enrich_petition_data(
        self, request: PetitionDraftRequest
    ) -> tuple[dict, RespondentData, EmploymentFacts, dict]:
        raw_combined = "\n".join(request.evidence_texts)
        combined_ocr_text = self._clean_ocr_text(raw_combined)
        inferred_facts: dict[str, str] = {}

        # 0. 진정인(근로자) 정보 보완
        comp_dict = request.complainant.model_dump()
        if self._is_empty(comp_dict.get("name")):
            worker_name = self._extract_worker_name(combined_ocr_text)
            if worker_name:
                comp_dict["name"] = worker_name
                inferred_facts["complainant.name"] = f"OCR 추출: {worker_name}"

        # 1. 사업장 정보 보완
        resp_dict = request.respondent.model_dump()
        if self._is_empty(resp_dict.get("name")):
            name = self._extract_representative_name(combined_ocr_text)
            if name:
                resp_dict["name"] = name
                inferred_facts["respondent.name"] = f"OCR 추출: {name}"

        if self._is_empty(resp_dict.get("company_name")):
            comp = self._extract_company_name(combined_ocr_text)
            if comp:
                resp_dict["company_name"] = comp
                inferred_facts["respondent.company_name"] = f"OCR 추출: {comp}"

        # 2. 근로 조건 사실관계 보완
        facts_dict = request.facts.model_dump()
        if self._is_empty(facts_dict.get("pay_day")):
            pay_day = self._extract_pay_day(combined_ocr_text)
            if pay_day:
                facts_dict["pay_day"] = pay_day
                inferred_facts["facts.pay_day"] = f"OCR 추출: {pay_day}"

        # hire_date가 없거나 오늘 기본 날짜인 경우 추출 시도
        if not facts_dict.get("hire_date") or self._is_empty(str(facts_dict.get("hire_date"))):
            h_date = self._parse_date(combined_ocr_text)
            if h_date:
                facts_dict["hire_date"] = h_date
                inferred_facts["facts.hire_date"] = f"OCR 추출: {h_date}"

        return comp_dict, RespondentData(**resp_dict), EmploymentFacts(**facts_dict), inferred_facts

    async def _generate_claim_reason_llm(
        self,
        complainant_name: str,
        resp: RespondentData,
        facts: EmploymentFacts,
        user_statement: str,
        evidence_texts: list[str],
        total_amount: int,
    ) -> str:
        dummy_legal_context = (
            "- 근로기준법 제36조(금품 청산): 사망 또는 퇴직 시 14일 이내 일체의 금품 지급 의무\n"
            "- 근로기준법 제43조(임금 지급): 매월 1회 이상 통화로 전액 지급"
        )

        try:
            llm = get_llm()
            chain = self.prompt | llm | StrOutputParser()

            response = await chain.ainvoke({
                "complainant_name": complainant_name if not self._is_empty(complainant_name) else "[확인 필요: 진정인 성명]",
                "company_name": resp.company_name if not self._is_empty(resp.company_name) else "[확인 필요: 회사명]",
                "representative_name": resp.name if not self._is_empty(resp.name) else "[확인 필요: 대표자명]",
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
                "evidence_texts": "\n".join(evidence_texts) if evidence_texts else "(제출된 증거 서류 없음)",
                "legal_context": dummy_legal_context,
            })
            return response.strip()
        except Exception as e:
            return f"[생성 실패] LLM 호출 중 오류가 발생했습니다: {str(e)}"

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
            evidence_texts=request.evidence_texts,
            total_amount=total_amount,
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
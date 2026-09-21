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
    # 1. OCR 텍스트 정규식 패턴 (띄어쓰기/콜론 변형 대응)
    DATE_PATTERNS = [
        r"(\d{4})\s*[.\-/년]\s*(\d{1,2})\s*[.\-/월]\s*(\d{1,2})\s*일?",
    ]
    PAY_DAY_PATTERN = r"(?:매\s*월|매\s*달|매\s*주)\s*(\d{1,2}\s*일?|말일|특정요일)"
    REPRESENTATIVE_PATTERN = r"(?:대표자?|대표이사|사용자|사업주)\s*[:：\-]?\s*([가-힣]{2,4})"
    COMPANY_NAME_PATTERN = r"(?:상\s*호|회사명|사업장명)\s*[:：\-]?\s*([가-힣A-Za-z0-9\(\)\（\）\s]{2,20})"

    def __init__(self):
        self.prompt = get_petition_prompt()

    def _clean_ocr_text(self, text: str) -> str:
        """OCR 추출 텍스트의 노이즈 정제 (중복 공백 및 무의미한 특수문자 완화)"""
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

    def _extract_company_name(self, text: str) -> str | None:
        match = re.search(self.COMPANY_NAME_PATTERN, text)
        if match:
            return match.group(1).strip()
        return None

    def enrich_petition_data(
        self, request: PetitionDraftRequest
    ) -> tuple[RespondentData, EmploymentFacts, dict]:
        # OCR 텍스트 결합 및 정제
        raw_combined = "\n".join(request.evidence_texts)
        combined_ocr_text = self._clean_ocr_text(raw_combined)
        inferred_facts: dict[str, str] = {}

        # 1. 사업장 정보 보완
        resp_dict = request.respondent.model_dump()
        if not resp_dict.get("name"):
            name = self._extract_representative_name(combined_ocr_text)
            if name:
                resp_dict["name"] = name
                inferred_facts["respondent.name"] = f"OCR 추출: {name}"

        if not resp_dict.get("company_name"):
            comp = self._extract_company_name(combined_ocr_text)
            if comp:
                resp_dict["company_name"] = comp
                inferred_facts["respondent.company_name"] = f"OCR 추출: {comp}"

        # 2. 근로 조건 사실관계 보완
        facts_dict = request.facts.model_dump()
        if not facts_dict.get("pay_day"):
            pay_day = self._extract_pay_day(combined_ocr_text)
            if pay_day:
                facts_dict["pay_day"] = pay_day
                inferred_facts["facts.pay_day"] = f"OCR 추출: {pay_day}"

        if not facts_dict.get("hire_date"):
            h_date = self._parse_date(combined_ocr_text)
            if h_date:
                facts_dict["hire_date"] = h_date
                inferred_facts["facts.hire_date"] = f"OCR 추출: {h_date}"

        return RespondentData(**resp_dict), EmploymentFacts(**facts_dict), inferred_facts

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
            "- 근로기준법 제36조(금품 청산): 사망 또는 퇴직 시 지급 사유 발생일로부터 14일 이내 금품 지급 의무\n"
            "- 근로기준법 제43조(임금 지급): 매월 1회 이상 일정한 날짜를 정하여 전액 통화 지급 원칙"
        )

        # 환경 변수(LLM_TEMPERATURE)를 반영하도록 인자 없이 호출
        llm = get_llm()
        chain = self.prompt | llm | StrOutputParser()

        response = await chain.ainvoke({
            "complainant_name": complainant_name,
            "company_name": resp.company_name,
            "representative_name": resp.name or "[확인 필요: 대표자명]",
            "hire_date": str(facts.hire_date) if facts.hire_date else "[확인 필요: 입사일]",
            "resignation_date": str(facts.resignation_date) if facts.resignation_date else "[확인 필요: 퇴사일]",
            "employment_status": facts.employment_status.value,
            "job_description": facts.job_description or "일반 업무",
            "pay_day": facts.pay_day or "[확인 필요: 급여일]",
            "unpaid_wages": f"{facts.unpaid_wages:,}",
            "unpaid_severance_pay": f"{facts.unpaid_severance_pay:,}",
            "unpaid_other_amount": f"{facts.unpaid_other_amount:,}",
            "total_amount": f"{total_amount:,}",
            "user_statement": user_statement,
            "evidence_texts": "\n".join(evidence_texts) if evidence_texts else "(제출된 증거 서류 발췌문 없음)",
            "legal_context": dummy_legal_context,
        })
        return response.strip()

    async def generate_draft(
        self, request: PetitionDraftRequest
    ) -> PetitionDraftResponse:
        enriched_resp, enriched_facts, inferred_facts = self.enrich_petition_data(request)

        total_amount = (
            enriched_facts.unpaid_wages
            + enriched_facts.unpaid_severance_pay
            + enriched_facts.unpaid_other_amount
        )

        claim_reason = await self._generate_claim_reason_llm(
            complainant_name=request.complainant.name,
            resp=enriched_resp,
            facts=enriched_facts,
            user_statement=request.user_statement,
            evidence_texts=request.evidence_texts,
            total_amount=total_amount,
        )

        generated_content = GeneratedPetitionContent(
            claim_reason=claim_reason,
            target_labor_office=None,
            total_unpaid_amount=total_amount,
            inferred_facts=inferred_facts if inferred_facts else None,
        )

        return PetitionDraftResponse(
            success=True,
            case_id=request.case_id,
            complainant=request.complainant,
            respondent=enriched_resp,
            facts=enriched_facts,
            content=generated_content,
        )


petition_service = PetitionProcessingService()
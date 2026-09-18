import re
from datetime import date, datetime
from app.schemas.petition_schema import (
    PetitionDraftRequest,
    PetitionDraftResponse,
    GeneratedPetitionContent,
    RespondentData,
    EmploymentFacts,
)


class PetitionProcessingService:
    """OCR 텍스트 정제, 결측치 보정 및 진정서 초안 데이터를 조합하는 서비스"""

    # 정규식 패턴 모음
    DATE_PATTERNS = [
        r"(\d{4})[.\-/년]\s*(\d{1,2})[.\-/월]\s*(\d{1,2})일?",  # 2024.01.01, 2024년 1월 1일
    ]
    PAY_DAY_PATTERN = r"(?:매월|매달|매주)\s*(\d{1,2}일?|말일|특정요일)"
    REPRESENTATIVE_PATTERN = r"(?:대표자?|대표이사|사용자|사업주)\s*[:：\-]?\s*([가-힣]{2,4})"
    COMPANY_NAME_PATTERN = r"(?:상\s*호|회사명|사업장명)\s*[:：\-]?\s*([가-힣A-Za-z0-9\(\)\（\）\s]{2,20})"

    def _parse_date(self, text: str) -> date | None:
        """문자열에서 가장 먼저 발견되는 유효 날짜를 date 객체로 파싱"""
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
        """임금 지급일 추출 (예: '매월 25일', '매월 말일')"""
        match = re.search(self.PAY_DAY_PATTERN, text)
        if match:
            return match.group(0).strip()
        return None

    def _extract_representative_name(self, text: str) -> str | None:
        """대표자명 추출"""
        match = re.search(self.REPRESENTATIVE_PATTERN, text)
        if match:
            return match.group(1).strip()
        return None

    def _extract_company_name(self, text: str) -> str | None:
        """회사명/상호 추출"""
        match = re.search(self.COMPANY_NAME_PATTERN, text)
        if match:
            return match.group(1).strip()
        return None

    def enrich_petition_data(
        self, request: PetitionDraftRequest
    ) -> tuple[RespondentData, EmploymentFacts, dict]:
        """
        사용자 입력 사실관계와 OCR 텍스트를 병합하여 누락된 필드를 보완.
        우선순위: 사용자 입력값 > OCR 추출값 > None
        """
        combined_ocr_text = "\n".join(request.evidence_texts)
        inferred_facts: dict[str, str] = {}

        # 1. 피진정인(사업장) 정보 보정
        respondent_dict = request.respondent.model_dump()
        
        if not respondent_dict.get("name"):
            inferred_rep = self._extract_representative_name(combined_ocr_text)
            if inferred_rep:
                respondent_dict["name"] = inferred_rep
                inferred_facts["respondent.name"] = f"OCR 추출: {inferred_rep}"

        if not respondent_dict.get("company_name"):
            inferred_comp = self._extract_company_name(combined_ocr_text)
            if inferred_comp:
                respondent_dict["company_name"] = inferred_comp
                inferred_facts["respondent.company_name"] = f"OCR 추출: {inferred_comp}"

        # 2. 근로 조건 및 사실관계(Facts) 보정
        facts_dict = request.facts.model_dump()

        if not facts_dict.get("pay_day"):
            inferred_pay_day = self._extract_pay_day(combined_ocr_text)
            if inferred_pay_day:
                facts_dict["pay_day"] = inferred_pay_day
                inferred_facts["facts.pay_day"] = f"OCR 추출: {inferred_pay_day}"

        # 입사일이 누락된 경우 OCR에서 최초 발견 날짜 탐색 (보조적 추론)
        if not facts_dict.get("hire_date"):
            inferred_hire_date = self._parse_date(combined_ocr_text)
            if inferred_hire_date:
                facts_dict["hire_date"] = inferred_hire_date
                inferred_facts["facts.hire_date"] = f"OCR 추출: {inferred_hire_date}"

        enriched_respondent = RespondentData(**respondent_dict)
        enriched_facts = EmploymentFacts(**facts_dict)

        return enriched_respondent, enriched_facts, inferred_facts

    async def generate_draft(
        self, request: PetitionDraftRequest
    ) -> PetitionDraftResponse:
        """진정서 생성 파이프라인 총괄 실행"""
        # 1) OCR 텍스트 기반 결측치 보정 (2단계)
        enriched_resp, enriched_facts, inferred_facts = self.enrich_petition_data(request)

        # 2) 체불 총액 계산 (원 단위 합산)
        total_amount = (
            enriched_facts.unpaid_wages
            + enriched_facts.unpaid_severance_pay
            + enriched_facts.unpaid_other_amount
        )

        # 3) LLM 호출 전 임시 진정 이유 문안 구성 (3~4단계에서 LLM 체인으로 대체)
        # 더미 템플릿 형태로 우선 동작 검증
        mock_claim_reason = (
            f"진정인은 {enriched_facts.hire_date or '입사일 미상'}부터 "
            f"{enriched_resp.company_name}에서 근무하였으나, "
            f"정기 임금 지급일({enriched_facts.pay_day or '약정일'})에 약정된 임금을 지급받지 못하였습니다. "
            f"현재 확인된 총 체불금액은 금 {total_amount:,}원이며, "
            f"피진정인은 당사자의 지급 요구에도 불구하고 정당한 사유 없이 금품 청산 의무를 해태하고 있어 이에 진정서를 제출합니다."
        )

        generated_content = GeneratedPetitionContent(
            claim_reason=mock_claim_reason,
            target_labor_office=None,  # 3단계 주소 기반 매핑 예정
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
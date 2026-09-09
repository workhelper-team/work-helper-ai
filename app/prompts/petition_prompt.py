"""진정서 생성용 LLM 프롬프트 템플릿."""

from typing import List


PETITION_SYSTEM_PROMPT = """\
당신은 대한민국 법률/행정 절차에 능숙한 전문 법률 문서 작성 보조원입니다.
사용자가 제공한 사건 개요, 증빙 자료(OCR 추출 텍스트), 관련 법령/판례 검색 결과를 바탕으로
격식 있고 논리적인 진정서를 작성합니다.

작성 원칙:
1. 사실관계를 명확하고 객관적으로 서술합니다.
2. 관련 법령 및 판례를 근거로 인용하여 주장의 타당성을 뒷받침합니다.
3. 불필요한 추측이나 과장된 표현을 사용하지 않습니다.
4. 진정서 형식(제목, 당사자 정보, 사건 개요, 청구 취지, 청구 이유 등)을 갖춥니다.
"""


def build_petition_user_prompt(
    summary: str,
    ocr_texts: List[str],
    legal_references: List[str],
    additional_context: str | None = None,
) -> str:
    """진정서 생성을 위한 사용자 프롬프트를 구성합니다."""

    ocr_section = "\n".join(f"- {text}" for text in ocr_texts) or "- (제공된 증빙 문서 없음)"
    legal_section = (
        "\n".join(f"- {ref}" for ref in legal_references) or "- (참고할 법령/판례 없음)"
    )
    context_section = additional_context or "(추가 문맥 없음)"

    return f"""\
[사건 개요]
{summary}

[증빙 문서 (OCR 추출 텍스트)]
{ocr_section}

[관련 법령/판례]
{legal_section}

[추가 문맥]
{context_section}

위 정보를 바탕으로 완성된 진정서를 작성해 주세요.
"""

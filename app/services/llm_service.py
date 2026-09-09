"""LLM 클라이언트 호출 래퍼."""

from app.core.config import settings
from app.prompts.petition_prompt import PETITION_SYSTEM_PROMPT


class LLMService:
    """LLM(OpenAI 등) API 호출을 담당하는 서비스 클래스."""

    def __init__(self, model_name: str = settings.LLM_MODEL_NAME, api_key: str = settings.OPENAI_API_KEY):
        self.model_name = model_name
        self.api_key = api_key

    async def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """시스템/유저 프롬프트를 바탕으로 LLM 응답을 생성합니다.

        TODO: OpenAI(또는 대체 LLM) API 호출 로직으로 교체합니다.
        예: AsyncOpenAI(api_key=self.api_key).chat.completions.create(...)
        """
        return (
            "[더미 LLM 응답]\n"
            f"모델: {self.model_name}\n\n"
            f"{user_prompt}\n\n"
            "위 내용을 바탕으로 생성된 진정서 초안입니다 (더미 구현)."
        )

    async def generate_petition_draft(self, user_prompt: str) -> str:
        """진정서 작성 전용 시스템 프롬프트를 사용하여 초안을 생성합니다."""
        return await self.generate_text(PETITION_SYSTEM_PROMPT, user_prompt)


llm_service = LLMService()

from langchain_core.language_models.chat_models import BaseChatModel
from app.core.config import settings


def get_llm(temperature: float | None = None) -> BaseChatModel:
    """
    설정값(USE_LOCAL_LLM)에 따라 Ollama 또는 OpenAI 인스턴스를 반환합니다.
    temperature가 전달되지 않으면 config(settings.LLM_TEMPERATURE) 기본값을 사용합니다.
    """
    temp = temperature if temperature is not None else settings.LLM_TEMPERATURE

    if getattr(settings, "USE_LOCAL_LLM", True):
        from langchain_ollama import ChatOllama

        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL_NAME,
            temperature=temp,
        )
    else:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            api_key=settings.OPENAI_API_KEY,
            temperature=temp,
        )
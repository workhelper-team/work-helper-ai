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

        ollama_model = getattr(settings, "OLLAMA_MODEL", getattr(settings, "OLLAMA_MODEL_NAME", "llama3.1"))
        ollama_base_url = getattr(settings, "OLLAMA_BASE_URL", "http://localhost:11434")

        common_kwargs = {
            "base_url": ollama_base_url,
            "model": ollama_model,
            "temperature": temp,
            "model_kwargs": {"think": False},
        }

        try:
            return ChatOllama(reasoning=False, **common_kwargs)
        except TypeError:
            try:
                return ChatOllama(**common_kwargs)
            except TypeError:
                common_kwargs["model_kwargs"] = {"think": False, "options": {"think": False}}
                return ChatOllama(**common_kwargs)
    else:
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=settings.OPENAI_MODEL_NAME,
            api_key=settings.OPENAI_API_KEY,
            temperature=temp,
        )
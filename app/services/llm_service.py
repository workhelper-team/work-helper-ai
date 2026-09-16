from functools import lru_cache
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel

from app.core.config import settings

# 랭체인 공통 인터페이스 BaseChatModel 반환
@lru_cache()
def get_llm() -> BaseChatModel:
    """설정(USE_LOCAL_LLM)에 따라 Ollama 또는 OpenAI 인스턴스를 반환합니다."""
    if settings.USE_LOCAL_LLM:
        return ChatOllama(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL_NAME,
            temperature=0.1,  # 법률 도메인이므로 환각 방지를 위해 낮게 유지
        )
    else:
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL_NAME,
            temperature=0.1,
        )
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """애플리케이션 전역 설정.

    환경변수 또는 .env 파일로부터 값을 로드합니다.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- App ---
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "WorkHelper AI Server"
    ENVIRONMENT: str = "local"

    # --- CORS ---
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:8080", "http://localhost:3000"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: str | List[str]) -> List[str] | str:
        if isinstance(value, str) and not value.startswith("["):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    # --- OpenAI / LLM ---
    OPENAI_API_KEY: str = ""
    LLM_MODEL_NAME: str = "gpt-4o-mini"

    # --- Vector DB ---
    VECTOR_DB_URL: str = "http://localhost:6333"
    VECTOR_DB_API_KEY: str = ""
    VECTOR_DB_COLLECTION: str = "workhelper_legal_docs"

    # --- OCR ---
    OCR_ENGINE: str = "tesseract"


settings = Settings()

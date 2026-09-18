from pathlib import Path
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    """애플리케이션 전역 환경 설정."""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Server App ---
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

    # --- LLM Providers ---
    USE_LOCAL_LLM: bool = True
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL_NAME: str = "gemma2:2b"

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL_NAME: str = "gpt-4o-mini"

    # --- Vector DB (PostgreSQL + pgvector) ---
    POSTGRES_USER: str = "workhelper"
    POSTGRES_PASSWORD: str = "workhelper_pw"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "workhelper_db"
    VECTOR_DB_COLLECTION: str = "workhelper_legal_docs"

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        """PostgreSQL pgvector 연결용 SQLAlchemy DSN 생성"""
        return (
                f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Embedding ---
    EMBEDDING_MODEL_NAME: str = "jhgan/ko-sroberta-multitask"

    # --- Vision & OCR ---
    # OCR 엔진 선택 (기본 파이프라인 연동 완료: "tesseract" | "paddleocr")
    # 로컬 테스트 시에는 .env의 OCR_ENGINE 값이 우선 적용됩니다.
    OCR_ENGINE: str = "paddleocr"

    # PaddleOCR의 oneDNN(MKL-DNN) 가속 백엔드 사용 여부.
    # 일부 CPU 환경에서 oneDNN 백엔드가 NotImplementedError를 발생시키므로 기본값은 False.
    # 정상 동작하는 환경에서는 .env에서 true로 바꿔 추론 속도를 높일 수 있습니다.
    OCR_PADDLE_ENABLE_MKLDNN: bool = False


settings = Settings()
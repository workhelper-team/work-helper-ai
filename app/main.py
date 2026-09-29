import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

from app.api.v1.api import api_router

project_name = os.getenv("PROJECT_NAME", "WorkHelper AI Server")
environment = os.getenv("ENVIRONMENT", "local")
cors_origins_value = os.getenv(
    "BACKEND_CORS_ORIGINS",
    "http://localhost:8080,http://localhost:3000",
)
if cors_origins_value.startswith("["):
    cors_origins = json.loads(cors_origins_value)
else:
    cors_origins = [
        origin.strip() for origin in cors_origins_value.split(",") if origin.strip()
    ]

app = FastAPI(title=project_name)

if cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in cors_origins],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix="/internal/ai")

# 루트 엔드포인트
@app.get("/", summary="루트 엔드포인트")
async def root() -> dict:
    return {"message": f"{project_name} is running."}

# 인프라 헬스체크 연동 표준
@app.get("/health", tags=["Health"], summary="헬스체크")
async def health_check() -> dict:
    return {"status": "ok", "environment": environment}
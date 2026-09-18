from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.api import api_router
from app.core.config import settings

app = FastAPI(title=settings.PROJECT_NAME)

if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(api_router, prefix="/internal/ai")

# 루트 엔드포인트
@app.get("/", summary="루트 엔드포인트")
async def root() -> dict:
    return {"message": f"{settings.PROJECT_NAME} is running."}

# 인프라 헬스체크 연동 표준
@app.get("/health", tags=["Health"], summary="헬스체크")
async def health_check() -> dict:
    return {"status": "ok", "environment": settings.ENVIRONMENT}
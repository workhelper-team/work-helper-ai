from fastapi import APIRouter

from app.api.v1.endpoints import health, ocr, petition, rag

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(petition.router, prefix="/petition", tags=["petition"])

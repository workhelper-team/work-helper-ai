from fastapi import APIRouter

from app.api.v1.endpoints import consultation, health, ocr, petition, rag

api_router = APIRouter()

# 엔드포인트 임포트 및 라우터 등록
api_router.include_router(consultation.router, prefix="/consultation", tags=["consultation"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(ocr.router, prefix="/ocr", tags=["ocr"])
api_router.include_router(rag.router, prefix="/rag", tags=["rag"])
api_router.include_router(petition.router, prefix="/petition", tags=["petition"])

from fastapi import APIRouter

from app.api.v1.endpoints import consultation, health, ocr, petition

api_router = APIRouter()

# 엔드포인트 임포트 및 라우터 등록
api_router.include_router(consultation.router, prefix="/consultation", tags=["INT-AI-001 노동법 상담"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(ocr.router, prefix="/evidence-analysis", tags=["INT-AI-002 증거 이미지 분석"])
api_router.include_router(petition.router, prefix="/document-draft", tags=["INT-AI-003 대응 문서 초안"])

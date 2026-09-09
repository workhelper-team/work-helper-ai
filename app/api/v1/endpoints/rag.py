from fastapi import APIRouter

from app.schemas.rag_schema import RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import rag_service

router = APIRouter()


@router.post("/search", response_model=RAGQueryResponse, summary="법령/판례 유사도 검색")
async def search_legal_documents(request: RAGQueryRequest) -> RAGQueryResponse:
    """질의와 관련된 법령/판례를 Vector DB에서 검색합니다."""
    return await rag_service.search(request)

"""Vector DB 유사도 검색을 호출하는 RAG 서비스."""

from app.core.config import settings
from app.db.vector_client import vector_client
from app.schemas.rag_schema import RAGQueryRequest, RAGQueryResponse, RAGSearchResultItem


class RAGService:
    """법령/판례 검색(RAG)을 담당하는 서비스 클래스."""

    async def search(self, request: RAGQueryRequest) -> RAGQueryResponse:
        """질의에 대한 관련 법령/판례를 검색합니다.

        TODO: 질의 임베딩 생성 후 vector_client.similarity_search 호출로 교체합니다.
        """
        collection = request.collection or settings.VECTOR_DB_COLLECTION

        # 예시: query_vector = await embed_text(request.query)
        raw_results = await vector_client.similarity_search(
            query_vector=[],
            collection=collection,
            top_k=request.top_k,
        )

        results = [
            RAGSearchResultItem(
                title=item.get("title", ""),
                content=item.get("content", ""),
                source=item.get("source"),
                score=item.get("score", 0.0),
            )
            for item in raw_results
        ]

        if not results:
            results = [
                RAGSearchResultItem(
                    title="더미 검색 결과",
                    content=f"'{request.query}'와 관련된 법령/판례 내용 (더미 구현)",
                    source="예시 법령 제1조",
                    score=0.0,
                )
            ]

        return RAGQueryResponse(query=request.query, results=results)


rag_service = RAGService()

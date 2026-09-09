"""Vector DB 연결 초기화 뼈대.

실제 운영 환경에서는 Qdrant, Milvus, Pinecone 등의 클라이언트 SDK로 교체합니다.
"""

from typing import Any, Dict, List, Optional

from app.core.config import settings


class VectorClient:
    """Vector DB와의 연결 및 유사도 검색을 담당하는 클라이언트 뼈대 클래스."""

    def __init__(self, url: str = settings.VECTOR_DB_URL, api_key: str = settings.VECTOR_DB_API_KEY):
        self.url = url
        self.api_key = api_key
        self._client: Optional[Any] = None

    def connect(self) -> None:
        """Vector DB 클라이언트를 초기화합니다.

        TODO: 실제 Vector DB SDK(client)로 교체하여 연결을 수립합니다.
        """
        if self._client is not None:
            return
        # 예: self._client = QdrantClient(url=self.url, api_key=self.api_key)
        self._client = {"connected": True, "url": self.url}

    def close(self) -> None:
        """Vector DB 연결을 종료합니다."""
        self._client = None

    async def similarity_search(
        self,
        query_vector: List[float],
        collection: str,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """주어진 쿼리 벡터와 유사한 문서를 검색합니다.

        TODO: 실제 Vector DB 검색 API 호출로 교체합니다.
        """
        if self._client is None:
            self.connect()
        return []


vector_client = VectorClient()

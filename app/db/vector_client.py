from functools import lru_cache
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_postgres import PGVector
from app.core.config import settings

# lru_cache: 커넥션 풀 재생성 방지 캐싱
@lru_cache()
def get_embedding_model() -> HuggingFaceEmbeddings:
    """한국어 임베딩 모델을 CPU 환경에 싱글톤으로 로드합니다."""
    return HuggingFaceEmbeddings(
        model_name=settings.EMBEDDING_MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},  # 코사인 유사도 검색 정확도 최적화
    )

# RAG 시스템에서는 텍스트 청크 + 메타데이터 저장됨
# 이후 검색 시 메타데이터 필터링을 걸 때 성능 향상을 위해 JSONB로 인덱싱
@lru_cache()
def get_vector_store() -> PGVector:
    """PostgreSQL pgvector 벡터 저장소 싱글톤 인스턴스를 반환합니다."""
    return PGVector(
        embeddings=get_embedding_model(),
        collection_name=settings.VECTOR_DB_COLLECTION,
        connection=settings.SQLALCHEMY_DATABASE_URI,
        use_jsonb=True,  # 판례 번호, 법령 조항 등 메타데이터를 JSONB로 인덱싱
    )

def get_retriever(k: int = 3):
    """자연어 질문과 유사한 상위 k개의 법률 문서를 반환하는 검색기를 생성합니다."""
    vector_store = get_vector_store()
    return vector_store.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )
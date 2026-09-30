import os
from typing import List
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

## 임베딩 모델 로딩 (BAAI/bge-m3)
model_name = "BAAI/bge-m3"

# 1. 우선 오프라인 모드로 로컬 캐시 접근 시도
os.environ["HF_HUB_OFFLINE"] = "1"
try:
    embedding_model = SentenceTransformer("BAAI/bge-m3")
except Exception:
    # 2. 로컬 캐시에 모델이 없는 최초 실행 시에만 온라인 전환 후 다운로드
    print("{model_name} 임베딩 모델을 다운로드합니다..")
    os.environ["HF_HUB_OFFLINE"] = "0"
    try:
        embedding_model = SentenceTransformer("BAAI/bge-m3")
    finally:
        # 3. 다운로드 완료 후 다시 오프라인 모드로 복원
        os.environ["HF_HUB_OFFLINE"] = "1"

## 텍스트를 지정된 크기로 분할
def chunk_text(text: str, chunk_size: int = 700, chunk_overlap: int = 100) -> List[str]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", "제", " ", ""]
    )
    return text_splitter.split_text(text)

## bge-m3 모델을 활용한 1024차원 임베딩 벡터 생성
def generate_embeddings(texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    embeddings = embedding_model.encode(
        texts,
        show_progress_bar=False,
        normalize_embeddings=True
    )
    return embeddings.tolist()
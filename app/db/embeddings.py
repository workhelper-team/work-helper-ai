from typing import List
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

## 임베딩 모델 로딩 (BAAI/bge-m3)
embedding_model = SentenceTransformer("BAAI/bge-m3")

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
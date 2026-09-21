import os
from typing import List
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from psycopg.types.json import Json
from sentence_transformers import SentenceTransformer

from app.law.law_repository import fetch_all_legal_documents, upsert_legal_chunks

load_dotenv()

## 임베딩 모델 로딩 (BAAI/bge-m3)
embedding_model = SentenceTransformer("BAAI/bge-m3")

## 법령 조문 특성을 고려한 문단 분할
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
    
## 법령 청크 및 임베딩 파이프라인
def run_law_chunk_ingestion():
    print("법령 데이터 임베딩 및 적재 시작")
    
    # 1. DB에서 법령 원문 조회
    documents = fetch_all_legal_documents()
    print(f"[Pipeline] 총 {len(documents)}건의 법령 원문 데이터를 처리합니다.")
    
    # 2. 법령 원문을 청크화 및 임베딩
    for doc_id, title, full_text, metadata in documents:
        if not full_text:
            continue
        
        print(f"[Processing] 법령명: '{title}' (ID: {doc_id})")
        chunks = chunk_text(full_text)
        print(f"    - 생성된 청크 수: {len(chunks)}개")
        
        embeddings = generate_embeddings(chunks)
        
        records = [
            (doc_id, idx, content, str(emb), Json(metadata or {}))
            for idx, (content, emb) in enumerate(zip(chunks, embeddings))
        ]
        
        # 3. 임베딩된 법령 데이터를 DB에 저장
        upsert_legal_chunks(records)
        print(f"    - DB 적재 완료!")
        
if __name__ == "__main__":
    run_law_chunk_ingestion()
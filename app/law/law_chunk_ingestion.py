from dotenv import load_dotenv
from psycopg.types.json import Json

from app.db.embeddings import chunk_text, generate_embeddings
from app.law.law_repository import fetch_all_legal_documents, upsert_legal_chunks

load_dotenv()
    
## 법령 데이터 청크화 및 임베딩 파이프라인
def run_law_chunk_ingestion():
    print(">> 법령 데이터 청크화 및 임베딩 파이프라인 시작")
    
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
        
    print(">> 파이프라인 종료")
        
if __name__ == "__main__":
    run_law_chunk_ingestion()
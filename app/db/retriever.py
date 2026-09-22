from typing import List, Dict
from app.db.connection import get_db_connection
from app.db.embeddings import generate_embeddings

## 사용자의 질문을 임베딩하여 유사도가 높은 법령 청크를 검색
def search_similar_chunks(query: str, top_k: int = 4) -> List[Dict]:
    
    # 1. 사용자 질문 임베딩
    query_embedding = generate_embeddings([query])[0]
    
    # 2. DB에서 코사인 유사도 기반 TOP-K 검색
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            sql = """
            SELECT
                content,
                metadata,
                (embedding <=> %s::vector) as distance
            FROM rag.legal_chunks
            ORDER BY distance ASC
            LIMIT %s;
            """
            cursor.execute(sql, (str(query_embedding), top_k))
            results = cursor.fetchall()
            
            return [
                {
                    "content": row[0],
                    "metadata": row[1],
                    "score": row[2]
                }
                for row in results
            ]
            
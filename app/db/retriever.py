from typing import List, Dict
from app.db.connection import get_db_connection
from app.db.embeddings import generate_embeddings

## 사용자의 질문을 임베딩하여 유사도가 높은 법령 청크를 검색
# OCR 증거분석에서 사용
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

## 사용자의 질문을 임베딩 후 의도에 따라 법령 및 판례 청크를 조건부로 검색
# AI 노무 법률 상담에서 사용
def search_legal_context(
    query: str,
    top_k_law: int = 3,
    top_k_precedent: int = 2,
    include_precedents: bool = True
) -> Dict[str, List[Dict]]:
    
    # 1. 사용자 질문 임베딩
    query_embedding = generate_embeddings([query])[0]
    results = {"laws": [], "precedents": []} # 답변용 딕셔너리 구조
    
    # 2. DB에서 코사인 유사도 기반 TOP-K 검색
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 2-1. 법령 검색
            law_sql = """
                SELECT content, metadata, (embedding <=> %s::vector) AS distance
                FROM rag.legal_chunks
                ORDER BY distance ASC
                LIMIT %s;
            """
            cursor.execute(law_sql, (str(query_embedding), top_k_law))
            results["laws"] = [
                {"content": row[0], "metadata": row[1], "score": row[2]}
                for row in cursor.fetchall()
            ]
            
            # 2-2. 판례 검색 (CASE_DISPUTE 분쟁 질문인 경우에만 수행)
            if include_precedents:
                prec_sql = """
                    SELECT content, metadata, (embedding <=> %s::vector) AS distance
                    FROM rag.precedent_chunks
                    ORDER BY distance ASC
                    LIMIT %s;
                """
                cursor.execute(prec_sql, (str(query_embedding), top_k_precedent))
                results["precedents"] = [
                    {"content": row[0], "metadata": row[1], "score": row[2]}
                    for row in cursor.fetchall()
                ]
    
    return results
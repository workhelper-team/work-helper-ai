from app.db.connection import get_db_connection
from typing import Any, Dict, List, Tuple
from psycopg.types.json import Json
from dotenv import load_dotenv

load_dotenv()

## 문서 데이터를 rag.legal_documents 테이블에 저장 (UPSERT)
def upsert_legal_document(doc_data: Dict[str, Any]) -> int:
    sql = """
    INSERT INTO rag.legal_documents (source_type, source_id, title, full_text, source_url, metadata)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON CONFLICT (source_type, source_id)
    DO UPDATE SET
        title = EXCLUDED.title,
        full_text = EXCLUDED.full_text,
        source_url = EXCLUDED.source_url,
        metadata = EXCLUDED.metadata
    RETURNING legal_document_id;
    """

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    sql,
                    (
                        doc_data.get("source_type"),
                        doc_data.get("source_id"),
                        doc_data.get("title"),
                        doc_data.get("full_text"),
                        doc_data.get("source_url"),
                        doc_data.get("metadata")
                    )
                )
                row = cursor.fetchone()
                doc_id = row[0] if row else None
                conn.commit()
                return doc_id
    except Exception as e:
        print(f"[DB] 법령 데이터 저장 실패: {e}")
        raise e

## 법령 원문 데이터 전체 조회
def fetch_all_legal_documents() -> List[Tuple[int, str, str, Dict[str, Any]]]:
    select_sql = (
        "SELECT legal_documents_id, title, full_text, metadata FROM rag.legal_documents;"
    )
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(select_sql)
            return cursor.fetchall()

## 법령 청크 데이터를 rag.legal_chunks 테이블에 저장 (UPSERT)
def upsert_legal_chunks(records: List[Tuple[int, int, str, str, Json]]) -> None:
    if not records:
        return
    
    upsert_sql = """
    INSERT INTO rag.legal_chunks (legal_document_id, chunk_index, content, embedding, metadata)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (legal_document_id, chunk_index)
    DO UPDATE SET
        content = EXCLUDED.content,
        embedding = EXCLUDED.embedding,
        metadata = EXCLUDED.metadata;
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(upsert_sql, records)
            conn.commit()
    
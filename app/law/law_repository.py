import os
from typing import Any, Dict
from dotenv import load_dotenv
import psycopg

load_dotenv()

# DB 커넥션 생성 및 연결
def get_db_connection():
    return psycopg.connect(
        host = os.getenv("POSTGRES_HOST"),
        port= os.getenv("POSTGRES_PORT", "5432"),
        dbname = os.getenv("POSTGRES_DB", "workhelper"),
        user = os.getenv("POSTGRES_USER", "postgres"),
        password = os.getenv("POSTGRES_PASSWORD")
    )
    
# 문서 데이터를 rag.legal_documents 테이블에 저장 (UPSERT)
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
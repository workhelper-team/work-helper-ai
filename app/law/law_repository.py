import os
from typing import Any, Dict
from dotenv import load_dotenv
import psycopg2

load_dotenv()

# DB 연결 및 rag.legal_documents 테이블 접근 전담 클래스
class LegalDocumentRepository:
    
    # DB 설정 로드
    def __init__(self):
        self.db_host = os.getenv("POSTGRES_HOST")
        self.db_port = os.getenv("POSTGRES_PORT", "5432")
        self.db_name = os.getenv("POSTGRES_DB", "workhelper")
        self.db_user = os.getenv("POSTGRES_USER", "postgres")
        self.db_password = os.getenv("POSTGRES_PASSWORD")
    
    # 컨넥션 연결
    def _get_connection(self):
        return psycopg2.connect(
            host=self.db_host,
            port=self.db_port,
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_password
        )
    
    # 문서 데이터를 rag.legal_documents 테이블에 저장 (UPSERT)
    def upsert_document(self, doc_data: Dict[str, Any]) -> int:
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
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                sql,
                (
                    doc_data.get("source_type"),
                    doc_data.get("source_id"),
                    doc_data.get("title"),
                    doc_data.get("full_text"),
                    doc_data.get("source_url"),
                    doc_data.get("metadata"),
                )
            )
            doc_id = cursor.fetchone()[0]
            conn.commit()
            return doc_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
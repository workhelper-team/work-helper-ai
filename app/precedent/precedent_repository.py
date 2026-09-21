from typing import Any, Dict, List, Tuple
from psycopg.types.json import Json
from app.db.connection import get_db_connection
    
## 판례 데이터 배치 저장
def upsert_precedents(data_list: list[dict]) -> None:
    if not data_list:
        print("[DB] 저장할 판례 데이터가 없습니다.")
        return
    
    # insert 쿼리문
    upsert_query = """
    INSERT INTO rag.precedents (
        precedent_id, case_number, case_name, court_name, judgment_date,
        judgment_type, referenced_articles, matched_laws, case_note, summary, judgment_content
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT ON CONSTRAINT pk_precedents DO UPDATE SET
        case_number = EXCLUDED.case_number,
        case_name = EXCLUDED.case_name,
        court_name = EXCLUDED.court_name,
        judgment_date = EXCLUDED.judgment_date,
        judgment_type = EXCLUDED.judgment_type,
        referenced_articles = EXCLUDED.referenced_articles,
        matched_laws = EXCLUDED.matched_laws,
        case_note = EXCLUDED.case_note,
        summary = EXCLUDED.summary,
        judgment_content = EXCLUDED.judgment_content;
    """
    
    # 저장할 판례 데이터
    records = [
        (
            d["precedent_id"],
            d["case_number"],
            d["case_name"],
            d["court_name"],
            d["judgment_date"],
            d["judgment_type"],
            d["referenced_articles"],
            d["matched_laws"],
            d["case_note"],
            d["summary"],
            d["judgment_content"]
        )
        for d in data_list
    ]
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(upsert_query, records)
                conn.commit()
                print(f"[DB] 총 {len(records)}건의 판례 데이터 저장 및 갱신 완료")
    except Exception as e:
        print(f"[DB] 데이터 적재 중 에러 발생 : {e}")
        raise e
    
## 판례 원문 데이터 전체 조회
def fetch_all_precedents() -> List[Tuple]:
    select_sql = """
    SELECT
        precedent_id,
        case_number,
        case_name,
        court_name,
        judgment_date,
        judgment_type
        referenced_articles,
        matched_laws,
        case_note,
        summary,
        judgment_content
    FROM rag.precedents;
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(select_sql)
            return cursor.fetchall()
        
## 판례 청크 데이터를 rag.legal_chunks 테이블에 저장 (UPSERT)
def upsert_precedent_chunks(records: List[Tuple[int, int, str, str, Json]]) -> None:
    if not records:
        return
    
    upsert_sql = """
    INSERT INTO rag.precedent_chunks (precedent_id, chunk_index, content, embedding, metadata)
    VALUES (%s, %s, %s, %s, %s)
    ON CONFLICT (precedent_id, chunk_index)
    DO UPDATE SET
        content = EXCLUDED.content,
        embedding = EXCLUDED.embedding,
        metadata = EXCLUDED.metadata;
    """
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.executemany(upsert_sql, records)
            conn.commit()
    
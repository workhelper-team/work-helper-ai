import os
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

## env 파일에서 설정을 로드하여 DB 커넥션을 반환
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        dbname=os.getenv("POSTGRES_DB", "workhelper"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD")
    )
    
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
    ) VALUES %s
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
            d["precedent_id"], d["case_number"], d["case_name"], d["court_name"],
            d["judgment_date"], d["judgment_type"], d["referenced_articles"],
            d["matched_laws"], d["case_note"], d["summary"], d["judgment_content"]
        )
        for d in data_list
    ]
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        execute_values(cursor, upsert_query, records)
        conn.commit()
        print(f"[DB] 총 {len(records)}건의 판례 데이터 저장 및 갱신 완료")
    except Exception as e:
        conn.rollback()
        print(f"[DB] 데이터 적재 중 에러 발생 : {e}")
    finally:
        cursor.close()
        conn.close()
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
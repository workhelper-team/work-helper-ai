from dotenv import load_dotenv
from psycopg.types.json import Json

from app.db.connection import get_db_connection
from app.db.embeddings import chunk_text, generate_embeddings
from app.precedent.precedent_repository import fetch_all_precedents, upsert_precedent_chunks

load_dotenv()

## 판시사항, 판결요지, 판결전문 중 존재하는 필드만 합쳐서 청크화된 데이터의 content로 사용
def build_precedent_full_text(
    case_note: str, summary: str, judgment_content: str
) -> str:
    parts = []
    
    if case_note and case_note.strip():
        parts.append(f"[판시사항]\n{case_note.strip()}")
        
    if summary and summary.strip():
        parts.append(f"[판결요지]\n{summary.strip()}")
        
    if judgment_content and judgment_content.strip():
        parts.append(f"[판결전문]\n{judgment_content.strip()}")
        
    return "\n\n".join(parts)

## 판례 데이터 청크화 및 임베딩 파이프라인
def run_precedent_chunk_ingestion():
    print(">> 판례 데이터 청크화 및 임베딩 파이프라인 시작")
    
    # 1. DB에서 판례 데이터 필드 조회
    precedents = fetch_all_precedents()
    total_count = len(precedents)
    print(f"[Pipeline] 총 {total_count}건의 판례 데이터를 처리합니다.")
    
    # 2. 판례 데이터를 청크화 및 임베딩
    with get_db_connection() as conn:
        for idx, prec in enumerate(precedents, start=1):
            (
                prec_id,
                case_number,
                case_name,
                court_name,
                judgment_date,
                judgment_type,
                referenced_articles,
                matched_laws,
                case_note,
                summary,
                judgment_content
            ) = prec

            # 청크 content용 텍스트 결합 (판시사항 + 판결요지 + 판결전문)
            full_text_to_chunk = build_precedent_full_text(
                case_note, summary, judgment_content
            )
            
            if not full_text_to_chunk:
                print(f"\n[Skip] ({idx:,} / {total_count:,}) 판례 ID {prec_id}: 텍스트 데이터가 없어 스킵합니다.")
                continue
            
            print(f"\n[Processing] 판례: '{case_name}' (사건번호: {case_number}) - {idx:,} / {total_count:,}")
            chunks = chunk_text(full_text_to_chunk)
            print(f"   - 생성된 청크 수: {len(chunks)}개")
            
            embeddings = generate_embeddings(chunks)
            
            # 3. 메타데이터 JSON 딕셔너리 구성
            metadata_dict = {
                "case_number": case_number,
                "case_name": case_name,
                "court_name": court_name,
                "judgment_date": str(judgment_date).strip() if judgment_date else "",
                "judgment_type": judgment_type,
                "referenced_articles": referenced_articles,
                "matched_laws": matched_laws,
            }
            
            records = [
                (prec_id, idx, content, str(emb), Json(metadata_dict))
                for idx, (content, emb) in enumerate(zip(chunks, embeddings))
            ]
            
            # 4. 임베딩된 판례 데이터를 DB에 저장
            upsert_precedent_chunks(conn, records)
            print(f"   - DB 적재 완료!")

if __name__ == "__main__":
    run_precedent_chunk_ingestion()
from typing import Any, Dict
from app.law.law_api_client import fetch_law_xml
from app.law.law_parser import parse_to_documents_schema
from app.law.law_repository import upsert_legal_document

## 하나의 법령 수집 및 DB 처리 함수
def ingest_law_by_name(law_name: str) -> Dict[str, Any]:
    print(f"[{law_name}] 수집 시작...")
    law_id, xml_content = fetch_law_xml(law_name)
    
    print(f"[{law_name}] XML 파싱 중...")
    doc_data = parse_to_documents_schema(law_id, xml_content)
    
    print(f"[{law_name}] DB 저장 중...")
    doc_id = upsert_legal_document(doc_data)
    
    print(f"성공: [{doc_data['title']}] 저장 완료 (ID: {doc_id})")
    return {"legal_document_id": doc_id, "title": doc_data["title"]}

## 파이프라인 프로세스 실행 함수
def run_law_ingestion(target_laws: list[str]) -> None:
    for law in target_laws:
        try:
            ingest_law_by_name(law)
        except Exception as e:
            print(f"[실패] [{law}] - {e}")

if __name__ == "__main__":
    target_laws = [
        "근로기준법",
        "근로자퇴직급여 보장법",
        "최저임금법",
        "임금채권보장법"
    ]
    
    run_law_ingestion(target_laws)
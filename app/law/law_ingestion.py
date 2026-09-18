from typing import Any, Dict
from app.law.law_repository import LegalDocumentRepository
from app.law.law_api_client import LawAPIClient
from app.law.law_parser import LawXMLParser

# 전체 데이터 수집 및 저장 실행 파이프라인 관리 파사드(Facade) 클래스
class LawIngestionService:
    def __init__(self):
        self.api_client = LawAPIClient()
        self.parser = LawXMLParser()
        self.repository = LegalDocumentRepository()
    
    def ingest_law_by_name(self, law_name: str) -> Dict[str, Any]:
        print(f"[{law_name}] 수집 시작...")
        law_id, xml_content = self.api_client.fetch_law_xml(law_name)
        
        print(f"[{law_name}] XML 파싱 중...")
        doc_data = self.parser.parse_to_documents_schema(law_id, xml_content)
        
        print(f"[{law_name}] DB 저장 중...")
        doc_id = self.repository.upsert_document(doc_data)
        
        print(f"성공: [{doc_data['title']}] 저장 완료 (ID: {doc_id})")
        return {"legal_document_id": doc_id, "title": doc_data["title"]}
    
if __name__ == "__main__":
    service = LawIngestionService()
    target_laws = [
        "근로기준법",
        "근로자퇴직급여 보장법",
        "최저임금법",
        "임금채권보장법"
    ]
    
    for law in target_laws:
        try:
            service.ingest_law_by_name(law)
        except Exception as e:
            print(f"실패: [{law}] - {e}")
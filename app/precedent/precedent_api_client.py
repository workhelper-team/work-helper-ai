import os
import requests
from dotenv import load_dotenv

load_dotenv()

SEARCH_URL = "http://www.law.go.kr/DRF/lawSearch.do"
SERVICE_URL = "http://www.law.go.kr/DRF/lawService.do"
OC_ID = os.getenv("LAW_OPENAPI_OC")

# 특정 법률 키워드 및 페이지 번호에 해당하는 판례 목록 XML 수신
def fetch_precedent_list_xml(law_name: str, page: int = 1) -> str | None:
    params = {
        "OC": OC_ID,
        "target": "prec",
        "type": "XML",
        "query": law_name,
        "display": 100,
        "page": page
    }
    
    try:
        response = requests.get(SEARCH_URL, params=params, timeout=10)
        return response.text if response.status_code == 200 else None
    except Exception as e:
        print(f"API 요청 실패 - 목록 조회 : {e}")
        return None

## 판례일련번호(ID)에 해당하는 판례 상세 본문 XML 수신
def fetch_precedent_detail_xml(prec_id: str) -> str | None:
    params = {
        "OC": OC_ID,
        "target": "prec",
        "type": "XML",
        "ID": prec_id
    }
    
    try:
        response = requests.get(SERVICE_URL, params=params, timeout=10)
        return response.text if response.status_code == 200 else None
    except Exception as e:
        print(f"API 요청 실패 - 상세 조회 : {e}")
        return None
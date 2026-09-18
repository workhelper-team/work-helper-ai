import re
from bs4 import BeautifulSoup

## 목록 XML에서 판례 일련번호 리스트와 전체 개수를 반환
def parse_precedent_list_ids(xml_content: str) -> tuple[list[str], int]:
    soup = BeautifulSoup(xml_content, "xml") # XML 구성요소를 쉽게 다루기 위한 객체
    
    total_cnt_tag = soup.find("totalCnt")
    total_cnt = int(total_cnt_tag.text) if total_cnt_tag and total_cnt_tag.text else 0
    
    ids = []
    for item in soup.find_all("prec"):
        prec_id_tag = item.find("판례일련번호")
        if prec_id_tag and prec_id_tag.text:
            ids.append(prec_id_tag.text.strip())
    
    return ids, total_cnt

# XML에서 타겟 법령 목록(target_laws)을 매칭하여 추출
# 1차: 참조조문 태그
# 2차: 판시사항 + 판결요지 본문
# 3차: 매칭 실패 시 기본 검색 법령(default_law) 적용
def extract_matched_laws(
    soup: BeautifulSoup, target_laws: list[str], default_law: str | None = None
) -> list[str]:
    matched = set()
    
    # 참고 법령을 탐색할 텍스트 [참조조문] -> [판시사항/판결요지] -> [판례내용]
    # 참조 조문
    ref_clause = soup.find("참조조문")
    ref_text = ref_clause.get_text() if ref_clause else ""

    # 판시사항 + 판결요지
    summary = soup.find("판시사항")
    gist = soup.find("판결요지")
    summary_text = (summary.get_text() if summary else "") + " " + (
        gist.get_text() if gist else ""
    )
    
    # 판례 내용
    content = soup.find("판례내용")
    content_text = content.get_text() if content else ""
    
    # 전체 텍스트 합치기 (우선순위대로)
    full_text = f"{ref_text}\n{summary_text}\n{content_text}"

    if not full_text.strip():
        return []

    # 2. 정규식 법령 형태의 단어 추출 ex) 근로기준법, 임금채권 보장법 등
    for law in ["근로기준법", "근로자퇴직급여 보장법", "최저임금법", "임금채권보장법"]:
        if law in full_text:
            matched.add(law)

    return list(matched)

## 판례 상세 XML 데이터를 정제하여 딕셔너리로 변환
def parse_precedent_detail(
    xml_content: str, target_laws: list[str], default_law: str | None = None
) -> dict | None:
    if not xml_content or not xml_content.strip():
        return None
    
    soup = BeautifulSoup(xml_content, "xml")
    
    # 법제처 판례 상세 API의 최상위/본문 태그 검색
    info = soup.find("판례") or soup.find("PrecService") or soup.find("판례정보")
    
    if not info:
        return None
    
    def clean_text(tag_name: str) -> str:
        tag = info.find(tag_name)
        if not tag or not tag.text:
            return ""
        
        # 1. 태그 원본 문자열 추출
        raw_text = tag.get_text()
        if not raw_text or raw_text.lower() == "null":
            return ""
        
        # 2. 문자열 형태의 </br>, <br>, <br/> 등을 먼저 줄바꿈(\n)으로 변환
        text_content = re.sub(r"</?br\s*/?>", "\n", raw_text, flags=re.IGNORECASE)
        
        # 3. HTML 특수문자 엔티티 처리
        text_content = text_content.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">")
        
        # 4. 줄바꿈 단위로 정돈하여 불필요한 공백 제거 후 다시 연결
        lines = [line.strip() for line in text_content.splitlines()]
        return "\n".join(line for line in lines if line)
    
    prec_id_str = clean_text("판례정보일련번호")
    
    # 숫자 외의 모든 문자(줄바꿈, 공백, 특수문자 등) 제거
    clean_prec_id = re.sub(r"\D", "", prec_id_str) if prec_id_str else ""
    # 숫자로 변환할 수 없는 경우 안전하게 제외
    if not clean_prec_id:
        return None
    
    # 참조 조문이 비는 것을 방지하기 위한 절차
    matched_laws = extract_matched_laws(soup, target_laws, default_law)
    
    raw_date = clean_text("선고일자")
    if raw_date.lower() == "null":
        formatted_date = None
    else:
        formatted_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
    
    return {
        "precedent_id": int(clean_prec_id),
        "case_number": clean_text("사건번호"),
        "case_name": clean_text("사건명"),
        "court_name": clean_text("법원명"),
        "judgment_date": formatted_date,
        "judgment_type": clean_text("판결유형"),
        "referenced_articles": clean_text("참조조문"),
        "matched_laws": matched_laws,
        "case_note": clean_text("판시사항"),
        "summary": clean_text("판결요지"),
        "judgment_content": clean_text("판례내용")
    }
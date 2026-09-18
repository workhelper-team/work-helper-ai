import time
from app.precedent.precedent_api_client import fetch_precedent_detail_xml, fetch_precedent_list_xml
from app.precedent.precedent_parser import parse_precedent_list_ids, parse_precedent_detail
from app.precedent.precedent_repository import upsert_precedents

## 대상 법률 목록에서 중복 없는 판례 ID 전체 수집
def collect_all_unique_ids(target_laws: list[str]) -> list[str]:
    id_law_map = {}  # { "284640": "근로기준법", ... }
    print("판례 수집 시작")

    for law in target_laws:
        first_xml = fetch_precedent_list_xml(law, page=1)
        if not first_xml:
            continue

        ids, total_cnt = parse_precedent_list_ids(first_xml)
        for prec_id in ids:
            id_law_map.setdefault(prec_id, law)  # 최초 검색된 법률 매핑 유지

        total_pages = (total_cnt // 100) + (1 if total_cnt % 100 > 0 else 0)
        print(f"{law}: 총 {total_cnt}건 ({total_pages} 페이지)")

        for page in range(2, total_pages + 1):
            page_xml = fetch_precedent_list_xml(law, page=page)
            if page_xml:
                page_ids, _ = parse_precedent_list_ids(page_xml)
                for prec_id in page_ids:
                    id_law_map.setdefault(prec_id, law)
            time.sleep(0.05)

    print(f"수집 완료 중복 제거된 판례 ID 총 {len(id_law_map)}건")
    return id_law_map

## 파이프라인 전체 프로세스
def run_pipeline(target_laws: list[str]) -> None:
    # 판례 ID 수집
    id_law_map = collect_all_unique_ids(target_laws)
    
    # 상세 파싱
    print("파싱 시작")
    parsed_results = []
    total_len = len(id_law_map)
    
    for idx, (prec_id, default_law) in enumerate(id_law_map.items(), 1):
        detail_xml = fetch_precedent_detail_xml(prec_id)

        if not detail_xml:
            print(f"  └ [{idx}/{total_len}] ID: {prec_id} -> API XML 응답 없음")
            continue

        # default_law 인자 추가 전달
        item = parse_precedent_detail(detail_xml, target_laws, default_law=default_law)

        if item:
            parsed_results.append(item)
            print(f"  └ [{idx}/{total_len}] ID: {prec_id} | {item['case_name'][:20]}...")
        else:
            print(f"  └ [{idx}/{total_len}] ID: {prec_id} -> 파싱 결과가 None (태그 추출 실패)")

        time.sleep(0.05)

    # DB 저장
    print("DB 저장")
    upsert_precedents(parsed_results)
    
    print(">> 파이프라인 종료 <<")
    
if __name__ == "__main__":
    TARGET_LAWS = [
        # 핵심 법률명
        "근로기준법",
        "근로자퇴직급여 보장법",
        "최저임금법",
        "임금채권보장법",
        
        # 입금/ 수당 / 퇴직금 주요 주제
        "임금체불",
        "체불임금",
        "통상임금",
        "평균임금",
        "포괄임금",
        "포괄임금제",
        "연장근로수당",
        "야간근로수당",
        "휴일근로수당",
        "시간외수당",
        "연차유급휴가수당",
        "연차수당",
        "주휴수당",
        "퇴직금",
        "퇴직위로금",
        "상여금",
        "성과급",
        "최저임금",
        "휴업수당",
        "해고예고수당",
        
        # 금전 청구 / 공제 / 채권 관련 키워드
        "임금 삭감",
        "임금 반납",
        "임금 공제",
        "임금 채권",
        "대지급금",  # (구 소액체당금)
        "체당금",
        "손해배상" # 사용자/근로자 간 금전 손해배상 청구 판례
        "부당이득반환", # 초과 지급된 임금 반환 등
        "임금 청구",
        "퇴직금 청구"
    ]
    
    run_pipeline(TARGET_LAWS)
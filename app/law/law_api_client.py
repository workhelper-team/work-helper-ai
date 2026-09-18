import os
import xml.etree.ElementTree as ET
from typing import Tuple
from urllib.parse import quote
import requests


class LawAPIClient:
    """국가법령정보 OpenAPI 통신 전담 클래스"""

    BASE_URL = "http://www.law.go.kr/DRF"

    def __init__(self, oc_key: str | None = None):
        self.oc_key = oc_key or os.getenv("LAW_OPENAPI_OC")
        if not self.oc_key:
            raise ValueError("LAW_OPENAPI_OC 인증키가 설정되지 않았습니다.")

    def fetch_law_xml(self, law_name: str) -> Tuple[str, bytes]:
        # 1. 법령 검색 API 호출 (검색어 URL 인코딩)
        encoded_query = quote(law_name)
        search_url = f"{self.BASE_URL}/lawSearch.do?OC={self.oc_key}&target=law&type=XML&query={encoded_query}"

        res = requests.get(search_url)
        res.raise_for_status()

        root = ET.fromstring(res.content)

        # 응답 에러 체크 (키 오류 등)
        result_msg = root.findtext(".//resultMsg") or root.findtext(
            ".//result"
        )
        if result_msg and "성공" not in result_msg and "OK" not in result_msg:
            print(f"   [API 응답 메시지]: {result_msg}")

        # 2. 검색 목록에서 정확한 법령의 ID(MST) 탐색
        target_mst = None

        # 목록 아이템 탐색 (<law> 태그)
        for law_node in root.findall(".//law"):
            name = (law_node.findtext("법령명_한글") or "").strip()
            mst = (law_node.findtext("법령일련번호") or "").strip()

            if name == law_name and mst:
                target_mst = mst
                break

        # 정확히 일치하는 명칭을 못 찾았을 경우 첫 번째 법령일련번호 추출
        if not target_mst:
            first_mst_node = root.find(".//법령일련번호")
            if first_mst_node is not None and first_mst_node.text:
                target_mst = first_mst_node.text.strip()

        if not target_mst:
            # 실패 원인 파악을 위해 수신된 XML 일부 출력
            raw_preview = res.text[:300].replace("\n", "")
            raise ValueError(
                f"'{law_name}'에 해당하는 법령일련번호(MST)를 찾을 수 없습니다. (응답: {raw_preview})"
            )

        # 3. 법령 상세 본문 API 호출
        detail_url = f"{self.BASE_URL}/lawService.do?OC={self.oc_key}&target=law&type=XML&MST={target_mst}"
        detail_res = requests.get(detail_url)
        detail_res.raise_for_status()

        return target_mst, detail_res.content
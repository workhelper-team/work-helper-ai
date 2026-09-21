import json
import xml.etree.ElementTree as ET
from typing import Any, Dict, List

## 가져온 법령 정보의 조문내용과 항/호 단위 텍스트를 추출하여 테이블 스키마에 맞춰 변형하는 함수
def parse_to_documents_schema(law_id: str, xml_content: bytes) -> Dict[str, Any]:
    
    # XML 원문을 legal_documents 테이블 스키마 포맷으로 추출
    root = ET.fromstring(xml_content)
    title = root.findtext(".//법령명_한글", "노동관계법률")

    full_text_list: List[str] = []

    # 조문 및 항 단위 텍스트 추출 및 결합
    for article in root.findall(".//조문단위"):
        art_content = article.findtext("조문내용", "").strip()
        sub_contents = [
            p.findtext("항내용", "").strip()
            for p in article.findall(".//항")
            if p.findtext("항내용")
        ]

        if art_content:
            full_text_list.append(f"{art_content}\n" + "\n".join(sub_contents))

    full_text = "\n\n".join(full_text_list)

    return {
        "source_type": "LAW",
        "source_id": f"LAW_{law_id}",
        "title": title,
        "full_text": full_text,
        "source_url": f"https://www.law.go.kr/법령/{title}",
        "metadata": json.dumps(
            {"law_id": law_id, "category": "labor"}, ensure_ascii=False
        ),
    }
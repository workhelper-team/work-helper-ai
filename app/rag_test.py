from dotenv import load_dotenv

from app.services.chain import labor_rag_pipeline

load_dotenv()

## 근로자 상담 전용 RAG 엔드포인트
def process_labor_consultation(user_question: str) -> str:
    try:
        response = labor_rag_pipeline(user_question)
        return response
    except Exception as e:
        return f"상담 처리 중 오류가 발생했습니다.: {str(e)}"

## RAG 파이프라인 테스트
def test_pipeline():
    test_cases = [
        # 케이스 1 : 욕설 검증
        "야 이 개새끼들이 돈 안주는데 어떻게 함?",
        
        # 케이스 2 : 도메인 이탈
        "맛있는 김치찌개 레시피 좀 알려줘",
        
        # 케이스 3 : 단순 법령/개념 질문 (판례 미검색)
        "근로기준법상 주휴수당의 정의와 지급 조건이 무엇인가요?",
        
        # 케이스 4 : 구체적 분쟁 상담 (법령 + 판례 검색)
        "수습기간 2달 차인데 사장이 오늘 갑자기 내일부터 나오지 말라고 합니다. 서명하라는 종이도 줬는데 서명해야 하나요?"
    ]
    
    for idx, question in enumerate(test_cases, 1):
        print("=" * 60)
        print(f"[테스트 케이스 {idx}] 질문: {question}")
        print("=" * 60)
        
        answer = process_labor_consultation(question)
        print(answer)
        print("\n")

if __name__ == "__main__":
    test_pipeline()
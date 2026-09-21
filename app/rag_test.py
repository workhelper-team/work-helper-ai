from dotenv import load_dotenv
from app.services.chain import generate_rag_response

load_dotenv()

if __name__ == "__main__":
    user_question = "부당해고를 당했을 때 중앙노동위원회에 구제신청을 할 수 있는 기간은 언제까지인가요?"
    
    print(f" 질문: {user_question}\n")
    print(" 답변 생성 중...")
    
    answer = generate_rag_response(user_question)
    
    print("\n" + "="*50)
    print("=== LLM RAG 답변 ===")
    print("="*50)
    print(answer)
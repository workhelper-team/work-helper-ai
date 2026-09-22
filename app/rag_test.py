from dotenv import load_dotenv
from app.services.chain import generate_rag_response

load_dotenv()

if __name__ == "__main__":
    user_question = "6개월 근무 후 퇴직했는데 퇴직금을 못받았습니다. 어떻게 해야 하나요?"
    
    print(f" 질문: {user_question}\n")
    print(" 답변 생성 중...")
    
    answer = generate_rag_response(user_question)
    
    print("\n" + "="*50)
    print("=== LLM RAG 답변 ===")
    print("="*50)
    print(answer)
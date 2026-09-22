from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from app.db.retriever import search_similar_chunks

RAG_PROMPT_TEMPLATE = """
당신은 대한민국 법률 전문가입니다. 아래 제공된 [법령 및 판례 컨텍스트]만을 바탕으로 사용자의 질문에 명확하고 정확하게 답변하세요.
컨텍스트에 직접적인 관련 내용이 없다면 솔직하게 알 수 없다고 답변하고, 절대로 추측해서 거짓 정보를 만들어내지 마세요.
답변할 때는 관련된 판례 사건번호나 법령 조문이 있다면 함께 명시해 주세요.

[법령 및 판례 컨텍스트]:
{context}

[사용자 질문]:
{question}
"""

## 사용자의 질문을 RAG 파이프라인을 거쳐 최종 답변을 반환
def generate_rag_response(question: str) -> str:
    # 1. 질문과 유사한 청크 TOP-4 조회
    retrieved_chunks = search_similar_chunks(question, top_k=4)
    
    if not retrieved_chunks:
        return "관련된 법령이나 판례 정보를 찾을 수 없습니다."
    
    # 2. 검색된 청크 텍스트 하나로 병합
    context_text = "\n\n".join([
        f"[참고] {idx+1}\n{chunk['content']}"
        for idx, chunk in enumerate(retrieved_chunks)
    ])
    
    # 3. LangChain 구성
    prompt = ChatPromptTemplate.from_template(RAG_PROMPT_TEMPLATE)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    output_parser = StrOutputParser()
    
    chain = prompt | llm | output_parser
    
    # 4. 체인 실행
    response = chain.invoke({
        "context": context_text,
        "question": question
    })
    
    return response
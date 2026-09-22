import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

from app.db.retriever import search_legal_context
from app.prompts.consultation_prompt import (
    PROFANITY_PROMPT,
    DOMAIN_CHECK_PROMPT,
    QUERY_REWRITE_PROMPT,
    ANALYSIS_PROMPT,
    FINAL_RESPONSE_PROMPT
)

## LLM 선언
llm_json = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind(response_format={"type": "json_object"})
llm_text = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

def labor_rag_pipeline(user_input: str) -> str:
    parser = JsonOutputParser()
    
    # 1. 욕설/비속어 검증
    profanity_chain = ChatPromptTemplate.from_template(PROFANITY_PROMPT) | llm_json | parser
    profanity_res = profanity_chain.invoke({"user_input": user_input})
    if not profanity_res.get("is_safe", True):
        return "질문하신 내용에 부적절한 표현이 감지되었습니다. 올바른 언어 사용을 부탁드리며 다시 질문해주시길 바랍니다."

    # 2. 도메인 적합성 검증
    domain_chain = ChatPromptTemplate.from_template(DOMAIN_CHECK_PROMPT) | llm_json | parser
    domain_res = domain_chain.invoke({"user_input": user_input})
    if not domain_res.get("is_labor_domain", True):
        return "저는 법률 상담 챗봇입니다. 법령 정보에 대해 궁금하거나 노무 관련 법률 상담이 필요하신가요? 언제든지 물어봐주세요!"
    
    # 3. 일상 용어 -> 법률 용어로 재작성 및 의도 분류
    rewrite_chain = ChatPromptTemplate.from_template(QUERY_REWRITE_PROMPT) | llm_json | parser
    rewrite_res = rewrite_chain.invoke({"user_input": user_input})
    
    rewritten_query = rewrite_res.get("rewritten_query") # 재작성된 사용자 질문
    intent = rewrite_res.get("intent") # 사용자의 질문 의도 (법령 개념 or 법률 상담)
    
    # CASE_DISPUTE(분쟁) 시에만 판례 검색 포함
    include_precedents = (intent == "CASE_DISPUTE")
    
    print(f"👉 [3단계 의도 분류]: {intent}")
    print(f"👉 [3단계 재작성 쿼리]: {rewritten_query}")
    
    # 4. DB 검색 및 사실 분석
    retrieved_data = search_legal_context(
        query=rewritten_query,
        top_k_law=3,
        top_k_precedent=2,
        include_precedents=include_precedents
    )
    
    print(f"👉 [검색된 법령 개수]: {len(retrieved_data['laws'])}")
    print(f"👉 [검색된 판례 개수]: {len(retrieved_data['precedents'])}")
    
    # 컨텍스트 문자 결합
    context_str = "[관련 법령]\n"
    for law in retrieved_data["laws"]:
        context_str += f"- {law['content']}\n"
        
    if include_precedents and retrieved_data["precedents"]:
        context_str += "\n[관련 판례]\n"
        for prec in retrieved_data["precedents"]:
            context_str += f"- {prec['content']}\n"
            
    analysis_chain = ChatPromptTemplate.from_template(ANALYSIS_PROMPT) | llm_json | parser
    analysis_res = analysis_chain.invoke({
        "context": context_str,
        "question": rewritten_query
    })
    
    # 5. 최종 답변
    final_chain = ChatPromptTemplate.from_template(FINAL_RESPONSE_PROMPT) | llm_text | StrOutputParser()
    final_res = final_chain.invoke({
        "analysis_data": json.dumps(analysis_res, ensure_ascii=False, indent=2)
    })
    
    return final_res
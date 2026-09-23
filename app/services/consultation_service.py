import json
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

from app.db.retriever import search_legal_context
from app.schemas.consultation_schema import ConsultationResponse
from app.utils.formatters import format_full_chat_history
from app.prompts.consultation_prompt import (
    PROFANITY_PROMPT, # 욕설/비속어 포함 여부 필터링
    DOMAIN_CHECK_PROMPT, # 노동/노무 관련 질문인지 필터링
    QUERY_REWRITE_PROMPT, # 일상 용어를 법령 용어로 재작성 및 의도 분석
    ANALYSIS_PROMPT, # 법령 컨텍스트 기반 사실 분석
    FINAL_RESPONSE_PROMPT, # 사용자 질문에 대한 AI 최종 답변
    PRECEDENT_SUMMARY_PROMPT # 판례 판결내용 요약
)

## LLM 선언
llm_json = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind(response_format={"type": "json_object"})
llm_text = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

async def labor_rag_pipeline(user_input: str) -> str:
    parser = JsonOutputParser()
    
    # 1. 욕설/비속어 검증
    profanity_chain = ChatPromptTemplate.from_template(PROFANITY_PROMPT) | llm_json | parser
    profanity_res = profanity_chain.invoke({"user_input": user_input})
    
    if not profanity_res.get("is_safe", True):
        return ConsultationResponse(
            answer="질문하신 내용에 부적절한 표현이 감지되었습니다. 올바른 언어 사용을 부탁드리며 다시 질문해주시길 바랍니다.",
            precedents=[]
        )

    # 2. 도메인 적합성 검증
    domain_chain = ChatPromptTemplate.from_template(DOMAIN_CHECK_PROMPT) | llm_json | parser
    domain_res = domain_chain.invoke({"user_input": user_input})
    
    if not domain_res.get("is_labor_domain", True):
        return ConsultationResponse(
            answer="법령 정보에 대해 궁금하거나 노무 관련 법률 상담이 필요하신가요? '근로기준법에 대해 궁금합니다'와 같이 질문해보세요.",
            precedents=[]
        )
    
    # 3. 일상 용어 -> 법률 용어로 재작성 및 의도 분류
    rewrite_chain = ChatPromptTemplate.from_template(QUERY_REWRITE_PROMPT) | llm_json | parser
    rewrite_res = rewrite_chain.invoke({"user_input": user_input})
    
    rewritten_query = rewrite_res.get("rewritten_query") # 재작성된 사용자 질문
    intent = rewrite_res.get("intent") # 사용자의 질문 의도 (법령 개념 or 법률 상담)
    include_precedents = (intent == "CASE_DISPUTE") # CASE_DISPUTE(분쟁) 시에만 판례 검색 포함
    
    # 4. DB 검색 및 사실 분석
    retrieved_data = search_legal_context(
        query=rewritten_query,
        top_k_law=3,
        top_k_precedent=3,
        include_precedents=include_precedents
    )
    
    # 4-1. 법령 컨텍스트 생성
    law_context_str = ""
    for law in retrieved_data["laws"]:
        law_context_str += f"- {law['content']}\n"
            
    # 4-2. 법령 기반 사실 분석 실행
    analysis_chain = ChatPromptTemplate.from_template(ANALYSIS_PROMPT) | llm_json | parser
    analysis_res = analysis_chain.invoke({
        "context": law_context_str,
        "question": rewritten_query
    })
    
    # 4-3. 판례가 있을 경우 판결 전문을 요약하고 API 스키마 규격에 맞춰 데이터 재구성
    precedents_list = []
    if include_precedents and retrieved_data.get("precedents"):
        prec_summary_chain = ChatPromptTemplate.from_template(PRECEDENT_SUMMARY_PROMPT) | llm_text | StrOutputParser()
        
        for prec in retrieved_data["precedents"]:
            metadata = prec.get("metadata", {})
            raw_content = prec.get("content", "")
            
            summarized_content = prec_summary_chain.invoke({"precedent_content": raw_content})
            
            precedents_list.append({
                "case_number": metadata.get("case_number", ""),
                "case_name": metadata.get("case_name", ""),
                "court_name": metadata.get("court_name", ""),
                "judgment_date": metadata.get("judgment_date", ""),
                "judgment_type": metadata.get("judgment_type", ""),
                "content": summarized_content
            })
    
    # 5. 최종 답변
    final_chain = ChatPromptTemplate.from_template(FINAL_RESPONSE_PROMPT) | llm_text | StrOutputParser()
    answer_text = final_chain.invoke({
        "analysis_data": json.dumps(analysis_res, ensure_ascii=False, indent=2)
    })
    
    return ConsultationResponse(
        answer=answer_text,
        precedents=precedents_list
    )
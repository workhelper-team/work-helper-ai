import json
import asyncio
from typing import List
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser

from app.db.retriever import search_legal_context
from app.db.reranker import rerank_documents
from app.schemas.consultation_schema import ConsultationResponse, ConsultationRequest, Precedents
from app.utils.formatters import format_full_chat_history
from app.utils.profanity_filter import contains_profanity
from app.prompts.consultation_prompt import (
    DOMAIN_CHECK_PROMPT, # 노동/노무 관련 질문인지 필터링
    QUERY_REWRITE_PROMPT, # 일상 용어를 법령 용어로 재작성 및 의도 분석
    ANALYSIS_PROMPT, # 법령 컨텍스트 기반 사실 분석
    FINAL_RESPONSE_PROMPT, # 사용자 질문에 대한 AI 최종 답변
    PRECEDENT_SUMMARY_PROMPT # 판례 판결내용 요약
)

## LLM 선언
# 도메인 적합성 검증 모델
domain_llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
# 법률 용어로 쿼리 재작성 및 의도 분리
rewrite_llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
# 법률 기반 사건 분석 모델
analysis_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind(response_format={"type": "json_object"})
# 최종 답변 모델
answer_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

## 파이프라인 시작 (비동기 처리)
async def labor_rag_pipeline(request: ConsultationRequest) -> ConsultationResponse:
    
    parser = JsonOutputParser()
    
    # 0. 데이터 준비
    full_chat_history = format_full_chat_history(request.chat_history or []) # 전체 이전 대화 기록
    question = request.question # 사용자 질문
    
    # 1. 욕설/비속어 검증
    if contains_profanity(question):
        return ConsultationResponse(
            answer="질문하신 내용에 부적절한 표현이 감지되었습니다. 올바른 언어 사용을 부탁드리며 다시 질문해주시길 바랍니다.",
            precedents=[]
        )
    
    # 2. 도메인 적합성 검증
    domain_chain = ChatPromptTemplate.from_template(DOMAIN_CHECK_PROMPT) | domain_llm | StrOutputParser()
    raw_domain_res = await domain_chain.ainvoke({"user_input": question})
    try:
        domain_res = json.loads(raw_domain_res.strip())
    except json.JSONDecodeError:
        domain_res = {"is_labor_domain": False} # 예외 발생 시 기본 통과 처리
    
    if not domain_res.get("is_labor_domain", True):
        return ConsultationResponse(
            answer="법령 정보에 대해 궁금하거나 노무 관련 법률 상담이 필요하신가요? '근로기준법에 대해 궁금합니다'와 같이 질문해보세요.",
            precedents=[]
        )
    
    # 3. 일상 용어 -> 법률 용어로 재작성 및 의도 분류
    rewrite_chain = ChatPromptTemplate.from_template(QUERY_REWRITE_PROMPT) | rewrite_llm | StrOutputParser()
    raw_rewrite_res = await rewrite_chain.ainvoke({
        "full_chat_history":full_chat_history,
        "question": question
    })
    
    try:
        rewrite_res = json.loads(raw_rewrite_res.strip())
    except json.JSONDecodeError:
        return ConsultationResponse(
            answer="답변을 생성하는 과정에서 예기치 못한 에러가 발생했습니다. 계속 문제가 발생한다면 관리자에게 문의해주세요.",
            precedents=[]
        )
    print(rewrite_res)
    
    rewritten_query = rewrite_res.get("rewritten_query") # 재작성된 사용자 질문
    intent = rewrite_res.get("intent") # 사용자의 질문 의도 (법령 개념 or 법률 상담)
    include_precedents = (intent == "CASE_DISPUTE") # CASE_DISPUTE(분쟁) 시에만 판례 검색 포함
    
    # 4. [RAG 1단계] 하이브리드 RAG DB 검색 (BM25 + pgvector 융합된 RRF 방식)
    # Reranker 검증을 위해 법령/판례 각각 10개씩 검색
    candidate_data = search_legal_context(
        query=rewritten_query,
        candidate_k_law=10, # 1차 법령 후보군 10개
        candidate_k_precedent=10, # 1차 판례 후보군 10개
        include_precedents=include_precedents
    )
    
    # 4-1. [RAG 2단계] Cross-Encoder Reranking (정밀 재점수화)
    # BGE-M3 Reranker로 10개 후보를 검증하여 질문과 진짜 관련 높은 상위 문서만 잘라냄
    # 법령 10개 후보 중 Cross-Encoder 점수 상위 3개 선별
    final_laws = rerank_documents(
        query=rewritten_query,
        documents=candidate_data["laws"],
        top_k=3
    )
    
    # 판례 10개 후보 중 Cross-Encoder 점수 상위 2개 선별
    final_precedents = []
    if include_precedents and candidate_data.get("precedents"):
        final_precedents = rerank_documents(
            query=rewritten_query,
            documents=candidate_data["precedents"],
            top_k=2
        )
        
    # 4-2. 재정렬된 최종 법령(Top-3) 컨텍스트 생성
    law_context_str = ""
    for law in final_laws:
        law_context_str += f"- {law['content']}\n"
            
    # 4-3. 법령 기반 사실 분석 실행
    analysis_chain = ChatPromptTemplate.from_template(ANALYSIS_PROMPT) | analysis_llm | parser
    analysis_res = await analysis_chain.ainvoke({
        "context": law_context_str,
        "question": rewritten_query
    })
    
    # 4-4. 판례가 있을 경우 판결 전문 요약 및 스키마 규격 변환
    precedents_list: List[Precedents] = []
    
    if include_precedents and final_precedents:
        prec_summary_chain = ChatPromptTemplate.from_template(PRECEDENT_SUMMARY_PROMPT) | answer_llm | StrOutputParser()
        
        # 사건 번호(case_number) 기준 중복 제거
        seen_case_numbers = set()
        unique_precedents =[]
        
        for prec in final_precedents:
            metadata = prec.get("metadata")
            case_no = metadata.get("case_number")
            if case_no and case_no in seen_case_numbers:
                continue
            seen_case_numbers.add(case_no)
            unique_precedents.append(prec)
            
        # 개별 판례 비동기 요약 태스크 생성
        async def summarize_single_precedent(prec: dict) -> Precedents:
            metadata = prec.get("metadata")
            raw_content = prec.get("content")
            
            # 비동기 LLM 요약 호출
            summarized_content = await prec_summary_chain.ainvoke({"precedent_content": raw_content})
            
            return Precedents(
                case_number=metadata.get("case_number", ""),
                case_name=metadata.get("case_name", ""),
                court_name=metadata.get("court_name", ""),
                judgment_data=metadata.get("judgment_date", ""),
                judgment_type=metadata.get("judgment_type", ""),
                content=summarized_content
            )
            
        # asyncio.gather로 판례를 비동기 동시 요약 (병렬 처리)
        precedents_list = await asyncio.gather(
            *[summarize_single_precedent(prec) for prec in unique_precedents]
        )
    
    # 5. 최종 답변 생성
    final_chain = ChatPromptTemplate.from_template(FINAL_RESPONSE_PROMPT) | answer_llm | StrOutputParser()
    answer_text = await final_chain.ainvoke({
        "full_chat_history": full_chat_history,
        "analysis_data": json.dumps(analysis_res, ensure_ascii=False, indent=2)
    })
    
    # 6. API 스키마 반환
    return ConsultationResponse(
        answer=answer_text,
        precedents=list(precedents_list)
    )
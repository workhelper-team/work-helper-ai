from typing import List
from langchain_core.output_parsers import StrOutputParser

from app.db.vector_client import get_retriever
from app.services.llm_service import get_llm
from app.prompts.consultation_prompt import get_consultation_prompt_template
from app.schemas.rag_schema import ConsultationRequest, ConsultationResponse, LegalReference


def format_docs(docs) -> str:
    """검색된 문서 청크들을 프롬프트 주입용 단일 문자열로 가공합니다."""
    formatted_chunks = []
    for doc in docs:
        law = doc.metadata.get("law", "법률")
        article = doc.metadata.get("article", "")
        header = f"[{law} {article}]" if article else f"[{law}]"
        formatted_chunks.append(f"{header}\n{doc.page_content}")
    return "\n\n".join(formatted_chunks)


def parse_legal_references(docs) -> List[LegalReference]:
    """검색된 문서들의 메타데이터를 기반으로 LegalReference 리스트를 구성합니다."""
    references = []
    for doc in docs:
        law = str(doc.metadata.get("law", "관련 법령"))
        article_val = doc.metadata.get("article")
        article = str(article_val) if article_val is not None else None
        
        references.append(
            LegalReference(
                law=law,
                article=article,
                content=doc.page_content.strip(),
            )
        )
    return references


async def generate_legal_consultation(request: ConsultationRequest) -> ConsultationResponse:
    """RAG 파이프라인을 실행하여 구조화된 법률 상담 응답을 생성합니다."""
    retriever = get_retriever(k=3)
    docs = retriever.invoke(request.question)

    context_str = format_docs(docs) if docs else "관련된 직접적인 법률 조항이 검색되지 않았습니다."

    prompt = get_consultation_prompt_template()
    llm = get_llm()
    chain = prompt | llm | StrOutputParser()

    raw_answer = await chain.ainvoke({
        "context": context_str,
        "question": request.question,
    })

    references = parse_legal_references(docs)

    return ConsultationResponse(
        answer=raw_answer.strip(),
        issues=["임금/수당 미지급", "근로시간 판단"] if "주휴" in request.question or "수당" in request.question else ["노동관계법 검토"],
        references=references,
        follow_up_questions=[
            "주당 소정근로시간이 15시간 이상인가요?",
            "약정된 소정근로일을 개근하셨나요?"
        ] if "주휴" in request.question else [
            "구체적인 근로계약서 작성 여부와 사업장 상시 근로자 수를 알려주실 수 있나요?"
        ],
    )
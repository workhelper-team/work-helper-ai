from typing import List, Dict, Any, Optional
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

from app.db.connection import get_db_connection
from app.db.embeddings import generate_embeddings

## -------------------------------
## ----- OCR 증거 분석에서 사용 -----
## -------------------------------

# 사용자의 질문을 임베딩하여 유사도가 높은 법령 청크를 검색
def search_similar_chunks(query: str, top_k: int = 4) -> List[Dict]:
    
    # 1. 사용자 질문 임베딩
    query_embedding = generate_embeddings([query])[0]
    
    # 2. DB에서 코사인 유사도 기반 TOP-K 검색
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            sql = """
            SELECT
                content,
                metadata,
                (embedding <=> %s::vector) as distance
            FROM rag.legal_chunks
            ORDER BY distance ASC
            LIMIT %s;
            """
            cursor.execute(sql, (str(query_embedding), top_k))
            results = cursor.fetchall()
            
            return [
                {
                    "content": row[0],
                    "metadata": row[1],
                    "score": row[2]
                }
                for row in results
            ]

## -------------------------------
## --- AI 노무 법률 상담에서 사용 ---
## -------------------------------

## 1. BM25 인덱스 메모리 캐싱 (싱글톤 전역 변수)
# 매 검색 요청마다 DB의 모든 문서를 읽고 BM25 인덱스를 만들면 속도가 수 초 이상 늦어지므로,
# 서버 시작 시 1회만 메모리에 캐싱하여 0.01초 만에 검색되도록 구성
_GLOBAL_LAW_BM25: Optional[BM25Retriever] = None
_GLOBAL_PRECEDENT_BM25: Optional[BM25Retriever] = None

## 2. 최초 실행 시 DB의 전체 청크를 가져와 법령과 판례 각각의 BM25 리트리버를 메모리에 생성
def init_bm25_retrievers():
    global _GLOBAL_LAW_BM25, _GLOBAL_PRECEDENT_BM25
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 2-1. 법령 전체 데이터 로드 및 BM25 인덱싱
            cursor.execute("SELECT content, metadata FROM rag.legal_chunks;")
            law_rows = cursor.fetchall()
            
            # 읽어온 원시 데이터를 LangChain Document 객체 리스트 반환
            law_docs = [
                Document(page_content=row[0], metadata=row[1] or {})
                for row in law_rows
            ]
            
            # 법령 Document 리스트 기반으로 BM25 인덱스 생성
            if law_docs:
                _GLOBAL_LAW_BM25 = BM25Retriever.from_documents(law_docs)
                
            # 2-2. 판례 전체 데이터 로드 및 BM25 인덱싱
            cursor.execute("SELECT content, metadata FROM rag.precedent_chunks;")
            prec_rows = cursor.fetchall()
            
            # 읽어온 원시 데이터를 LangChain Document 객체 리스트 반환
            prec_docs = [
                Document(page_content=row[0], metadata=row[1] or {})
                for row in prec_rows
            ]
            
            # 법례 Document 리스트 기반으로 BM25 인덱스 생성
            if prec_docs:
                _GLOBAL_PRECEDENT_BM25 = BM25Retriever.from_documents(prec_docs)
                
## 3. Vector 검색 결과와 BM25 키워드 검색 결과를 RRF(Reciprocal Rank Fusion)하고
## 중복 문서를 제거한 후 최종 스코어 순으로 정렬
def _combine_hybird_results(
    vector_results: List[Dict[str, Any]], bm25_docs: List[Document],
    vector_weight: float = 0.6, bm25_weight: float = 0.4) -> List[Dict[str, Any]]:
    
    combined_dict = {} # 문서 내용을 Key로 사용해 중복 제거
    
    # 3-1. Vector 검색 결과 점수 반영
    # Vector Distance는 작을수록 유사하므로 score = 1 / (1 + distance) 변환
    for rank, item in enumerate(vector_results):
        content = item["content"]
        # 순위 기반 RRF 스코어 계산
        rrf_score = vector_weight * (1.0 / (60 * rank + 1))
        
        combined_dict[content] = {
            "content": content,
            "metadata": item["metadata"],
            "score": rrf_score
        }
        
    # 3-2. BM25 검색 결과 점수 합산
    for rank, doc in enumerate(bm25_docs):
        content = doc.page_content
        rrf_score = bm25_weight * (1.0 / (60 * rank + 1))
        
        # 이미 vector 결과에 존재하는 문서의 경우 점수 합산 (키워드 + 의미 둘다 부합)
        if content in combined_dict:
            combined_dict[content]["score"] += rrf_score
        else:
            # BM25만 걸린 문서인 경우 새로 추가
            combined_dict[content] = {
                "content": content,
                "metadata": doc.metadata,
                "score": rrf_score
            }  
            
    # 3-3. 최종 융합 점수를 내림차순으로 정렬하여 리스트로 반환
    sorted_results = sorted(combined_dict.values(), key=lambda x: x["score"], reverse=True)
    return sorted_results

## 4. 하이브리드 RAG 파이프라인 (Vector + BM25)
def search_legal_context(
    query: str,
    top_k_law: int = 3,
    top_k_precedent: int = 2,
    include_precedents: bool = True,
    vector_weight: float = 0.6, # Vector 검색 가중치 60%
    bm25_weight: float = 0.4 # BM25 검색 가중치 40%
) -> Dict[str, List[Dict]]:
    
    # 만약 BM25 전역 리트리버가 아직 초기화되지 않았다면 1회 자동 실행
    if _GLOBAL_LAW_BM25 is None:
        init_bm25_retrievers()
    
    # 1. 사용자 질문 텍스트 임베딩 후 벡터 생성
    query_embedding = generate_embeddings([query])[0]
    results = {"laws": [], "precedents": []} # 최종 반환할 딕셔너리 구조 초기화
    
    # 2. DB 연결 및 pgvector 코사인 거리(Vector) 검색 수행
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            
            # 2-1. 법령 하이브리드 검색
            # Vector 검색 SQL 실행
            law_sql = """
                SELECT content, metadata, (embedding <=> %s::vector) AS distance
                FROM rag.legal_chunks
                ORDER BY distance ASC
                LIMIT %s;
            """
            cursor.execute(law_sql, (str(query_embedding), top_k_law * 2)) # 융합을 위해 상위 K의 2배수 추출
            vector_laws = [
                {"content": row[0], "metadata": row[1], "score": row[2]}
                for row in cursor.fetchall()
            ]
            
            # BM25 키워드 검색 실행
            _GLOBAL_LAW_BM25.k = top_k_law * 2 # BM25 추출 개수 설정
            bm25_laws = _GLOBAL_LAW_BM25.invoke(query) # 검색 메소드 호출
            
            # Vector 결과 + BM25 결과 융합 (RRF 방식 적용)
            combined_laws = _combine_hybird_results(
                vector_results=vector_laws,
                bm25_docs=bm25_laws,
                vector_weight=vector_weight,
                bm25_weight=bm25_weight
            )
            
            # 요청 받은 top_k_law 개수만큼 상위 청크 슬라이싱
            results["laws"] = combined_laws[:top_k_law]
            
            # 2-2. 판례 하이브리드 검색 (분쟁 질문일 경우만)
            if include_precedents and _GLOBAL_PRECEDENT_BM25 is not None:
                # Vector 검색 SQL 실행
                prec_sql = """
                    SELECT content, metadata, (embedding <=> %s::vector) AS distance
                    FROM rag.precedent_chunks
                    ORDER BY distance ASC
                    LIMIT %s;
                """
                cursor.execute(prec_sql, (str(query_embedding), top_k_precedent * 2)) # 융합을 위해 상위 K의 2배수 추출
                vector_precedents = [
                    {"content": row[0], "metadata": row[1], "score": row[2]}
                    for row in cursor.fetchall()
                ]
                
                # BM25 키워드 검색 실행
                _GLOBAL_PRECEDENT_BM25.k = top_k_precedent * 2 # BM25 추출 개수 설정
                bm25_precedents = _GLOBAL_PRECEDENT_BM25.invoke(query)
                
                # Vector 결과 + BM25 결과 융합 (RRF 방식 적용)
                combined_precedents = _combine_hybird_results(
                    vector_results=vector_precedents,
                    bm25_docs=bm25_precedents,
                    vector_weight=vector_weight,
                    bm25_weight=bm25_weight
                )
                
                # 요청 받은 top_k_precedent 개수만큼 상위 청크 슬라이싱
                results["precedents"] = combined_precedents[:top_k_precedent]
    
    # 3. 최종 결합 및 중복 제거된 법령/판례 검색 결과 반환
    return results
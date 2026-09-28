import torch
from typing import List, Dict, Any
from FlagEmbedding import FlagReranker

# BGE-M3 Reranker 싱글톤 전역 변수
# 서버 시작 시 1회만 모델을 메모리(CPU/GPU)에 로드하여 지연을 방지
_GLOBAL_RERANKER: FlagReranker = None

## Reranker 모델 객체를 반환
# Cross-Encoder 방식을 사용하여 질문과 문서 전체를 한 번에 입력받아 밀접도를 추론
def get_reranker() -> FlagReranker:
    global _GLOBAL_RERANKER
    if _GLOBAL_RERANKER is None:
        # GPU가 사용 가능한 지 확인
        use_gpu = torch.cuda.is_available()
        # BAAI/bge-reranker-v2-m3 모델 로드 (Cross-Encoder 기반)
        # use_fp16=True로 GPU 환경에서 메모리 절약 및 연산 속도 향상, CPU일 땐 False로 로드됨
        _GLOBAL_RERANKER = FlagReranker("BAAI/bge-reranker-v2-m3", use_fp16=use_gpu)
    return _GLOBAL_RERANKER

## Cross-Encoder 재점수화
# 1차 하이브리드 검색으로 넘어온 10~15개의 문서 후보군과 질문을 Cross-Encoder에 입력하여
# 질문과 문서 간의 정밀한 심층 연관성 스코어를 다시 계산하고 상위 top_k개만 추출
def rerank_documents(
    query: str,
    documents: List[Dict[str, Any]],
    top_k: int
) -> List[Dict[str, Any]]:
    # 후보군이 비어있으면 빈 리스트 반환
    if not documents:
        return []
    
    reranker = get_reranker()
    
    # 1. Cross-Encoder 입력 규격에 맞게 [질문, 문서내용] 쌍 리스트 생성
    # Cross-Encoder가 질문과 문서를 한 번에 레이어에 통과시켜 심층 관계를 파악
    pairs = [[query, doc["content"]] for doc in documents]
    
    # 2. Reranker 스코어 계산 (Cross-Encoder 점수 산출)
    # compute_score 함수는 각 [query, content] 쌍에 대한 float 점수를 리스트로 반환함
    scores = reranker.compute_score(pairs, normalize=True) # 0~1 사이의 값으로 정규화
    
    # 만약 단일 문서만 들어와서 scores가 float 단일 값으로 반한된 경우 리스트로 변환
    if isinstance(scores, float):
        scores = [scores]
        
    # 3. 문서 객체에 Reranker 계산 스코어 덮어씌우기
    for idx, doc in enumerate(documents):
        doc["rerank_score"] = float(scores[idx])
        
    # 4. Reranker 점수 기준 내림차순 정렬
    reranked_docs = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
    
    # 5. 최종 상위 top_k개 추출 후 반환
    return reranked_docs[:top_k]
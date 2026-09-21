# WorkHelper AI Server

법률/행정 지원 플랫폼 **WorkHelper**의 AI 전담 서버입니다. Spring Boot 메인 백엔드로부터 요청을 받아 OCR(문서 인식), 진정서 작성, 법령·판례 데이터 파싱 및 임베딩, Vector DB 기반 RAG 검색 워크플로우를 수행합니다.

## 현재 구현 범위

- OCR 기반 문서 인식
- LLM 기반 진정서 작성 및 상담 워크플로우
- 법령·판례 API 데이터 수집, 파싱 및 저장
- 문서 청크 생성 및 임베딩
- Vector DB 기반 법령·판례 검색(RAG)

## 기술 스택

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic / pydantic-settings

## 프로젝트 구조

```
app/
├── api/                         # FastAPI 라우터
│   └── v1/
│       ├── api.py
│       └── endpoints/
│           ├── health.py
│           ├── ocr.py
│           ├── consultation.py
│           ├── petition.py
│           └── rag.py
├── core/                        # 환경설정 및 LLM 설정
│   ├── config.py
│   └── llm.py
├── db/                          # DB 연결, 임베딩, Vector DB 클라이언트
│   ├── connection.py
│   ├── embeddings.py
│   └── vector_client.py
├── law/                         # 법령 데이터 수집·파싱·저장·임베딩
│   ├── law_api_client.py
│   ├── law_parser.py
│   ├── law_repository.py
│   ├── law_ingestion.py
│   └── law_chunk_ingestion.py
├── precedent/                   # 판례 데이터 수집·파싱·저장·임베딩
│   ├── precedent_api_client.py
│   ├── precedent_parser.py
│   ├── precedent_repository.py
│   ├── precedent_ingestion.py
│   └── precedent_chunk_ingestion.py
├── prompts/                     # LLM 프롬프트
│   ├── consultation_prompt.py
│   └── petition_prompt.py
├── schemas/                     # API 요청·응답 스키마
│   ├── consultation_schema.py
│   ├── ocr_schema.py
│   ├── petition_schema.py
│   └── rag_schema.py
├── services/                    # 도메인 서비스 및 워크플로우
│   ├── llm_service.py
│   ├── ocr_service.py
│   ├── petition_service.py
│   ├── rag_service.py
│   └── workflow_service.py
└── main.py                      # 애플리케이션 진입점
```

## 개발 환경 설정

### 1. 가상환경 생성 및 활성화

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

### 2. 의존성 설치

```powershell
pip install -r requirements.txt
```

### 3. 환경변수 설정

`.env.example` 파일을 복사하여 `.env` 파일을 생성하고 값을 채워주세요.

```powershell
copy .env.example .env
```

### 4. 서버 실행

```powershell
uvicorn app.main:app --reload
```

서버가 정상적으로 실행되면 아래 주소에서 확인할 수 있습니다.

- API: http://127.0.0.1:8000
- Swagger 문서: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/api/v1/health

# WorkHelper AI Server

법률/행정 지원 플랫폼 **WorkHelper**의 AI 전담 서버입니다. Spring Boot 메인 백엔드로부터 요청을 받아 OCR(문서 인식), Vector DB 기반 RAG(법령/판례 검색), LLM을 활용한 진정서 자동 작성 워크플로우를 수행합니다.

## 기술 스택

- Python 3.10+
- FastAPI
- Uvicorn
- Pydantic / pydantic-settings

## 프로젝트 구조

```
app/
├── api/
│   └── v1/
│       ├── api.py
│       └── endpoints/
│           ├── health.py
│           ├── ocr.py
│           ├── rag.py
│           └── petition.py
├── core/
│   └── config.py
├── db/
│   └── vector_client.py
├── prompts/
│   └── petition_prompt.py
├── schemas/
│   ├── ocr_schema.py
│   ├── rag_schema.py
│   └── petition_schema.py
├── services/
│   ├── ocr_service.py
│   ├── rag_service.py
│   ├── llm_service.py
│   └── workflow_service.py
└── main.py
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

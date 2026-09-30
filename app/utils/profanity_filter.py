import re # 정규표현식 처리를 위한 파이썬 표준 라이브러리

# 욕설/비속어 파일 경로
DEFAULT_FILE_PATH = "app/data/bad_words.txt"

_PROFANITY_REGEX = None # 비속어 매칭용 정규식 컴파일 객체
_IS_LOADED = False # 파일 로드 확인 플래그 변수

## bad_words.txt 파일에서 비속어를 읽어와 하나씩 정규식 패턴(A|B|C)으로 컴파일
## 서버 가동 시 메모리에 1회만 올려두고 사용
def load_profanity_dict(file_path: str = DEFAULT_FILE_PATH):
    global _PROFANITY_REGEX, _IS_LOADED
    
    try:
        words = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip()
                # 빈 줄이나 주석(#) 제외
                if word and not word.startswith("#"):
                    # 정규식 특수문(?, *, + 등)가 비속어에 들어있을 경우를 대비해 이스케이프 처리
                    words.append(re.escape(word))
                    
        if words:
            # 모든 욕설을 OR 형태로 묶어서 한번에 매칭하도록 정규식 컴파일
            pattern = "|".join(words)
            _PROFANITY_REGEX = re.compile(pattern)
            _IS_LOADED = True
            
    except FileNotFoundError:
        print(f"비속어 파일 탐색 실패")
        
## 공백 및 특수문자 제거 전처리
def _normalize_text(text: str) -> str:
    return re.sub(r"[^\w가-힣]", "", text)

## 사용자 질문 내 비속어 포함 여부 검사
def contains_profanity(text: str) -> bool:
    if not text:
        return False
    
    # 비속어 사전 로드 (최초 1회)
    if not _IS_LOADED:
        load_profanity_dict()
    
    # 단어장이 비어있거나 파일이 없으면 통과
    if _PROFANITY_REGEX is None:
        return False
    
    # 1. 원본 문장 검사
    if _PROFANITY_REGEX.search(text):
        return True
    
    # 2. 우회 문장 검사 (비속어 사이 특수문자로 우회방지)
    normalized = _normalize_text(text)
    if _PROFANITY_REGEX.search(normalized):
        return True

    return False
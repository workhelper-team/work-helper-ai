from typing import List, Optional
from app.schemas.consultation_schema import ConsultationMessage

## 이전 대화 기록 전체를 프롬프트용 텍스트로 변환
def format_full_chat_history(chat_history: Optional[List[ConsultationMessage]]) -> str:
    if not chat_history:
        return "이전 대화 기록 없음"
    
    formatted = []
    for msg in chat_history:
        role_label = "사용자" if msg.role and msg.role.upper() in ["USER", "ASSISTANT"] else "AI 상담사"
        formatted.append(f"{role_label}: {msg.content}")
        
    return "\n".join(formatted)
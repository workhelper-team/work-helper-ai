from fastapi import APIRouter

router = APIRouter()


@router.get("", summary="서버 상태 확인")
async def health_check() -> dict:
    """AI 서버가 정상적으로 동작 중인지 확인하는 헬스 체크 엔드포인트."""
    return {"status": "ok"}

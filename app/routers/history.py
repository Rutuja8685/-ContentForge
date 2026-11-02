"""History router – placeholder; fully implemented in Phase 6."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def history_ping():
    return {"router": "history", "status": "placeholder"}

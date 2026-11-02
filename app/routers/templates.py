"""Templates router – placeholder; fully implemented in Phase 6."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def templates_ping():
    return {"router": "templates", "status": "placeholder"}

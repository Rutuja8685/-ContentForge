"""Auth router – placeholder for Phase 6."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def auth_ping():
    """Health check for auth router."""
    return {"router": "auth", "status": "placeholder"}

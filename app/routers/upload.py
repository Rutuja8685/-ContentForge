"""Upload router – placeholder; fully implemented in Phase 4."""
from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def upload_ping():
    return {"router": "upload", "status": "placeholder"}

from fastapi import APIRouter

from app.core.response import APIResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=APIResponse)
async def health_check():
    return APIResponse.success(data={"status": "running"})

"""微信订阅消息结果保存接口。"""
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.response import APIResponse
from app.db.database import get_db
from app.models.subscription import UserSubscription

logger = logging.getLogger("subscribe")

router = APIRouter(prefix="/api/wechat", tags=["wechat"])


class SubscribeResultRequest(BaseModel):
    template_id: str = Field(..., description="订阅消息模板ID")
    status: str = Field(..., description="accept / reject / ban")


@router.post("/subscribe-result", response_model=APIResponse)
async def save_subscribe_result(
    req: SubscribeResultRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """保存用户对订阅消息的授权结果。

    前端调用 wx.requestSubscribeMessage 后，将结果 POST 到此接口。
    后端根据当前 token 解析 openid，UPSERT 订阅状态。
    """
    user_id = current_user["openid"]

    # UPSERT
    result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.template_id == req.template_id,
        )
    )
    sub = result.scalar_one_or_none()

    if sub:
        sub.status = req.status
        logger.info("[订阅] 更新订阅状态 user_id=%s template_id=%s status=%s", user_id, req.template_id, req.status)
    else:
        sub = UserSubscription(
            user_id=user_id,
            template_id=req.template_id,
            status=req.status,
        )
        db.add(sub)
        logger.info("[订阅] 新建订阅记录 user_id=%s template_id=%s status=%s", user_id, req.template_id, req.status)

    await db.commit()
    return APIResponse.success(message="订阅状态已保存")

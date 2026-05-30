"""微信登录接口。"""
import logging

import httpx
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import create_token
from app.core.config import settings
from app.db.database import get_db
from app.services.user_service import UserService

logger = logging.getLogger("wechat-auth")

router = APIRouter(prefix="/api/auth", tags=["auth"])


class WechatLoginRequest(BaseModel):
    code: str = Field(..., description="wx.login() 返回的临时 code")


class WechatLoginResponse(BaseModel):
    token: str
    user: dict


@router.post("/wechat-login", response_model=WechatLoginResponse)
async def wechat_login(req: WechatLoginRequest, db: AsyncSession = Depends(get_db)):
    """微信小程序静默登录。

    前端调用 wx.login() 获取 code，后端换取 openid 后生成 JWT 返回。
    """
    logger.info("[微信登录] 接收到code: %s***", req.code[:8] if len(req.code) > 8 else req.code)

    if not settings.wechat_appid or not settings.wechat_secret:
        raise ValueError(
            "WECHAT_APPID / WECHAT_SECRET 未配置，请检查 .env 文件"
        )

    # 调用微信 jscode2session
    async with httpx.AsyncClient() as client:
        wx_res = await client.get(
            "https://api.weixin.qq.com/sns/jscode2session",
            params={
                "appid": settings.wechat_appid,
                "secret": settings.wechat_secret,
                "js_code": req.code,
                "grant_type": "authorization_code",
            },
        )
        wx_data = wx_res.json()

    if "openid" not in wx_data:
        errcode = wx_data.get("errcode", "unknown")
        errmsg = wx_data.get("errmsg", "unknown")
        logger.error("[微信登录] jscode2session失败 errcode=%s errmsg=%s", errcode, errmsg)
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail=f"微信登录失败: {errmsg}")

    openid = wx_data["openid"]
    session_key = wx_data.get("session_key", "")
    unionid = wx_data.get("unionid")

    logger.info("[微信登录] openid获取成功 openid=%s", openid)

    # 创建或更新用户
    service = UserService(db)
    user = await service.get_or_create(openid, session_key=session_key)
    if unionid:
        user.unionid = unionid
        await db.commit()
        await db.refresh(user)

    # 生成 JWT
    token = create_token(openid)

    return WechatLoginResponse(
        token=token,
        user={
            "openid": openid,
            "unionid": unionid,
        },
    )


class DevLoginRequest(BaseModel):
    openid: str = Field(..., description="测试用的 openid")


@router.post("/dev-login", response_model=WechatLoginResponse)
async def dev_login(req: DevLoginRequest, db: AsyncSession = Depends(get_db)):
    """开发环境登录：直接传 openid，跳过微信 code2session。

    仅开发/测试环境使用，生产环境应禁用。
    """
    if settings.app_env == "production":
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="生产环境已禁用 dev-login")

    logger.info("[开发登录] openid=%s", req.openid)

    service = UserService(db)
    await service.get_or_create(req.openid)

    token = create_token(req.openid)
    return WechatLoginResponse(
        token=token,
        user={"openid": req.openid},
    )

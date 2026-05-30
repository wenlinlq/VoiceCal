"""JWT 编解码 + 鉴权依赖注入。"""
import logging

from fastapi import Header, HTTPException

from app.core.config import settings

logger = logging.getLogger("auth")

try:
    import jwt
except ImportError:
    jwt = None


def create_token(openid: str) -> str:
    """生成 JWT，payload 包含 openid。"""
    if jwt is None:
        raise ImportError("请安装 PyJWT: pip install PyJWT")
    payload = {
        "openid": openid,
        "user_id": openid,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    logger.info("[JWT] 生成token成功 openid=%s expire=%ds", openid, settings.jwt_expire_seconds)
    return token


def decode_token(token: str) -> dict:
    """解析 JWT，返回 payload。"""
    if jwt is None:
        raise ImportError("请安装 PyJWT: pip install PyJWT")
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("[鉴权] token已过期")
        raise HTTPException(status_code=401, detail="token 已过期")
    except jwt.InvalidTokenError:
        logger.warning("[鉴权] token无效")
        raise HTTPException(status_code=401, detail="token 无效")


async def get_current_user(authorization: str = Header(None)) -> dict:
    """从 Authorization header 解析当前用户。

    返回 {"openid": "...", "user_id": "..."}
    """
    if not authorization:
        logger.warning("[鉴权] 缺少 Authorization header")
        raise HTTPException(status_code=401, detail="缺少 Authorization header")

    if not authorization.startswith("Bearer "):
        logger.warning("[鉴权] Authorization 格式错误")
        raise HTTPException(status_code=401, detail="Authorization 格式必须为 Bearer <token>")

    token = authorization.removeprefix("Bearer ").strip()
    payload = decode_token(token)

    if "openid" not in payload:
        logger.warning("[鉴权] token中缺少openid")
        raise HTTPException(status_code=401, detail="token 无效：缺少 openid")

    return {"openid": payload["openid"], "user_id": payload["openid"]}

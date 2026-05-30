"""微信推送服务：Access Token 管理 + 订阅消息发送 + 定时扫描。"""
import logging
from datetime import datetime
from typing import Optional

import httpx
import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.event import Event
from app.models.subscription import UserSubscription

logger = logging.getLogger("wechat-push")

ACCESS_TOKEN_KEY = "wechat:access_token"
ACCESS_TOKEN_BUFFER = 300  # 提前5分钟刷新


class WechatPushService:
    """微信推送服务：获取 access_token、发送订阅消息。"""

    def __init__(self):
        self._redis: Optional[aioredis.Redis] = None
        self._redis_failed = False

    async def _ensure_redis(self):
        if self._redis is not None:
            return self._redis
        if self._redis_failed:
            return None
        try:
            self._redis = aioredis.from_url(settings.redis_url, decode_responses=True)
            await self._redis.ping()
            logger.info("[微信推送] Redis 连接成功")
        except Exception as e:
            logger.warning("[微信推送] Redis 不可用，access_token 无法缓存: %s", e)
            self._redis_failed = True
            self._redis = None
        return self._redis

    async def get_access_token(self) -> str:
        """获取微信 access_token，优先从 Redis 缓存读取。"""
        r = await self._ensure_redis()
        if r:
            cached = await r.get(ACCESS_TOKEN_KEY)
            if cached:
                logger.debug("[微信推送] access_token 命中缓存")
                return cached

        if not settings.wechat_appid or not settings.wechat_secret:
            raise RuntimeError("WECHAT_APPID / WECHAT_SECRET 未配置")

        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://api.weixin.qq.com/cgi-bin/token",
                params={
                    "grant_type": "client_credential",
                    "appid": settings.wechat_appid,
                    "secret": settings.wechat_secret,
                },
            )
            data = res.json()

        if "access_token" not in data:
            errcode = data.get("errcode", "unknown")
            errmsg = data.get("errmsg", "unknown")
            logger.error("[微信推送] 获取access_token失败 errcode=%s errmsg=%s", errcode, errmsg)
            raise RuntimeError(f"获取 access_token 失败: {errmsg}")

        access_token = data["access_token"]
        expires_in = data.get("expires_in", 7200)
        ttl = max(expires_in - ACCESS_TOKEN_BUFFER, 60)

        if r:
            await r.set(ACCESS_TOKEN_KEY, access_token, ex=ttl)
            logger.info("[微信推送] access_token 已缓存 ttl=%ds", ttl)

        return access_token

    async def send_subscribe_message(
        self,
        openid: str,
        template_id: str,
        page: str,
        reminder_text: str,
        title: str,
        start_time: str,
        location: str,
    ) -> dict:
        """发送一条微信订阅消息。

        Returns:
            dict: 微信接口返回的原始 JSON。
        """
        access_token = await self.get_access_token()

        payload = {
            "touser": openid,
            "template_id": template_id,
            "page": page,
            "data": {
                "thing3": {"value": reminder_text[:20]},
                "phrase5": {"value": title[:20]},
                "time13": {"value": start_time},
                "thing4": {"value": location[:20]},
            },
        }

        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"https://api.weixin.qq.com/cgi-bin/message/subscribe/send?access_token={access_token}",
                json=payload,
            )
            data = res.json()

        errcode = data.get("errcode", -1)
        if errcode != 0:
            logger.error(
                "[微信推送] subscribeMessage.send失败 errcode=%s errmsg=%s openid=%s template_id=%s",
                errcode,
                data.get("errmsg", ""),
                openid,
                template_id,
            )
        else:
            logger.info("[微信推送] 发送成功 openid=%s title=%s", openid, title)

        return data


# 单例
wechat_push_service = WechatPushService()


async def _get_subscription_status(db: AsyncSession, user_id: str, template_id: str) -> Optional[str]:
    """查询用户对指定模板的订阅状态。"""
    result = await db.execute(
        select(UserSubscription).where(
            UserSubscription.user_id == user_id,
            UserSubscription.template_id == template_id,
        )
    )
    sub = result.scalar_one_or_none()
    return sub.status if sub else None


async def scan_and_push_reminders(db: AsyncSession):
    """扫描待推送的日程提醒并发送微信订阅消息。

    每分钟执行一次：
    1. 查询 remind_at <= now AND push_status='pending' AND remind_enabled=true
    2. 对每条检查用户是否已授权订阅
    3. 已授权 → 调微信接口 → sent / failed
    4. 未授权 → 标记 no_auth
    """
    template_id = settings.wechat_subscribe_template_id
    if not template_id:
        logger.debug("[推送定时] 未配置订阅模板ID，跳过")
        return

    now = datetime.now()
    result = await db.execute(
        select(Event).where(
            Event.remind_at <= now,
            Event.remind_enabled.is_(True),
            Event.push_status == "pending",
            Event.completed.is_(False),
        )
    )
    events = list(result.scalars().all())

    if not events:
        return

    logger.info(
        "[推送定时] ========== 开始扫描 ========== 共发现 %d 条待推送日程",
        len(events),
    )
    for i, evt in enumerate(events, 1):
        logger.info(
            "[推送定时] [%d/%d] 日程: event_id=%s title=\"%s\" user_id=%s remind_at=%s",
            i, len(events), evt.id, evt.title, evt.user_id,
            evt.remind_at.isoformat() if evt.remind_at else "未设置",
        )

    sent_count = 0
    failed_count = 0
    no_auth_count = 0

    for event in events:
        try:
            # 检查用户是否授权订阅
            status = await _get_subscription_status(db, event.user_id, template_id)
            if status != "accept":
                event.push_status = "no_auth"
                await db.commit()
                no_auth_count += 1
                logger.warning(
                    "[推送定时] ⊘ 跳过推送 — 用户未授权订阅 event_id=%s user_id=%s title=\"%s\"",
                    event.id, event.user_id, event.title,
                )
                continue

            start_time_str = event.start_time.strftime("%Y年%m月%d日 %H:%M") if event.start_time else ""
            page = f"pages/event-detail/event-detail?id={event.id}"

            logger.info(
                "[推送定时] → 正在发送微信订阅消息: openid=%s title=\"%s\" time=%s template_id=%s",
                event.user_id, event.title, start_time_str, template_id,
            )

            result_data = await wechat_push_service.send_subscribe_message(
                openid=event.user_id,
                template_id=template_id,
                page=page,
                reminder_text="日程即将开始",
                title=event.title,
                start_time=start_time_str,
                location=event.location or "未填写",
            )

            errcode = result_data.get("errcode", -1)
            if errcode == 0:
                event.push_status = "sent"
                event.pushed_at = datetime.now()
                await db.commit()
                sent_count += 1
                logger.info(
                    "[推送定时] ✓ 微信模版消息发送成功 event_id=%s title=\"%s\" openid=%s",
                    event.id, event.title, event.user_id,
                )
            else:
                errmsg = result_data.get("errmsg", "unknown")
                event.push_status = "failed"
                await db.commit()
                failed_count += 1
                logger.error(
                    "[推送定时] ✗ 微信模版消息发送失败 event_id=%s title=\"%s\" errcode=%s errmsg=%s",
                    event.id, event.title, errcode, errmsg,
                )

        except Exception:
            logger.exception(
                "[推送定时] ✗ 推送异常 event_id=%s title=\"%s\" openid=%s",
                event.id, event.title, event.user_id,
            )
            event.push_status = "failed"
            await db.commit()
            failed_count += 1

    logger.info(
        "[推送定时] ========== 本轮完成 ========== 扫描=%d 已推送=%d 失败=%d 未授权=%d",
        len(events), sent_count, failed_count, no_auth_count,
    )

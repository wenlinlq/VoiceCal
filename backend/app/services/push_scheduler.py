"""定时任务调度：APScheduler 每分钟扫描待推送日程。"""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session_factory
from app.services.wechat_push_service import scan_and_push_reminders

logger = logging.getLogger("push-scheduler")

scheduler = AsyncIOScheduler()


async def _scan_job():
    """定时任务：扫描并推送日程提醒。"""
    session_factory = get_session_factory()
    async with session_factory() as db:
        try:
            await scan_and_push_reminders(db)
        except Exception:
            logger.exception("[推送定时] 扫描任务异常")


def start_push_scheduler():
    """启动定时推送调度器。"""
    scheduler.add_job(_scan_job, "interval", minutes=1, id="push_reminders", name="扫描日程提醒")
    scheduler.start()
    logger.info("[推送定时] 调度器已启动，每1分钟扫描一次")


def stop_push_scheduler():
    """停止定时推送调度器。"""
    scheduler.shutdown(wait=False)
    logger.info("[推送定时] 调度器已停止")

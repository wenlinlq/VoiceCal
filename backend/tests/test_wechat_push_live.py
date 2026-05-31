"""全库推送测试 — 扫描所有开启提醒的日程并推送"""
import asyncio
from datetime import datetime, timedelta

from app.db.database import get_session_factory
from app.models.event import Event
from app.models.subscription import UserSubscription
from app.services.wechat_push_service import scan_and_push_reminders
from sqlalchemy import select, update, delete

TEST_OPENID = "oTtw53VF5N3JIH5JEPFvFaoOiLzQ"
TEMPLATE_ID = "Z3RaB3lf2XpbkRXVYyK8rZNefkDnlY_A7sJ7WAesL1c"


async def main():
    factory = get_session_factory()

    async with factory() as db:
        # 1. 列出所有带提醒的日程
        r = await db.execute(
            select(Event).where(Event.remind_enabled.is_(True))
        )
        events = list(r.scalars().all())
        print(f"找到 {len(events)} 条开启提醒的日程:\n")
        for evt in events:
            print(
                f"  [{evt.push_status}] {evt.title[:20]} "
                f"user={evt.user_id} remind_at={evt.remind_at}"
            )

        if not events:
            print("(无)")
            return

        # 2. 给所有用户写入订阅授权
        user_ids = list({e.user_id for e in events})
        for uid in user_ids:
            await db.execute(
                delete(UserSubscription).where(UserSubscription.user_id == uid)
            )
            db.add(UserSubscription(user_id=uid, template_id=TEMPLATE_ID, status="accept"))
        await db.commit()
        print(f"\n✅ 已为 {len(user_ids)} 个用户写入订阅授权")

        # 3. 把 remind_at 改为 1 分钟前、push_status 改 pending
        now = datetime.now()
        for evt in events:
            await db.execute(
                update(Event)
                .where(Event.id == evt.id)
                .values(
                    remind_at=now - timedelta(minutes=1),
                    push_status="pending",
                )
            )
        await db.commit()
        print(f"✅ 已重置 {len(events)} 条日程为待推送\n")

        # 4. 执行推送
        print("=" * 50)
        print("执行 scan_and_push_reminders...")
        print("=" * 50)
        await scan_and_push_reminders(db)

        # 5. 查看结果
        print()
        r = await db.execute(
            select(Event).where(Event.remind_enabled.is_(True))
        )
        for evt in r.scalars().all():
            icon = "✅" if evt.push_status == "sent" else "❌"
            print(f"{icon} [{evt.push_status}] {evt.title[:20]} user={evt.user_id}")

    print("\n完成")


if __name__ == "__main__":
    asyncio.run(main())

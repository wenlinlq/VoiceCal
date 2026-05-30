from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.event import Event
from app.models.subscription import UserSubscription
from app.services.wechat_push_service import scan_and_push_reminders, wechat_push_service


@pytest.mark.asyncio
async def test_scan_and_push_reminders_skips_completed_events(db_session, monkeypatch):
    called = {"count": 0}

    async def fake_send_subscribe_message(**kwargs):
        called["count"] += 1
        return {"errcode": 0}

    monkeypatch.setattr(settings, "wechat_subscribe_template_id", "template_001")
    monkeypatch.setattr(
        wechat_push_service,
        "send_subscribe_message",
        fake_send_subscribe_message,
    )

    event = Event(
        user_id="oPushUser001",
        title="已完成提醒",
        start_time=datetime.now() + timedelta(minutes=10),
        end_time=datetime.now() + timedelta(minutes=40),
        completed=True,
        remind_enabled=True,
        remind_at=datetime.now() - timedelta(minutes=1),
        push_status="pending",
    )
    sub = UserSubscription(
        user_id="oPushUser001",
        template_id="template_001",
        status="accept",
    )
    db_session.add_all([event, sub])
    await db_session.commit()

    await scan_and_push_reminders(db_session)

    result = await db_session.execute(select(Event).where(Event.id == event.id))
    refreshed = result.scalar_one()
    assert called["count"] == 0
    assert refreshed.push_status == "pending"


@pytest.mark.asyncio
async def test_scan_and_push_reminders_marks_sent_for_authorized_events(db_session, monkeypatch):
    sent_payloads = []

    async def fake_send_subscribe_message(**kwargs):
        sent_payloads.append(kwargs)
        return {"errcode": 0}

    monkeypatch.setattr(settings, "wechat_subscribe_template_id", "template_001")
    monkeypatch.setattr(
        wechat_push_service,
        "send_subscribe_message",
        fake_send_subscribe_message,
    )

    event = Event(
        user_id="oPushUser002",
        title="待推送提醒",
        start_time=datetime.now() + timedelta(minutes=15),
        end_time=datetime.now() + timedelta(minutes=45),
        completed=False,
        remind_enabled=True,
        remind_at=datetime.now() - timedelta(minutes=1),
        push_status="pending",
    )
    sub = UserSubscription(
        user_id="oPushUser002",
        template_id="template_001",
        status="accept",
    )
    db_session.add_all([event, sub])
    await db_session.commit()

    await scan_and_push_reminders(db_session)

    result = await db_session.execute(select(Event).where(Event.id == event.id))
    refreshed = result.scalar_one()
    assert len(sent_payloads) == 1
    assert sent_payloads[0]["openid"] == "oPushUser002"
    assert refreshed.push_status == "sent"
    assert refreshed.pushed_at is not None


@pytest.mark.asyncio
async def test_send_subscribe_message_uses_real_template_field_mapping(monkeypatch):
    captured = {}

    class FakeResponse:
        def json(self):
            return {"errcode": 0}

    class FakeAsyncClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    async def fake_get_access_token():
        return "mock-access-token"

    monkeypatch.setattr(
        wechat_push_service,
        "get_access_token",
        fake_get_access_token,
    )
    monkeypatch.setattr("app.services.wechat_push_service.httpx.AsyncClient", FakeAsyncClient)

    result = await wechat_push_service.send_subscribe_message(
        openid="oPushUser003",
        template_id="template_001",
        page="pages/event-detail/event-detail?id=evt_001",
        reminder_text="日程即将开始",
        title="项目会议",
        start_time="2026-05-30 15:00",
        location="线上会议",
    )

    assert result["errcode"] == 0
    assert captured["url"].endswith("access_token=mock-access-token")
    assert captured["json"] == {
        "touser": "oPushUser003",
        "template_id": "template_001",
        "page": "pages/event-detail/event-detail?id=evt_001",
        "data": {
            "thing3": {"value": "日程即将开始"},
            "phrase5": {"value": "项目会议"},
            "time13": {"value": "2026-05-30 15:00"},
            "thing4": {"value": "线上会议"},
        },
    }

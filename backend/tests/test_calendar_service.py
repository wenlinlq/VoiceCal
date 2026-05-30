import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.schemas.event_schema import EventCreate, EventUpdate
from app.services.calendar_service import CalendarService


TEST_USER_ID = "test_openid_svc_001"


@pytest_asyncio.fixture
async def service(db_session):
    return CalendarService(db=db_session, user_id=TEST_USER_ID)


@pytest.fixture
def sample_event_data():
    now = datetime.now(timezone.utc)
    return EventCreate(
        title="组会",
        description="每周组会",
        location="会议室A",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
    )


@pytest.mark.asyncio
async def test_create_event(service, sample_event_data):
    event = await service.create_event(sample_event_data)
    assert event.id is not None
    assert isinstance(event.id, uuid.UUID)
    assert event.title == "组会"
    assert event.user_id == TEST_USER_ID


@pytest.mark.asyncio
async def test_query_events(service, sample_event_data):
    await service.create_event(sample_event_data)
    events = await service.query_events()
    assert len(events) == 1
    assert events[0].title == "组会"


@pytest.mark.asyncio
async def test_query_events_time_filter(service, sample_event_data):
    now = datetime.now(timezone.utc)
    old_event = EventCreate(
        title="旧日程",
        start_time=now - timedelta(days=10),
        end_time=now - timedelta(days=9),
    )
    await service.create_event(old_event)
    await service.create_event(sample_event_data)

    events = await service.query_events(start_time=now)
    assert len(events) == 1
    assert events[0].title == "组会"


@pytest.mark.asyncio
async def test_get_event(service, sample_event_data):
    created = await service.create_event(sample_event_data)
    fetched = await service.get_event(created.id)
    assert fetched is not None
    assert fetched.id == created.id


@pytest.mark.asyncio
async def test_get_event_not_found(service):
    fetched = await service.get_event(uuid.uuid4())
    assert fetched is None


@pytest.mark.asyncio
async def test_update_event(service, sample_event_data):
    created = await service.create_event(sample_event_data)
    update = EventUpdate(title="更新后的组会")
    updated = await service.update_event(created.id, update)
    assert updated is not None
    assert updated.title == "更新后的组会"
    assert updated.description == "每周组会"


@pytest.mark.asyncio
async def test_update_event_not_found(service):
    update = EventUpdate(title="不会成功")
    result = await service.update_event(uuid.uuid4(), update)
    assert result is None


@pytest.mark.asyncio
async def test_delete_event(service, sample_event_data):
    created = await service.create_event(sample_event_data)
    deleted = await service.delete_event(created.id)
    assert deleted is True
    fetched = await service.get_event(created.id)
    assert fetched is None


@pytest.mark.asyncio
async def test_delete_event_not_found(service):
    deleted = await service.delete_event(uuid.uuid4())
    assert deleted is False

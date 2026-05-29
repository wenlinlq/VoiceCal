import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base, get_db
from app.main import app
from app.models.event import Event  # noqa: F401


@pytest_asyncio.fixture
async def client():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_list_events(client):
    resp = await client.post(
        "/api/events",
        json={
            "title": "项目会议",
            "start_time": "2026-05-30T15:00:00",
            "end_time": "2026-05-30T16:00:00",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["title"] == "项目会议"
    event_id = data["data"]["id"]

    resp = await client.get("/api/events?start=2026-05-30T00:00:00&end=2026-05-30T23:59:59")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    titles = [e["title"] for e in data["data"]]
    assert "项目会议" in titles

    resp = await client.get(f"/api/events/{event_id}")
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "项目会议"


@pytest.mark.asyncio
async def test_update_event(client):
    resp = await client.post(
        "/api/events",
        json={
            "title": "原会议",
            "start_time": "2026-05-30T10:00:00",
            "end_time": "2026-05-30T11:00:00",
        },
    )
    event_id = resp.json()["data"]["id"]

    resp = await client.put(
        f"/api/events/{event_id}",
        json={"title": "改后的会议", "start_time": "2026-05-30T14:00:00", "end_time": "2026-05-30T15:00:00"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["title"] == "改后的会议"


@pytest.mark.asyncio
async def test_delete_event(client):
    resp = await client.post(
        "/api/events",
        json={
            "title": "待删除",
            "start_time": "2026-05-30T09:00:00",
            "end_time": "2026-05-30T10:00:00",
        },
    )
    event_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/events/{event_id}")
    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    resp = await client.get(f"/api/events/{event_id}")
    assert resp.json()["code"] == 404


@pytest.mark.asyncio
async def test_not_found(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    assert (await client.get(f"/api/events/{fake_id}")).json()["code"] == 404
    assert (await client.put(f"/api/events/{fake_id}", json={"title": "x"})).json()["code"] == 404
    assert (await client.delete(f"/api/events/{fake_id}")).json()["code"] == 404

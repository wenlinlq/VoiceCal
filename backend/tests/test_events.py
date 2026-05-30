"""日程 CRUD API 测试 — 含 JWT 鉴权 + 数据隔离。"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import create_token
from app.db.database import Base, get_db
from app.main import app
from app.models.event import Event  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.subscription import UserSubscription  # noqa: F401

TEST_OPENID_A = "oTest_user_a_001"
TEST_OPENID_B = "oTest_user_b_002"


def auth_header(openid=TEST_OPENID_A):
    return {"Authorization": f"Bearer {create_token(openid)}"}


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
async def test_unauthorized_returns_401(client):
    """不带 token 返回 401。"""
    resp = await client.get("/api/events")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token_returns_401(client):
    """无效 token 返回 401。"""
    resp = await client.get("/api/events", headers={"Authorization": "Bearer invalid_token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_and_list_events(client):
    resp = await client.post(
        "/api/events",
        json={
            "title": "项目会议",
            "start_time": "2026-05-30T15:00:00",
            "end_time": "2026-05-30T16:00:00",
        },
        headers=auth_header(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["title"] == "项目会议"
    assert data["data"]["user_id"] == TEST_OPENID_A
    event_id = data["data"]["id"]

    resp = await client.get(
        "/api/events?start=2026-05-30T00:00:00&end=2026-05-30T23:59:59",
        headers=auth_header(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    titles = [e["title"] for e in data["data"]]
    assert "项目会议" in titles

    resp = await client.get(f"/api/events/{event_id}", headers=auth_header())
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
        headers=auth_header(),
    )
    event_id = resp.json()["data"]["id"]

    resp = await client.put(
        f"/api/events/{event_id}",
        json={"title": "改后的会议", "start_time": "2026-05-30T14:00:00", "end_time": "2026-05-30T15:00:00"},
        headers=auth_header(),
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
        headers=auth_header(),
    )
    event_id = resp.json()["data"]["id"]

    resp = await client.delete(f"/api/events/{event_id}", headers=auth_header())
    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    resp = await client.get(f"/api/events/{event_id}", headers=auth_header())
    assert resp.json()["code"] == 404


@pytest.mark.asyncio
async def test_not_found(client):
    fake_id = "00000000-0000-0000-0000-000000000000"
    h = auth_header()
    assert (await client.get(f"/api/events/{fake_id}", headers=h)).json()["code"] == 404
    assert (await client.put(f"/api/events/{fake_id}", json={"title": "x"}, headers=h)).json()["code"] == 404
    assert (await client.delete(f"/api/events/{fake_id}", headers=h)).json()["code"] == 404


# ---------- 数据隔离测试 ----------

@pytest.mark.asyncio
async def test_user_a_cannot_see_user_b_event(client):
    """A 创建的日程 B 看不到。"""
    # A 创建日程
    resp = await client.post(
        "/api/events",
        json={
            "title": "A的私密日程",
            "start_time": "2026-05-30T12:00:00",
            "end_time": "2026-05-30T13:00:00",
        },
        headers=auth_header(TEST_OPENID_A),
    )
    assert resp.status_code == 200
    event_id = resp.json()["data"]["id"]

    # B 查不到
    resp = await client.get(
        "/api/events?start=2026-05-30T00:00:00&end=2026-05-30T23:59:59",
        headers=auth_header(TEST_OPENID_B),
    )
    assert resp.status_code == 200
    titles = [e["title"] for e in resp.json()["data"]]
    assert "A的私密日程" not in titles

    # B 直接通过 ID 也访问不到
    resp = await client.get(f"/api/events/{event_id}", headers=auth_header(TEST_OPENID_B))
    assert resp.json()["code"] == 404


@pytest.mark.asyncio
async def test_user_b_cannot_delete_user_a_event(client):
    """B 不能删除 A 的日程。"""
    resp = await client.post(
        "/api/events",
        json={
            "title": "A的日程",
            "start_time": "2026-05-30T15:00:00",
            "end_time": "2026-05-30T16:00:00",
        },
        headers=auth_header(TEST_OPENID_A),
    )
    event_id = resp.json()["data"]["id"]

    # B 删除失败
    resp = await client.delete(f"/api/events/{event_id}", headers=auth_header(TEST_OPENID_B))
    assert resp.json()["code"] == 404

    # A 的数据还在
    resp = await client.get(f"/api/events/{event_id}", headers=auth_header(TEST_OPENID_A))
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "A的日程"


@pytest.mark.asyncio
async def test_create_event_with_remind_fields(client):
    """创建带提醒字段的日程。"""
    resp = await client.post(
        "/api/events",
        json={
            "title": "带提醒的会议",
            "start_time": "2026-05-30T15:00:00",
            "end_time": "2026-05-30T16:00:00",
            "remind_enabled": True,
            "remind_at": "2026-05-30T14:45:00",
            "subscribe_template_id": "template_001",
        },
        headers=auth_header(),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["data"]["remind_enabled"] is True
    assert data["data"]["push_status"] == "pending"
    assert data["data"]["subscribe_template_id"] == "template_001"

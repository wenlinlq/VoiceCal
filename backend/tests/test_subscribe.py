import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.auth import create_token
from app.db.database import Base, get_db
from app.main import app
from app.models.event import Event  # noqa: F401
from app.models.subscription import UserSubscription
from app.models.user import User  # noqa: F401

TEST_OPENID = "oSubscribeUser001"


def auth_header():
    return {"Authorization": f"Bearer {create_token(TEST_OPENID)}"}


@pytest_asyncio.fixture
async def app_client():
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, session_factory
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.mark.asyncio
async def test_subscribe_result_upserts_status(app_client):
    client, session_factory = app_client

    resp = await client.post(
        "/api/wechat/subscribe-result",
        json={"template_id": "template_001", "status": "accept"},
        headers=auth_header(),
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0

    async with session_factory() as session:
        result = await session.execute(
            select(UserSubscription).where(
                UserSubscription.user_id == TEST_OPENID,
                UserSubscription.template_id == "template_001",
            )
        )
        sub = result.scalar_one_or_none()

    assert sub is not None
    assert sub.status == "accept"

    resp = await client.post(
        "/api/wechat/subscribe-result",
        json={"template_id": "template_001", "status": "reject"},
        headers=auth_header(),
    )
    assert resp.status_code == 200

    async with session_factory() as session:
        result = await session.execute(
            select(UserSubscription).where(
                UserSubscription.user_id == TEST_OPENID,
                UserSubscription.template_id == "template_001",
            )
        )
        sub = result.scalar_one_or_none()

    assert sub is not None
    assert sub.status == "reject"

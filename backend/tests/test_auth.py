import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.api.auth as auth_api
from app.core.auth import decode_token
from app.core.config import settings
from app.db.database import Base, get_db
from app.main import app
from app.models.event import Event  # noqa: F401
from app.models.subscription import UserSubscription  # noqa: F401
from app.models.user import User


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


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeWechatClient:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, params):
        assert url == "https://api.weixin.qq.com/sns/jscode2session"
        assert params["js_code"] == "mock-code"
        return _FakeResponse(
            {
                "openid": "oMockWechatUser001",
                "session_key": "session-key-001",
                "unionid": "unionid-001",
            }
        )


@pytest.mark.asyncio
async def test_wechat_login_returns_jwt_and_creates_user(app_client, monkeypatch):
    client, session_factory = app_client
    monkeypatch.setattr(settings, "wechat_appid", "wx-test-appid")
    monkeypatch.setattr(settings, "wechat_secret", "wx-test-secret")
    monkeypatch.setattr(auth_api.httpx, "AsyncClient", _FakeWechatClient)

    resp = await client.post("/api/auth/wechat-login", json={"code": "mock-code"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["openid"] == "oMockWechatUser001"
    assert data["user"]["unionid"] == "unionid-001"

    token_payload = decode_token(data["token"])
    assert token_payload["openid"] == "oMockWechatUser001"

    async with session_factory() as session:
        result = await session.execute(
            select(User).where(User.id == "oMockWechatUser001")
        )
        user = result.scalar_one_or_none()

    assert user is not None
    assert user.unionid == "unionid-001"
    assert user.session_key == "session-key-001"

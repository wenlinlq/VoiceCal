"""用户服务：创建和查询用户。"""
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserService:
    """用户管理服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create(self, openid: str, session_key: str = None) -> User:
        """查找用户，不存在则创建。返回 User 对象。"""
        result = await self.db.execute(select(User).where(User.id == openid))
        user = result.scalar_one_or_none()

        if user is None:
            user = User(
                id=openid,
                session_key=session_key,
                last_login_at=datetime.now(),
            )
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
        else:
            # 更新 session_key 和登录时间
            if session_key:
                user.session_key = session_key
            user.last_login_at = datetime.now()
            await self.db.commit()
            await self.db.refresh(user)

        return user

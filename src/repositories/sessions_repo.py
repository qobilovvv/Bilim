from sqlalchemy import select, update
from sqlalchemy.sql import func

from src.models.auth_session import AuthSession


class SessionsRepository:
    def __init__(self, db):
        self.db = db

    async def get_active(self, session_id, user_id, lock=False):
        stmt = select(AuthSession).where(
            AuthSession.id == session_id,
            AuthSession.user_id == user_id,
            AuthSession.revoked_at.is_(None),
            AuthSession.expires_at > func.now(),
        )
        if lock:
            stmt = stmt.with_for_update()
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def revoke_all(self, user_id):
        await self.db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=func.now())
        )

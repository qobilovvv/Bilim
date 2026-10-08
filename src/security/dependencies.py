from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database import get_db_session
from src.models.user import User, UserType
from src.repositories.users_repo import UsersRepository
from src.repositories.sessions_repo import SessionsRepository
from src.security.tokens import TokenError, verify_access_token

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session, scope="function")
) -> User:
    token = credentials.credentials
    try:
        claims = verify_access_token(token)
        user_id = int(claims.sub)
    except (TokenError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    repo = UsersRepository(db)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    if not user.is_active or user.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is unavailable"
        )
    if claims.version != user.auth_version or not await SessionsRepository(db).get_active(claims.session_id, user.id):
        raise HTTPException(401, "Session expired or revoked", headers={"WWW-Authenticate": "Bearer"})
    return user

async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.type != UserType.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin privileges required"
        )
    return current_user

async def get_current_teacher_or_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    if current_user.type not in (UserType.ADMIN, UserType.SELLER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Admin or teacher privileges required"
        )
    return current_user

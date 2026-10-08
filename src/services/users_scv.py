import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from src.infrastructure.config import settings
from src.models.auth_session import AuthSession
from src.repositories.sessions_repo import SessionsRepository

from fastapi import Depends, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database import get_db_session
from src.models.user import User, UserType, SellerProfile
from src.repositories.users_repo import UsersRepository
from src.schemas.auth_schemas import (
    UserLoginRequest,
    AdminLoginRequest,
    UserRegisterRequest,
    ProfileUpdateRequest,
    PasswordUpdateRequest,
    UserListItemResponse,
    AdminUserUpdateRequest,
)
from src.services.file_storage import IMAGE_EXTENSIONS, stage_upload, queue_media_cleanup
from src.security.passwords import hash_password_async, verify_password_async
from src.security.tokens import create_token_pair, TokenPair, TokenError, verify_refresh_token

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB

class UsersService:
    def __init__(self, repo: UsersRepository):
        self.repo = repo

    async def _issue_tokens(self, user, session=None) -> TokenPair:
        session_id = session.id if session is not None else secrets.token_hex(16)
        tokens = create_token_pair(subject=str(user.id), role=user.type,
                                   version=user.auth_version, session_id=session_id)
        digest = hashlib.sha256(tokens.refresh_token.encode()).hexdigest()
        expires = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        if session is None:
            session = AuthSession(id=session_id, user_id=user.id, token_digest=digest, expires_at=expires)
            self.repo.db.add(session)
        else:
            session.token_digest = digest
            session.expires_at = expires
        await self.repo.db.flush()
        return tokens

    async def refresh_tokens(self, token: str) -> TokenPair:
        try:
            claims = verify_refresh_token(token)
        except TokenError as exc:
            raise HTTPException(401, "Invalid refresh token") from exc
        # Shared ordering with password reset/change/logout prevents concurrent token resurrection.
        user = await self.repo.get_by_id_for_update(int(claims.sub))
        if not user or not user.is_active or user.is_blocked or user.auth_version != claims.version:
            raise HTTPException(401, "Session expired or revoked")
        session = await SessionsRepository(self.repo.db).get_active(claims.session_id, user.id, lock=True)
        if not session or not secrets.compare_digest(session.token_digest, hashlib.sha256(token.encode()).hexdigest()):
            raise HTTPException(401, "Session expired or revoked")
        return await self._issue_tokens(user, session)

    async def logout_all(self, user_id: int):
        user = await self.repo.get_by_id_for_update(user_id)
        if not user:
            raise HTTPException(401, "User not found")
        user.auth_version += 1
        await SessionsRepository(self.repo.db).revoke_all(user_id)
        await self.repo.db.flush()

    async def register_user(self, data: UserRegisterRequest) -> User:
        # Check if phone number is already registered
        existing_user = await self.repo.get_by_phone(data.phone)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number already registered"
            )

        # Hash the password and save
        hashed = await hash_password_async(data.password)
        new_user = User(
            first_name=data.first_name,
            phone=data.phone,
            password=hashed,
            type=UserType.USER,
            is_active=True,
            is_superuser=False
        )
        return await self.repo.create_user(new_user)

    async def register_seller(self, data: UserRegisterRequest) -> User:
        # Check if phone number is already registered
        existing_user = await self.repo.get_by_phone(data.phone)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Phone number already registered"
            )

        # Hash the password
        hashed = await hash_password_async(data.password)
        
        # Create user as seller and initialize an empty seller profile
        new_user = User(
            first_name=data.first_name,
            phone=data.phone,
            password=hashed,
            type=UserType.SELLER,
            is_active=True,
            is_superuser=False,
            seller_profile=SellerProfile(
                years_of_experience=None,
                portfolio=None,
                description=None
            )
        )
        return await self.repo.create_user(new_user)

    async def login_user(self, data: UserLoginRequest) -> tuple[User, TokenPair]:
        # Login using phone directly (from UserLoginRequest)
        user = await self.repo.get_by_phone(data.phone)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect phone number or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active or user.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is unavailable"
            )

        # Verify password hash
        if not await verify_password_async(data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect phone number or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last login timestamp
        user.last_login = datetime.now(timezone.utc)
        await self.repo.update_user(user)

        # Generate JWT token pair
        tokens = await self._issue_tokens(user)
        return user, tokens

    async def login_admin(self, data: AdminLoginRequest) -> tuple[User, TokenPair]:
        # Authenticate admin by username
        user = await self.repo.get_by_username(data.username)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active or user.is_blocked:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Account is unavailable"
            )

        # Verify password hash
        if not await verify_password_async(data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if user.type != UserType.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Admin privileges required"
            )

        user.last_login = datetime.now(timezone.utc)
        await self.repo.update_user(user)
        tokens = await self._issue_tokens(user)
        return user, tokens


    async def login_seller(self, data: UserLoginRequest) -> tuple[User, TokenPair]:
        user, tokens = await self.login_user(data)
        if user.type != UserType.SELLER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Seller privileges required"
            )
        return user, tokens


    async def update_profile(self, user_id: int, data: ProfileUpdateRequest, avatar: UploadFile | None = None) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        updates = data.model_dump(exclude_unset=True)
        for field in ("phone", "username", "email"):
            if field not in updates or updates[field] == getattr(user, field):
                continue
            value = updates[field]
            if field == "username" and user.type == UserType.ADMIN and value is None:
                raise HTTPException(400, "Administrators must keep a username")
            if value is not None and await getattr(self.repo, f"get_by_{field}")(value):
                raise HTTPException(409, f"{field} is already in use")
        for field in ("first_name", "last_name", "phone", "username", "email"):
            if field in updates:
                setattr(user, field, updates[field])
        seller_fields = {"years_of_experience", "portfolio", "description"}
        if user.type == UserType.SELLER and seller_fields.intersection(updates):
            if user.seller_profile is None:
                user.seller_profile = SellerProfile()
            for field in seller_fields.intersection(updates):
                setattr(user.seller_profile, field, updates[field])

        if avatar:
            user.avatar = await stage_upload(self.repo.db, avatar, "avatars", IMAGE_EXTENSIONS,
                                             MAX_AVATAR_SIZE, user.avatar)

        return await self.repo.update_user(user)

    async def update_password(self, user_id: int, data: PasswordUpdateRequest) -> None:
        user = await self.repo.get_by_id_for_update(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify the current password
        if not await verify_password_async(data.old_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )

        # Hash and save the new password
        user.password = await hash_password_async(data.new_password)
        user.auth_version += 1
        await SessionsRepository(self.repo.db).revoke_all(user_id)
        await self.repo.update_user(user)

    async def list_users(
        self,
        status_filter: str | None,
        search: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        limit: int,
        offset: int,
        user_type: str = UserType.USER,
    ) -> tuple[list[UserListItemResponse], int]:
        users, total = await self.repo.list_users(
            status_filter=status_filter,
            search=search,
            date_from=date_from,
            date_to=date_to,
            offset=offset,
            limit=limit,
            user_type=user_type,
        )

        items = []
        for user in users:
            # Derive full_name
            full_name = user.first_name
            if user.last_name:
                full_name += f" {user.last_name}"

            # Derive status
            if user.is_blocked:
                user_status = "blocked"
            elif user.is_active:
                user_status = "active"
            else:
                user_status = "inactive"

            items.append(UserListItemResponse(
                id=user.id,
                full_name=full_name,
                avatar=user.avatar,
                phone=user.phone,
                status=user_status,
                created_at=user.created_at,
                bought_courses_count=0,  # TODO: implement when courses model is ready
                last_login=user.last_login,
            ))

        return items, total


    async def admin_update_user(self, user_id: int, data: AdminUserUpdateRequest) -> User:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        updates = data.model_dump(exclude_unset=True)
        if user.type == UserType.ADMIN and (updates.get("is_blocked") or updates.get("is_active") is False):
            raise HTTPException(409, "Administrator accounts cannot be disabled through user moderation")
        for field in ("phone", "email"):
            value = updates.get(field)
            if value is not None and value != getattr(user, field):
                if await getattr(self.repo, f"get_by_{field}")(value):
                    raise HTTPException(409, f"{field} is already in use")
        for field, value in updates.items():
            setattr(user, field, value)
        if updates.get("is_blocked") or updates.get("is_active") is False:
            user.auth_version += 1
            await SessionsRepository(self.repo.db).revoke_all(user.id)

        return await self.repo.update_user(user)

    async def admin_delete_user(self, user_id: int) -> None:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        if user.type == UserType.ADMIN:
            raise HTTPException(409, "Administrator accounts cannot be deleted through user moderation")
        await queue_media_cleanup(self.repo.db, [user.avatar])
        await self.repo.delete_user(user)


async def get_users_service(db: AsyncSession = Depends(get_db_session, scope="function")) -> UsersService:
    repo = UsersRepository(db)
    return UsersService(repo)

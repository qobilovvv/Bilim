import os
import uuid
from datetime import datetime, timezone

import aiofiles
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
from src.security.passwords import hash_password, verify_password
from src.security.tokens import create_token_pair, TokenPair

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_AVATAR_SIZE = 5 * 1024 * 1024  # 5 MB

class UsersService:
    def __init__(self, repo: UsersRepository):
        self.repo = repo

    async def register_user(self, data: UserRegisterRequest) -> User:
        # Check if phone number is already registered
        existing_user = await self.repo.get_by_phone(data.phone)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

        # Hash the password and save
        hashed = hash_password(data.password)
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
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

        # Hash the password
        hashed = hash_password(data.password)
        
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

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is inactive"
            )

        # Verify password hash
        if not verify_password(data.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect phone number or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Update last login timestamp
        user.last_login = datetime.now(timezone.utc)
        await self.repo.update_user(user)

        # Generate JWT token pair
        tokens = create_token_pair(subject=str(user.id), role=user.type)
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

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is inactive"
            )

        # Verify password hash
        if not verify_password(data.password, user.password):
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

        # Generate JWT token pair
        tokens = create_token_pair(subject=str(user.id), role=user.type)
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

        # Update phone if provided and changed
        if data.phone is not None and data.phone != user.phone:
            existing_phone = await self.repo.get_by_phone(data.phone)
            if existing_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Phone number already registered by another user"
                )
            user.phone = data.phone

        # Update username if provided and changed
        if data.username is not None and data.username != user.username:
            username_val = data.username.strip() if data.username else None
            if username_val:
                existing_username = await self.repo.get_by_username(username_val)
                if existing_username:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Username already registered by another user"
                    )
                user.username = username_val
            else:
                user.username = None

        # Update email if provided and changed
        if data.email is not None and data.email != user.email:
            email_val = data.email.strip() if data.email else None
            if email_val:
                existing_email = await self.repo.get_by_email(email_val)
                if existing_email:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered by another user"
                    )
                user.email = email_val
            else:
                user.email = None

        if data.first_name is not None:
            user.first_name = data.first_name

        if data.last_name is not None:
            user.last_name = data.last_name.strip() if data.last_name else None

        # Update seller specific profile fields if type is SELLER
        if user.type == UserType.SELLER:
            if not user.seller_profile:
                user.seller_profile = SellerProfile(
                    years_of_experience=None,
                    portfolio=None,
                    description=None
                )
            
            if data.years_of_experience is not None:
                user.seller_profile.years_of_experience = data.years_of_experience
                
            if data.portfolio is not None:
                user.seller_profile.portfolio = data.portfolio.strip() if data.portfolio else None
                
            if data.description is not None:
                user.seller_profile.description = data.description.strip() if data.description else None

        if avatar:
            # Validate file type
            if avatar.content_type not in ALLOWED_IMAGE_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid image type. Allowed: JPEG, PNG, WebP"
                )
            
            content = await avatar.read()
            if len(content) > MAX_AVATAR_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image too large. Maximum size: 5 MB"
                )

            # Delete old avatar
            if user.avatar:
                old_path = os.path.join("media", user.avatar)
                if os.path.exists(old_path):
                    os.remove(old_path)

            ext = avatar.filename.rsplit(".", 1)[-1] if avatar.filename and "." in avatar.filename else "jpg"
            filename = f"{uuid.uuid4().hex}.{ext}"
            avatar_dir = os.path.join("media", "avatars")
            os.makedirs(avatar_dir, exist_ok=True)
            file_path = os.path.join(avatar_dir, filename)

            async with aiofiles.open(file_path, "wb") as f:
                await f.write(content)
            
            user.avatar = f"avatars/{filename}"

        return await self.repo.update_user(user)

    async def update_password(self, user_id: int, data: PasswordUpdateRequest) -> None:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify the current password
        if not verify_password(data.old_password, user.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password"
            )

        # Hash and save the new password
        user.password = hash_password(data.new_password)
        await self.repo.update_user(user)

    async def list_users(
        self,
        status_filter: str | None,
        search: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        page: int,
        page_size: int,
    ) -> tuple[list[UserListItemResponse], int]:
        offset = (page - 1) * page_size
        users, total = await self.repo.list_users(
            status_filter=status_filter,
            search=search,
            date_from=date_from,
            date_to=date_to,
            offset=offset,
            limit=page_size,
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

        # Allow admin to update specific fields
        if data.first_name is not None:
            user.first_name = data.first_name
        
        if data.last_name is not None:
            user.last_name = data.last_name.strip() if data.last_name else None

        if data.phone is not None and data.phone != user.phone:
            existing = await self.repo.get_by_phone(data.phone)
            if existing:
                raise HTTPException(status_code=400, detail="Phone number already in use")
            user.phone = data.phone

        if data.email is not None and data.email != user.email:
            email_val = data.email.strip() if data.email else None
            if email_val:
                existing = await self.repo.get_by_email(email_val)
                if existing:
                    raise HTTPException(status_code=400, detail="Email already in use")
                user.email = email_val
            else:
                user.email = None

        if data.is_active is not None:
            user.is_active = data.is_active

        if data.is_blocked is not None:
            user.is_blocked = data.is_blocked

        return await self.repo.update_user(user)

    async def admin_delete_user(self, user_id: int) -> None:
        user = await self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Optionally, check if user has dependencies that shouldn't be deleted,
        # but the DB constraints will handle cascades usually.
        await self.repo.delete_user(user)


async def get_users_service(db: AsyncSession = Depends(get_db_session)) -> UsersService:
    repo = UsersRepository(db)
    return UsersService(repo)

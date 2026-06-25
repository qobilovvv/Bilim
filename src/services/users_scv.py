from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database import get_db_session
from src.models.user import User, UserType
from src.repositories.users_repo import UsersRepository
from src.schemas.auth_schemas import (
    UserLoginRequest,
    UserRegisterRequest,
    ProfileUpdateRequest,
    PasswordUpdateRequest,
)
from src.security.passwords import hash_password, verify_password
from src.security.tokens import create_token_pair, TokenPair

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

    async def login_user(self, data: UserLoginRequest) -> tuple[User, TokenPair]:
        # Login using username which represents the phone number
        user = await self.repo.get_by_phone(data.username)
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

        # Generate JWT token pair
        tokens = create_token_pair(subject=str(user.id), role=user.type)
        return user, tokens

    async def login_admin(self, data: UserLoginRequest) -> tuple[User, TokenPair]:
        user, tokens = await self.login_user(data)
        if user.type != UserType.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Admin privileges required"
            )
        return user, tokens

    async def update_profile(self, user_id: int, data: ProfileUpdateRequest) -> User:
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

        # Update email if provided and changed
        if data.email is not None and data.email != user.email:
            # If the user is setting email to empty string, handle it as None or empty
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
            # last_name is optional, so it can be None or empty
            user.last_name = data.last_name.strip() if data.last_name else None

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

async def get_users_service(db: AsyncSession = Depends(get_db_session)) -> UsersService:
    repo = UsersRepository(db)
    return UsersService(repo)

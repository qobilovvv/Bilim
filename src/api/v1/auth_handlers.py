from fastapi import APIRouter, Depends, status
from src.models.user import User
from src.schemas.auth_schemas import (
    UserLoginRequest,
    AdminLoginRequest,
    UserRegisterRequest,
    UserResponse,
    AuthResponse,
    TokenResponse,
    ProfileUpdateRequest,
    PasswordUpdateRequest,
)
from src.services.users_scv import UsersService, get_users_service
from src.security.dependencies import get_current_user

router = APIRouter(prefix="/auth")

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def register(
    data: UserRegisterRequest,
    service: UsersService = Depends(get_users_service)
):
    return await service.register_user(data)

@router.post("/seller/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def register_seller(
    data: UserRegisterRequest,
    service: UsersService = Depends(get_users_service)
):
    return await service.register_seller(data)

@router.post("/login", response_model=AuthResponse, tags=["auth"])
async def login(
    data: UserLoginRequest,
    service: UsersService = Depends(get_users_service)
):
    user, tokens = await service.login_user(data)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
        )
    )

@router.post("/admin/login", response_model=AuthResponse, tags=["auth"])
async def admin_login(
    data: AdminLoginRequest,
    service: UsersService = Depends(get_users_service)
):
    user, tokens = await service.login_admin(data)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
        )
    )

@router.post("/seller/login", response_model=AuthResponse, tags=["auth"])
async def seller_login(
    data: UserLoginRequest,
    service: UsersService = Depends(get_users_service)
):
    user, tokens = await service.login_seller(data)
    return AuthResponse(
        user=UserResponse.model_validate(user),
        tokens=TokenResponse(
            access_token=tokens.access_token,
            refresh_token=tokens.refresh_token,
            token_type=tokens.token_type,
        )
    )

@router.get("/profile", response_model=UserResponse, tags=["profile"])
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=UserResponse, tags=["profile"])
async def update_profile(
    data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: UsersService = Depends(get_users_service),
):
    return await service.update_profile(current_user.id, data)

@router.put("/password", status_code=status.HTTP_200_OK, tags=["profile"])
async def update_password(
    data: PasswordUpdateRequest,
    current_user: User = Depends(get_current_user),
    service: UsersService = Depends(get_users_service),
):
    await service.update_password(current_user.id, data)
    return {"message": "Password updated successfully"}

@router.get("/me", response_model=UserResponse, tags=["auth"])
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
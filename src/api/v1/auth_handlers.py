from fastapi import APIRouter, Depends, File, Form, UploadFile, status
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
    ForgotPasswordSendCodeRequest,
    ForgotPasswordVerifyCodeRequest,
    ForgotPasswordResetRequest,
)
from src.services.users_scv import UsersService, get_users_service
from src.services.password_reset_scv import PasswordResetService, get_password_reset_service
from src.security.dependencies import get_current_user

router = APIRouter(prefix="")

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

def profile_update_form(
    first_name: str | None = Form(None),
    last_name: str | None = Form(None),
    phone: str | None = Form(None),
    username: str | None = Form(None),
    email: str | None = Form(None),
    years_of_experience: int | None = Form(None),
    portfolio: str | None = Form(None),
    description: str | None = Form(None),
) -> ProfileUpdateRequest:
    return ProfileUpdateRequest(
        first_name=first_name,
        last_name=last_name,
        phone=phone,
        username=username,
        email=email,
        years_of_experience=years_of_experience,
        portfolio=portfolio,
        description=description,
    )

@router.get("/profile", response_model=UserResponse, tags=["profile"])
async def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/profile", response_model=UserResponse, tags=["profile"])
async def update_profile(
    data: ProfileUpdateRequest = Depends(profile_update_form),
    avatar: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    service: UsersService = Depends(get_users_service),
):
    return await service.update_profile(current_user.id, data, avatar)

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

@router.post("/forgot-password/send-code", status_code=status.HTTP_200_OK, tags=["auth"])
async def send_code(
    data: ForgotPasswordSendCodeRequest,
    service: PasswordResetService = Depends(get_password_reset_service),
):
    await service.send_reset_code(data.phone)
    return {"message": "Verification code sent successfully"}

@router.post("/forgot-password/verify-code", status_code=status.HTTP_200_OK, tags=["auth"])
async def verify_code(
    data: ForgotPasswordVerifyCodeRequest,
    service: PasswordResetService = Depends(get_password_reset_service),
):
    token = await service.verify_reset_code(data.phone, data.code)
    return {"token": token, "message": "Verification code verified successfully"}

@router.post("/forgot-password/new-password", status_code=status.HTTP_200_OK, tags=["auth"])
async def new_password(
    data: ForgotPasswordResetRequest,
    service: PasswordResetService = Depends(get_password_reset_service),
):
    await service.reset_password(data.phone, data.token, data.new_password)
    return {"message": "Password reset successfully"}
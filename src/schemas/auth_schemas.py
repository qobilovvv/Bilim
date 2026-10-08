from pydantic import BaseModel, ConfigDict, Field, EmailStr
from src.schemas.validation import RequestModel, PatchModel, Phone, Name, Username, Password, LongText
from datetime import datetime

class UserLoginRequest(RequestModel):
    phone: Phone
    password: str = Field(min_length=1, max_length=128)

class AdminLoginRequest(RequestModel):
    username: Username
    password: str = Field(min_length=1, max_length=128)

class UserRegisterRequest(RequestModel):
    first_name: Name
    phone: Phone
    password: Password

class SellerProfileResponse(BaseModel):
    years_of_experience: int | None = None
    portfolio: str | None = None
    description: str | None = None

    model_config = ConfigDict(from_attributes=True)

class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    phone: str | None = None
    username: str | None = None
    email: str | None = None
    avatar: str | None = None
    type: str
    is_active: bool
    is_superuser: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_login: datetime | None = None
    seller_profile: SellerProfileResponse | None = None

    model_config = ConfigDict(from_attributes=True)

class ProfileUpdateRequest(PatchModel):
    nullable_fields = {"last_name", "username", "email", "years_of_experience", "portfolio", "description"}
    first_name: Name | None = None
    last_name: Name | None = None
    phone: Phone | None = None
    username: Username | None = None
    email: EmailStr | None = None
    # Seller specific fields
    years_of_experience: int | None = Field(default=None, ge=0, le=100)
    portfolio: LongText | None = None
    description: LongText | None = None

class PasswordUpdateRequest(RequestModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: Password

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse

class ForgotPasswordSendCodeRequest(RequestModel):
    phone: Phone

class ForgotPasswordVerifyCodeRequest(RequestModel):
    phone: Phone
    code: str = Field(pattern=r"^[0-9]{6}$")

class ForgotPasswordResetRequest(RequestModel):
    phone: Phone
    token: str = Field(min_length=32, max_length=128)
    new_password: Password


class UserListItemResponse(BaseModel):
    id: int
    full_name: str
    avatar: str | None = None
    phone: str | None = None
    status: str  # "active" | "inactive" | "blocked"
    created_at: datetime | None = None
    bought_courses_count: int = 0
    last_login: datetime | None = None


class UserListResponse(BaseModel):
    total: int
    limit: int
    offset: int
    result: list[UserListItemResponse]


class AdminUserUpdateRequest(PatchModel):
    nullable_fields = {"last_name", "email"}
    first_name: Name | None = None
    last_name: Name | None = None
    phone: Phone | None = None
    email: EmailStr | None = None
    is_active: bool | None = None
    is_blocked: bool | None = None



class RefreshTokenRequest(RequestModel):
    refresh_token: str = Field(min_length=1, max_length=4096)

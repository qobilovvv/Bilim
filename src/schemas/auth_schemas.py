from pydantic import BaseModel, ConfigDict
from datetime import datetime

class UserLoginRequest(BaseModel):
    phone: str
    password: str

class AdminLoginRequest(BaseModel):
    username: str
    password: str

class UserRegisterRequest(BaseModel):
    first_name: str
    phone: str
    password: str

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

class ProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    username: str | None = None
    email: str | None = None
    # Seller specific fields
    years_of_experience: int | None = None
    portfolio: str | None = None
    description: str | None = None

class PasswordUpdateRequest(BaseModel):
    old_password: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class AuthResponse(BaseModel):
    user: UserResponse
    tokens: TokenResponse

class ForgotPasswordSendCodeRequest(BaseModel):
    phone: str

class ForgotPasswordVerifyCodeRequest(BaseModel):
    phone: str
    code: str

class ForgotPasswordResetRequest(BaseModel):
    phone: str
    token: str
    new_password: str


class UserListItemResponse(BaseModel):
    id: int
    full_name: str
    avatar: str | None = None
    status: str  # "active" | "inactive" | "blocked"
    created_at: datetime | None = None
    bought_courses_count: int = 0
    last_login: datetime | None = None


class UserListResponse(BaseModel):
    items: list[UserListItemResponse]
    total: int
    page: int
    page_size: int


class AdminUserUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None
    is_active: bool | None = None
    is_blocked: bool | None = None


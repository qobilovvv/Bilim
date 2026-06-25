from pydantic import BaseModel, ConfigDict
from datetime import datetime

class UserLoginRequest(BaseModel):
    phone: str
    password: str

class UserRegisterRequest(BaseModel):
    first_name: str
    phone: str
    password: str

class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str | None = None
    phone: str
    email: str | None = None
    type: str
    is_active: bool
    is_superuser: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

class ProfileUpdateRequest(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    email: str | None = None

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

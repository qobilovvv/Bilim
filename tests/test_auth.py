from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from src.infrastructure.config import Settings
from src.schemas.auth_schemas import AdminLoginRequest, UserLoginRequest
from src.security import dependencies
from src.security.tokens import TokenError, _encode, verify_access_token
from src.services.users_service import UsersService


@pytest.mark.parametrize(
    "method,payload",
    [
        ("login_user", UserLoginRequest(phone="998901234567", password="valid-password")),
        ("login_admin", AdminLoginRequest(username="admin", password="valid-password")),
    ],
)
async def test_blocked_user_cannot_login(method, payload):
    user = SimpleNamespace(is_active=True, is_blocked=True)
    repo = SimpleNamespace(
        get_by_phone=AsyncMock(return_value=user), get_by_username=AsyncMock(return_value=user)
    )
    with pytest.raises(HTTPException):
        await getattr(UsersService(repo), method)(payload)


async def test_blocking_rejects_existing_access_token(monkeypatch):
    user = SimpleNamespace(is_active=True, is_blocked=True)
    monkeypatch.setattr(
        dependencies,
        "UsersRepository",
        lambda db: SimpleNamespace(get_by_id=AsyncMock(return_value=user)),
    )
    monkeypatch.setattr(dependencies, "verify_access_token", lambda token: SimpleNamespace(sub="1"))
    with pytest.raises(HTTPException) as exc:
        await dependencies.get_current_user(SimpleNamespace(credentials="token"), None)
    assert exc.value.status_code == 403


@pytest.mark.parametrize("subject", ["abc", "0", "-1", "١", ""])
def test_invalid_subjects_are_rejected(subject):
    token = _encode(
        {"sub": subject, "role": "admin", "type": "access", "iat": 1, "exp": 4102444800}
    )
    with pytest.raises(TokenError):
        verify_access_token(token)


@pytest.mark.parametrize("secret", ["secrett", "a" * 40, "change-me-0123456789abcdef0123456789"])
def test_weak_secrets_fail_configuration(secret):
    with pytest.raises(ValidationError):
        Settings(JWT_SECRET_KEY=secret)

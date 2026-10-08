from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from src.services.password_reset_service import PasswordResetService, code_digest


async def test_unknown_phone_has_generic_success_without_sms(monkeypatch):
    sender = AsyncMock()
    monkeypatch.setattr("src.services.password_reset_service.eskiz_client.send_sms", sender)
    users = SimpleNamespace(get_by_phone_for_update=AsyncMock(return_value=None))
    await PasswordResetService(None, users).send_reset_code("998901234567")
    sender.assert_not_awaited()


async def test_five_failed_attempts_exhaust_challenge():
    phone = "998901234567"
    challenge = SimpleNamespace(
        code=code_digest(phone, "123456"),
        attempts=4,
        verified=False,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
    )
    resets = SimpleNamespace(
        get_latest_challenge=AsyncMock(return_value=challenge), update_reset_code=AsyncMock()
    )
    users = SimpleNamespace(
        get_by_phone_for_update=AsyncMock(
            return_value=SimpleNamespace(is_active=True, is_blocked=False)
        )
    )
    service = PasswordResetService(resets, users)
    assert await service.verify_reset_code(phone, "999999") is None
    assert challenge.attempts == 5
    assert await service.verify_reset_code(phone, "123456") is None

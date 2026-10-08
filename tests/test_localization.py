import pytest
from src.security.localization import get_accept_language


@pytest.mark.parametrize("header,expected", [
    (None, "uz"), ("ru-RU, en;q=0.8", "ru"), ("ru;q=0.2,en;q=0.9", "en"),
    ("ru;q=0,en;q=0.1", "en"), ("en;q=invalid", "uz"), ("fr", "uz"),
])
async def test_language_quality_and_fallback(header, expected):
    assert await get_accept_language(header) == expected

from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import OperationalError

from src.infrastructure import database
from src.main import app


async def test_liveness_and_request_id():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/healthz", headers={"X-Request-ID": "trace-123"})
    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "trace-123"


async def test_readiness_returns_generic_failure(monkeypatch):
    session = AsyncMock()
    session.execute.side_effect = OperationalError(
        "connect", {}, Exception("sensitive provider details")
    )
    factory = AsyncMock()
    factory.__aenter__.return_value = session
    monkeypatch.setattr(database, "AsyncSessionFactory", lambda: factory)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/readyz")
    assert response.status_code == 503
    assert response.text == "Unavailable"

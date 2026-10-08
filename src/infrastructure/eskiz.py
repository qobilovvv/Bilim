import asyncio

import httpx

from src.infrastructure.config import settings


class EskizError(Exception):
    pass


class EskizClient:
    def __init__(self):
        self.base_url = settings.ESKIZ_BASE_URL.rstrip("/")
        self.token = None
        self._client = None
        self._auth_lock = asyncio.Lock()

    @property
    def client(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(10, connect=5),
                limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
            )
        return self._client

    async def close(self):
        if self._client is not None:
            await self._client.aclose()
            self._client = None
        self.token = None

    async def authenticate(self, previous_token=None):
        async with self._auth_lock:
            if self.token and self.token != previous_token:
                return
            if not settings.ESKIZ_EMAIL or not settings.ESKIZ_PASSWORD:
                raise EskizError("SMS credentials are not configured")
            response = await self.client.post(
                f"{self.base_url}/auth/login",
                data={"email": settings.ESKIZ_EMAIL, "password": settings.ESKIZ_PASSWORD},
            )
            if response.is_error:
                raise EskizError("SMS authentication failed")
            try:
                token = response.json().get("data", {}).get("token")
            except (ValueError, AttributeError) as exc:
                raise EskizError("Invalid SMS provider response") from exc
            if not isinstance(token, str) or not token:
                raise EskizError("SMS authentication failed")
            self.token = token

    async def send_sms(self, phone, text):
        if not self.token:
            await self.authenticate()
        token = self.token
        payload = {"mobile_phone": phone, "message": text, "from": settings.ESKIZ_FROM}
        response = await self.client.post(
            f"{self.base_url}/message/sms/send",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
        )
        # Only retry explicit authentication rejection; a timed-out send may already have succeeded.
        if response.status_code == 401:
            await self.authenticate(token)
            response = await self.client.post(
                f"{self.base_url}/message/sms/send",
                json=payload,
                headers={"Authorization": f"Bearer {self.token}"},
            )
        if response.is_error:
            raise EskizError("SMS request failed")
        try:
            body = response.json()
            status = str(body.get("status", "")).lower().strip()
            message = str(body.get("message", "")).lower()
        except (ValueError, AttributeError) as exc:
            raise EskizError("Invalid SMS provider response") from exc
        if (
            status not in {"success", "waiting", "queued"}
            and "waiting for sms provider" not in message
        ):
            raise EskizError("SMS request was rejected")


eskiz_client = EskizClient()

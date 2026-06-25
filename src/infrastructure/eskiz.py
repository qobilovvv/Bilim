import httpx
import logging
from src.infrastructure.config import settings

logger = logging.getLogger(__name__)

class EskizClient:
    def __init__(self):
        self.base_url = settings.ESKIZ_BASE_URL.rstrip('/')
        self.email = settings.ESKIZ_EMAIL
        self.password = settings.ESKIZ_PASSWORD
        self.from_number = settings.ESKIZ_FROM
        self.token = None

    async def authenticate(self) -> None:
        if not self.email or not self.password:
            raise ValueError("ESKIZ_EMAIL and ESKIZ_PASSWORD must be configured")
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.base_url}/auth/login",
                data={"email": self.email, "password": self.password},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if resp.status_code >= 400:
                raise Exception(f"Eskiz authentication failed: {resp.status_code} {resp.text}")
            
            res = resp.json()
            token = res.get("data", {}).get("token")
            if not token:
                raise Exception(f"Eskiz token not found in response: {res}")
            self.token = token

    async def send_sms(self, phone: str, text: str) -> None:
        # Clean phone number: keep only digits
        phone = "".join(filter(str.isdigit, phone))
        
        if not self.token:
            await self.authenticate()

        async def make_request():
            async with httpx.AsyncClient() as client:
                payload = {
                    "mobile_phone": phone,
                    "message": text,
                    "from": self.from_number
                }
                return await client.post(
                    f"{self.base_url}/message/sms/send",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    }
                )

        resp = await make_request()
        
        # If token expired (401), re-authenticate once
        if resp.status_code == 401:
            logger.info("Eskiz token expired, re-authenticating...")
            await self.authenticate()
            resp = await make_request()

        if resp.status_code >= 400:
            raise Exception(f"Eskiz HTTP request failed: {resp.status_code} {resp.text}")

        res = resp.json()
        status = str(res.get("status", "")).lower().strip()
        message = str(res.get("message", "")).lower().strip()

        if status in ("success", "waiting", "queued"):
            return
        if "waiting for sms provider" in message:
            return

        raise Exception(f"Eskiz SMS failed: {res.get('message')}")

# Shared client instance
eskiz_client = EskizClient()

from abc import ABC, abstractmethod
from typing import Optional

class IAuthRepository(ABC):
    @abstractmethod
    async def login_user(self, data: dict): ...

    @abstractmethod
    async def create_admin(self, data: dict): ...
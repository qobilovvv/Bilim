from abc import ABC, abstractmethod
from datetime import datetime
from src.models.user import User
from src.models.category import Category

class IUsersRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: int) -> User | None: ...

    @abstractmethod
    async def get_by_phone(self, phone: str) -> User | None: ...

    @abstractmethod
    async def get_by_username(self, username: str) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    async def create_user(self, user: User) -> User: ...

    @abstractmethod
    async def update_user(self, user: User) -> User: ...

    @abstractmethod
    async def delete_user(self, user: User) -> None: ...

    @abstractmethod
    async def list_users(
        self,
        status_filter: str | None,
        search: str | None,
        date_from: datetime | None,
        date_to: datetime | None,
        offset: int,
        limit: int,
    ) -> tuple[list[User], int]: ...


class ICategoriesRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: int) -> Category | None: ...

    @abstractmethod
    async def get_by_path(self, path: str) -> Category | None: ...

    @abstractmethod
    async def list_categories(self, active_only: bool = True) -> list[Category]: ...

    @abstractmethod
    async def create_category(self, category: Category) -> Category: ...

    @abstractmethod
    async def update_category(self, category: Category) -> Category: ...

    @abstractmethod
    async def delete_category(self, category: Category) -> None: ...


from src.models.password_reset import PasswordResetCode

class IPasswordResetRepository(ABC):
    @abstractmethod
    async def create_reset_code(self, reset_code: PasswordResetCode) -> PasswordResetCode: ...

    @abstractmethod
    async def get_active_code(self, phone: str, code: str) -> PasswordResetCode | None: ...

    @abstractmethod
    async def get_active_token(self, phone: str, token: str) -> PasswordResetCode | None: ...

    @abstractmethod
    async def update_reset_code(self, reset_code: PasswordResetCode) -> PasswordResetCode: ...
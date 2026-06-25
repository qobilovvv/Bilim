from abc import ABC, abstractmethod
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
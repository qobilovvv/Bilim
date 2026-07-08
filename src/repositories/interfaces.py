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
        user_type: str,
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


from src.models.course import Course
from src.models.module import Module
from src.models.lesson import Lesson
from src.models.material import Material
from src.models.homework import Homework

class ICoursesRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: int) -> Course | None: ...

    @abstractmethod
    async def list_courses(
        self,
        category_id: int | None,
        type_filter: str | None,
        teacher_id: int | None,
        search: str | None,
        active_only: bool,
        offset: int,
        limit: int,
    ) -> tuple[list[Course], int]: ...

    @abstractmethod
    async def create_course(self, course: Course) -> Course: ...

    @abstractmethod
    async def update_course(self, course: Course) -> Course: ...

    @abstractmethod
    async def delete_course(self, course: Course) -> None: ...


class IModulesRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: int) -> Module | None: ...

    @abstractmethod
    async def create_module(self, module: Module) -> Module: ...

    @abstractmethod
    async def update_module(self, module: Module) -> Module: ...

    @abstractmethod
    async def delete_module(self, module: Module) -> None: ...


class ILessonsRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: int) -> Lesson | None: ...

    @abstractmethod
    async def create_lesson(self, lesson: Lesson) -> Lesson: ...

    @abstractmethod
    async def update_lesson(self, lesson: Lesson) -> Lesson: ...

    @abstractmethod
    async def delete_lesson(self, lesson: Lesson) -> None: ...


class IMaterialsRepository(ABC):
    @abstractmethod
    async def get_by_id(self, id: int) -> Material | None: ...

    @abstractmethod
    async def create_material(self, material: Material) -> Material: ...

    @abstractmethod
    async def delete_material(self, material: Material) -> None: ...


class IHomeworkRepository(ABC):
    @abstractmethod
    async def get_by_lesson_id(self, lesson_id: int) -> Homework | None: ...

    @abstractmethod
    async def create_homework(self, homework: Homework) -> Homework: ...

    @abstractmethod
    async def update_homework(self, homework: Homework) -> Homework: ...

    @abstractmethod
    async def delete_homework(self, homework: Homework) -> None: ...
from src.models.category import Category
from src.models.course import Course
from src.models.user import User


def public_course_conditions():
    category_visible = Category.is_active.is_(True) & (
        Category.parent_id.is_(None) | Category.parent.has(Category.is_active.is_(True)))
    teacher_visible = User.is_active.is_(True) & User.is_blocked.is_(False)
    return (Course.is_active.is_(True), Course.category.has(category_visible), Course.teacher.has(teacher_visible))

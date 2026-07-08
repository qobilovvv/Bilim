from fastapi import HTTPException, status
from src.models.course import Course
from src.models.user import User, UserType

def check_course_permission(course: Course, user: User) -> None:
    if user.type == UserType.ADMIN:
        return
    if user.type == UserType.SELLER and course.teacher_id == user.id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have permission to modify this course"
    )

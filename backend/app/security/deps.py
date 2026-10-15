from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Path, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import CourseCapabilities
from app.config import Settings, get_settings
from app.db import get_db
from app.models.course import Course, CourseMember, CourseMemberRole
from app.models.user import User, UserRole
from app.security.sessions import get_valid_session


@dataclass
class CourseAccess:
    course: Course
    member: CourseMember
    user: User

    @property
    def is_teacher(self) -> bool:
        return self.member.role == CourseMemberRole.teacher.value

    @property
    def capabilities(self) -> CourseCapabilities:
        return CourseCapabilities(
            can_manage_documents=self.is_teacher,
            can_manage_members=self.is_teacher,
            can_view_insights=self.is_teacher,
        )


def get_current_user(
    request: Request,
    db: Annotated[DbSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    session_id = request.cookies.get(settings.session_cookie_name)
    session = get_valid_session(db, session_id)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def require_admin(user: Annotated[User, Depends(get_current_user)]) -> User:
    if user.role != UserRole.admin.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


def get_course_or_404(db: DbSession, course_id: UUID) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course


def get_membership(db: DbSession, course_id: UUID, user_id: UUID) -> CourseMember | None:
    return db.execute(
        select(CourseMember).where(
            CourseMember.course_id == course_id,
            CourseMember.user_id == user_id,
        )
    ).scalar_one_or_none()


def require_course_member(
    course_id: Annotated[UUID, Path()],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> CourseAccess:
    course = get_course_or_404(db, course_id)
    member = get_membership(db, course_id, user.id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a course member")
    return CourseAccess(course=course, member=member, user=user)


def require_course_teacher(
    access: Annotated[CourseAccess, Depends(require_course_member)],
) -> CourseAccess:
    if not access.is_teacher:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Course teacher only")
    return access

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import CourseMemberOut, CourseOut, TeacherAddStudentRequest
from app.db import get_db
from app.models.course import Course, CourseMember, CourseMemberRole
from app.models.user import User, UserRole
from app.security.deps import (
    CourseAccess,
    get_current_user,
    get_membership,
    require_course_member,
    require_course_teacher,
)

router = APIRouter(prefix="/courses", tags=["courses"])


def _resolve_student_user(db: DbSession, body: TeacherAddStudentRequest) -> User | None:
    if body.user_id and body.user_id.strip():
        try:
            user_id = UUID(body.user_id.strip())
        except ValueError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id") from None
        user = db.get(User, user_id)
        if user is not None and body.username and body.username.strip() and user.username != body.username.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id and username do not match",
            )
        return user
    return db.execute(select(User).where(User.username == body.username.strip())).scalar_one_or_none()


@router.get("", response_model=list[CourseOut])
def list_my_courses(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[CourseOut]:
    rows = db.execute(
        select(Course)
        .join(CourseMember, CourseMember.course_id == Course.id)
        .where(CourseMember.user_id == user.id)
        .order_by(Course.created_at)
    ).scalars().all()
    return [CourseOut(id=str(c.id), title=c.title) for c in rows]


@router.get("/{course_id}", response_model=CourseOut)
def get_course(access: Annotated[CourseAccess, Depends(require_course_member)]) -> CourseOut:
    return CourseOut(id=str(access.course.id), title=access.course.title)


@router.get("/{course_id}/members", response_model=list[CourseMemberOut])
def list_members(
    access: Annotated[CourseAccess, Depends(require_course_member)],
    db: Annotated[DbSession, Depends(get_db)],
) -> list[CourseMemberOut]:
    members = db.execute(
        select(CourseMember, User)
        .join(User, User.id == CourseMember.user_id)
        .where(CourseMember.course_id == access.course.id)
    ).all()
    return [
        CourseMemberOut(user_id=str(user.id), username=user.username, role=member.role)
        for member, user in members
    ]


@router.post("/{course_id}/members", response_model=CourseMemberOut, status_code=status.HTTP_201_CREATED)
def add_student(
    body: TeacherAddStudentRequest,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
) -> CourseMemberOut:
    user = _resolve_student_user(db, body)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.role != UserRole.student.value:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can only add students")
    if get_membership(db, access.course.id, user.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member")
    member = CourseMember(
        course_id=access.course.id,
        user_id=user.id,
        role=CourseMemberRole.student.value,
    )
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member") from None
    return CourseMemberOut(user_id=str(user.id), username=user.username, role=member.role)


@router.delete("/{course_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student(
    user_id: UUID,
    access: Annotated[CourseAccess, Depends(require_course_teacher)],
    db: Annotated[DbSession, Depends(get_db)],
) -> None:
    member = get_membership(db, access.course.id, user_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if member.role != CourseMemberRole.student.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Can only remove students")
    db.delete(member)
    db.commit()

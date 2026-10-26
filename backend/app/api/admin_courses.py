import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.api.schemas import (
    AdminAddMemberRequest,
    CourseCreateRequest,
    CourseMemberOut,
    CourseOut,
    CourseUpdateRequest,
)
from app.config import Settings, get_settings
from app.db import get_db
from app.models.course import Course, CourseMember, CourseMemberRole, Semester
from app.models.user import User, UserRole
from app.security.deps import get_course_or_404, get_membership, require_admin
from app.services.storage import StorageError, delete_course_uploads

router = APIRouter(prefix="/admin/courses", tags=["admin-courses"])
logger = logging.getLogger(__name__)


def _course_out(course: Course) -> CourseOut:
    return CourseOut(id=str(course.id), title=course.title, semester_id=course.semester_id)


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
def create_course(
    body: CourseCreateRequest,
    db: Annotated[DbSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> CourseOut:
    if body.semester_id is not None and db.get(Semester, body.semester_id) is None:
        raise HTTPException(status_code=404, detail="Semester not found")
    course = Course(title=body.title, semester_id=body.semester_id)
    db.add(course)
    db.commit()
    db.refresh(course)
    return _course_out(course)


@router.get("", response_model=list[CourseOut])
def list_courses(
    db: Annotated[DbSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> list[CourseOut]:
    courses = db.execute(select(Course).order_by(Course.created_at)).scalars().all()
    return [_course_out(c) for c in courses]


@router.get("/{course_id}/members", response_model=list[CourseMemberOut])
def list_course_members(
    course_id: UUID,
    db: Annotated[DbSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> list[CourseMemberOut]:
    course = get_course_or_404(db, course_id)
    members = db.execute(
        select(CourseMember, User)
        .join(User, User.id == CourseMember.user_id)
        .where(CourseMember.course_id == course.id)
    ).all()
    return [
        CourseMemberOut(user_id=str(user.id), username=user.username, role=member.role)
        for member, user in members
    ]


@router.patch("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: UUID,
    body: CourseUpdateRequest,
    db: Annotated[DbSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> CourseOut:
    course = get_course_or_404(db, course_id)
    if body.title is not None:
        course.title = body.title
    if "semester_id" in body.model_fields_set:
        if body.semester_id is not None and db.get(Semester, body.semester_id) is None:
            raise HTTPException(status_code=404, detail="Semester not found")
        course.semester_id = body.semester_id
    db.commit()
    db.refresh(course)
    return _course_out(course)


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: UUID,
    db: Annotated[DbSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    course = get_course_or_404(db, course_id)
    db.delete(course)
    db.commit()
    try:
        delete_course_uploads(settings.upload_dir, course_id)
    except StorageError as exc:
        logger.error(
            "storage_cleanup_failed scope=course course_id=%s error_type=%s",
            course_id,
            type(exc).__name__,
        )


@router.post("/{course_id}/members", response_model=CourseMemberOut, status_code=status.HTTP_201_CREATED)
def add_member(
    course_id: UUID,
    body: AdminAddMemberRequest,
    db: Annotated[DbSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> CourseMemberOut:
    course = get_course_or_404(db, course_id)
    try:
        user_id = UUID(body.user_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user_id") from None
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if body.role == CourseMemberRole.teacher and user.role not in (
        UserRole.teacher.value, UserRole.admin.value
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a teacher")
    if body.role == CourseMemberRole.student and user.role not in (
        UserRole.student.value, UserRole.admin.value
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not a student")
    if get_membership(db, course.id, user.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member")
    member = CourseMember(course_id=course.id, user_id=user.id, role=body.role.value)
    db.add(member)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already a member") from None
    return CourseMemberOut(user_id=str(user.id), username=user.username, role=member.role)


@router.delete("/{course_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    course_id: UUID,
    user_id: UUID,
    db: Annotated[DbSession, Depends(get_db)],
    _admin: Annotated[User, Depends(require_admin)],
) -> None:
    get_course_or_404(db, course_id)
    member = get_membership(db, course_id, user_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    db.delete(member)
    db.commit()

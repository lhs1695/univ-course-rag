"""PLAN-17: small course-scoped business operations, using existing identities."""

import csv
import io
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.course import Course, CourseClass, CourseMember, Semester
from app.models.user import User
from app.security.deps import (
    get_course_or_404,
    get_current_user,
    get_membership,
    require_admin,
)

router = APIRouter(tags=["course-business"])
Db = Annotated[Session, Depends(get_db)]
Admin = Annotated[User, Depends(require_admin)]


def require_course_staff(
    course_id: UUID, user: Annotated[User, Depends(get_current_user)], db: Db
) -> Course:
    course = get_course_or_404(db, course_id)
    member = get_membership(db, course_id, user.id)
    if user.role != "admin" and (member is None or member.role != "teacher"):
        raise HTTPException(403, "Course teacher or admin only")
    return course


StaffCourse = Annotated[Course, Depends(require_course_staff)]


class SemesterInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    starts_on: date
    ends_on: date

    @model_validator(mode="after")
    def validate_dates(self):
        if self.ends_on < self.starts_on:
            raise ValueError("ends_on must be on or after starts_on")
        return self


class SemesterOut(SemesterInput):
    id: UUID


class ClassInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    name: str = Field(min_length=1, max_length=100)


class ClassOut(ClassInput):
    id: UUID
    course_id: UUID
    student_count: int


def commit_unique(db: Session):
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Name or membership conflict; refresh and retry"
        ) from None


def semester_out(row: Semester) -> SemesterOut:
    return SemesterOut(
        id=row.id, name=row.name, starts_on=row.starts_on, ends_on=row.ends_on
    )


def class_out(db: Session, row: CourseClass) -> ClassOut:
    count = db.scalar(
        select(func.count())
        .select_from(CourseMember)
        .where(CourseMember.class_id == row.id)
    )
    return ClassOut(
        id=row.id, course_id=row.course_id, name=row.name, student_count=count
    )


@router.get("/admin/semesters", response_model=list[SemesterOut])
def list_semesters(db: Db, _admin: Admin):
    return [
        semester_out(s)
        for s in db.scalars(select(Semester).order_by(Semester.starts_on.desc()))
    ]


@router.post("/admin/semesters", response_model=SemesterOut, status_code=201)
def create_semester(body: SemesterInput, db: Db, _admin: Admin):
    row = Semester(**body.model_dump())
    db.add(row)
    commit_unique(db)
    return semester_out(row)


@router.put("/admin/semesters/{semester_id}", response_model=SemesterOut)
def edit_semester(semester_id: UUID, body: SemesterInput, db: Db, _admin: Admin):
    row = db.get(Semester, semester_id)
    if row is None:
        raise HTTPException(404, "Semester not found")
    for key, value in body.model_dump().items():
        setattr(row, key, value)
    commit_unique(db)
    return semester_out(row)


@router.delete("/admin/semesters/{semester_id}", status_code=204)
def delete_semester(semester_id: UUID, db: Db, _admin: Admin):
    row = db.get(Semester, semester_id)
    if row is None:
        raise HTTPException(404, "Semester not found")
    if db.scalar(select(Course.id).where(Course.semester_id == semester_id).limit(1)):
        raise HTTPException(409, "Semester is assigned to courses")
    db.delete(row)
    commit_unique(db)


@router.get("/courses/{course_id}/classes", response_model=list[ClassOut])
def list_classes(course: StaffCourse, db: Db):
    return [
        class_out(db, row)
        for row in db.scalars(
            select(CourseClass)
            .where(CourseClass.course_id == course.id)
            .order_by(CourseClass.name)
        )
    ]


@router.post("/courses/{course_id}/classes", response_model=ClassOut, status_code=201)
def create_class(body: ClassInput, course: StaffCourse, db: Db):
    row = CourseClass(course_id=course.id, name=body.name)
    db.add(row)
    commit_unique(db)
    return class_out(db, row)


def scoped_class(db: Session, course: Course, class_id: UUID) -> CourseClass:
    row = db.get(CourseClass, class_id)
    if row is None or row.course_id != course.id:
        raise HTTPException(404, "Class not found")
    return row


@router.put("/courses/{course_id}/classes/{class_id}", response_model=ClassOut)
def edit_class(class_id: UUID, body: ClassInput, course: StaffCourse, db: Db):
    row = scoped_class(db, course, class_id)
    row.name = body.name
    commit_unique(db)
    return class_out(db, row)


@router.delete("/courses/{course_id}/classes/{class_id}", status_code=204)
def delete_class(class_id: UUID, course: StaffCourse, db: Db):
    row = scoped_class(db, course, class_id)
    if db.scalar(
        select(CourseMember.id).where(CourseMember.class_id == class_id).limit(1)
    ):
        raise HTTPException(409, "Class still has students")
    db.delete(row)
    commit_unique(db)


class RosterIssue(BaseModel):
    line: int
    code: str


class RosterSummary(BaseModel):
    total: int
    imported: int = 0
    unchanged: int = 0
    rejected: int = 0
    errors: list[RosterIssue] = Field(default_factory=list)


@router.post("/courses/{course_id}/roster", response_model=RosterSummary)
def import_roster(course: StaffCourse, db: Db, file: Annotated[UploadFile, File()]):
    try:
        return _import_roster(course, db, file)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            409, "Name or membership conflict; refresh and retry"
        ) from None


def _import_roster(course: Course, db: Session, file: UploadFile):
    """Import existing student identities only. Errors are per row; valid rows commit together.

    Every occurrence of a duplicate student number in the same CSV is rejected.
    Existing memberships can be repeated unchanged, but never silently moved.
    """
    raw = file.file.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise HTTPException(413, "CSV exceeds 1 MiB")
    try:
        reader = csv.reader(
            io.StringIO(raw.decode("utf-8-sig"), newline=""), strict=True
        )
        header = next(reader, None)
        if header != ["学号", "姓名", "班级"]:
            raise HTTPException(422, "CSV header must be 学号,姓名,班级 (UTF-8)")
        rows = []
        for cells in reader:
            rows.append((reader.line_num, [cell.strip() for cell in cells]))
            if len(rows) > 5000:
                raise HTTPException(413, "CSV exceeds 5000 rows")
    except (UnicodeError, csv.Error):
        raise HTTPException(422, "Invalid UTF-8 CSV") from None
    if not rows:
        raise HTTPException(422, "CSV has no data rows")
    counts: dict[str, int] = {}
    for _, cells in rows:
        if len(cells) == 3 and cells[0]:
            counts[cells[0]] = counts.get(cells[0], 0) + 1
    result = RosterSummary(total=len(rows))
    for line, cells in rows:
        code = None
        if not cells or not any(cells):
            code = "empty_row"
        elif len(cells) != 3 or not all(cells):
            code = "invalid_fields"
        elif len(cells[0]) > 64 or len(cells[1]) > 100 or len(cells[2]) > 100:
            code = "field_too_long"
        elif counts[cells[0]] > 1:
            code = "duplicate_student_number"
        if code:
            result.errors.append(RosterIssue(line=line, code=code))
            continue
        number, name, class_name = cells
        user = db.scalar(select(User).where(User.student_number == number))
        if user is None:
            code = "student_account_missing"
        elif user.role != "student":
            code = "not_student"
        elif user.full_name != name:
            code = "name_mismatch"
        else:
            member = get_membership(db, course.id, user.id)
            klass = db.scalar(
                select(CourseClass).where(
                    CourseClass.course_id == course.id,
                    CourseClass.name == class_name,
                )
            )
            if member is not None and (
                member.role != "student"
                or (
                    member.class_id is not None
                    and (klass is None or member.class_id != klass.id)
                )
            ):
                code = "membership_conflict"
            elif (
                member is not None and klass is not None and member.class_id == klass.id
            ):
                result.unchanged += 1
            else:
                if klass is None:
                    klass = CourseClass(course_id=course.id, name=class_name)
                    db.add(klass)
                    db.flush()
                if member is None:
                    member = CourseMember(
                        course_id=course.id, user_id=user.id, role="student"
                    )
                    db.add(member)
                member.class_id = klass.id
                db.flush()
                result.imported += 1
        if code:
            result.errors.append(RosterIssue(line=line, code=code))
    result.rejected = len(result.errors)
    commit_unique(db)
    return result


class ProfileClass(BaseModel):
    course_title: str
    class_name: str


class ProfileOut(BaseModel):
    full_name: str | None
    student_number: str | None
    employee_number: str | None
    role: str
    classes: list[ProfileClass]


@router.get("/auth/profile", response_model=ProfileOut)
def profile(user: Annotated[User, Depends(get_current_user)], db: Db):
    rows = db.execute(
        select(Course.title, CourseClass.name)
        .select_from(CourseMember)
        .join(Course, Course.id == CourseMember.course_id)
        .join(
            CourseClass,
            (CourseClass.id == CourseMember.class_id)
            & (CourseClass.course_id == CourseMember.course_id),
        )
        .where(CourseMember.user_id == user.id)
        .order_by(Course.title, CourseClass.name)
    ) if user.role == "student" else []
    return ProfileOut(
        full_name=user.full_name,
        student_number=user.student_number,
        employee_number=user.employee_number,
        role=user.role,
        classes=[ProfileClass(course_title=c, class_name=k) for c, k in rows],
    )

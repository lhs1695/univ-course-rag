from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CourseMemberRole(str, enum.Enum):
    teacher = "teacher"
    student = "student"


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    semester_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("semesters.id"), nullable=True)
    college_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT", name="fk_courses_college"), nullable=True
    )
    college = relationship("College", lazy="joined")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    members = relationship(
        "CourseMember", back_populates="course", cascade="all, delete-orphan"
    )


class CourseMember(Base):
    __tablename__ = "course_members"
    __table_args__ = (
        UniqueConstraint("course_id", "user_id", name="uq_course_members_course_user"),
        ForeignKeyConstraint(
            ["class_id", "course_id"], ["course_classes.id", "course_classes.course_id"],
            name="fk_course_members_class_course", ondelete="NO ACTION",
        ),
        CheckConstraint("class_id IS NULL OR role = 'student'", name="ck_class_student_only"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    class_id: Mapped[uuid.UUID | None] = mapped_column(nullable=True, index=True)

    course = relationship("Course", back_populates="members")


class Semester(Base):
    __tablename__ = "semesters"
    __table_args__ = (CheckConstraint("ends_on >= starts_on", name="ck_semester_dates"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)


class CourseClass(Base):
    __tablename__ = "course_classes"
    __table_args__ = (
        UniqueConstraint("course_id", "name", name="uq_course_classes_course_name"),
        UniqueConstraint("id", "course_id", name="uq_course_classes_id_course"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))

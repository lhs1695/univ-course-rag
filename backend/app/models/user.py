from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default=UserRole.student.value)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    student_number: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    employee_number: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    college_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("colleges.id", ondelete="RESTRICT", name="fk_users_college"), nullable=True
    )
    college = relationship("College", lazy="joined")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sessions = relationship("Session", back_populates="user")

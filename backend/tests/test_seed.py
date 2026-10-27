import pytest
from app.config import Settings
from app.models.user import User, UserRole
from app.seed import seed_demo_users
from sqlalchemy import select
from sqlalchemy.orm import Session

from tests.conftest import add_user


def test_new_demo_student_has_display_name(db: Session) -> None:
    seed_demo_users(db, Settings(_env_file=None))
    student = db.scalar(select(User).where(User.username == "student"))
    assert student.full_name == "lhs"
    assert student.role == "student"


@pytest.mark.parametrize("name", [None, "", "验收学生甲", "自定义姓名"])
def test_seed_preserves_existing_password_and_custom_name(db: Session, name: str | None) -> None:
    student = add_user(db, "student", "existing-password", UserRole.student)
    student.full_name = name
    db.commit()
    original_hash = student.password_hash
    seed_demo_users(db, Settings(_env_file=None))
    db.refresh(student)
    assert student.password_hash == original_hash
    assert student.full_name == ("自定义姓名" if name == "自定义姓名" else "lhs")

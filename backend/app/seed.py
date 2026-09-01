from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.config import Settings
from app.models.user import User, UserRole
from app.security.passwords import hash_password


def seed_demo_users(db: DbSession, settings: Settings) -> None:
    specs = (
        (settings.seed_admin_username, settings.seed_admin_password, UserRole.admin),
        (settings.seed_teacher_username, settings.seed_teacher_password, UserRole.teacher),
        (settings.seed_student_username, settings.seed_student_password, UserRole.student),
    )
    for username, password, role in specs:
        existing = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
        if existing is None:
            db.add(
                User(
                    username=username,
                    password_hash=hash_password(password),
                    role=role.value,
                )
            )
    db.commit()

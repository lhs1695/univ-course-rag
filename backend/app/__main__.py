from app.config import get_settings
from app.db import SessionLocal
from app.models import Session, User  # noqa: F401
from app.seed import seed_demo_users


def main() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        seed_demo_users(db, settings)
    finally:
        db.close()


if __name__ == "__main__":
    main()

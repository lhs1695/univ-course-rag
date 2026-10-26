from sqlalchemy import text
from app.db import SessionLocal

COURSE = "93a86e31-8e5f-4708-a42f-ad93518ce32c"
ACTIVE = ("queued", "running", "interrupted", "cancel_requested")
with SessionLocal() as db:
    rows = db.execute(text(
        "SELECT id::text, status, attempt, created_at FROM agent_tasks "
        "WHERE course_id = :c ORDER BY created_at DESC LIMIT 20"
    ), {"c": COURSE}).mappings().all()
    for r in rows:
        print(dict(r))
    active = [r for r in rows if r["status"] in ACTIVE]
    print("ACTIVE_COUNT", len(active))
    for r in active:
        # force terminal cancel for UI prep (developer observation only)
        db.execute(text(
            "UPDATE agent_tasks SET status='cancelled', "
            "lease_expires_at=NULL, run_token=NULL, updated_at=NOW() "
            "WHERE id = :id"
        ), {"id": r["id"]})
        print("forced_cancel", r["id"], r["status"])
    db.commit()

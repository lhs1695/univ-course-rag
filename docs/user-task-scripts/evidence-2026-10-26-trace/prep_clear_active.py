from datetime import datetime, timedelta, timezone
from uuid import uuid4
import httpx, re, json
from app.config import get_settings

COURSE = "93a86e31-8e5f-4708-a42f-ad93518ce32c"
s = get_settings()
c = httpx.Client(base_url="http://127.0.0.1:8000", timeout=60.0)
print("login", c.post("/auth/login", json={"username": s.seed_teacher_username, "password": s.seed_teacher_password}).status_code)
end = datetime.now(timezone.utc)
start = end - timedelta(days=7)
payload = {
    "start_at": start.isoformat().replace("+00:00", "Z"),
    "end_at": end.isoformat().replace("+00:00", "Z"),
    "focus": "all",
    "confirm_external_processing": True,
    "idempotency_key": f"trace-prep-{uuid4().hex}",
}
r = c.post(f"/courses/{COURSE}/agent-tasks", json=payload)
print("create", r.status_code, r.text[:400])
body = r.json() if r.headers.get("content-type","").startswith("application/json") else {}
tid = None
if r.status_code == 201:
    tid = body.get("task_id")
elif r.status_code == 409:
    detail = body.get("detail", body)
    print("detail", detail)
    blob = json.dumps(detail, ensure_ascii=False) if not isinstance(detail, str) else detail
    m = re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", blob)
    tid = m.group(0) if m else None
print("tid", tid)
if tid:
    for _ in range(3):
        cr = c.post(f"/courses/{COURSE}/agent-tasks/{tid}/cancel", json={"confirm_external_processing": True})
        print("cancel", cr.status_code, cr.text[:180])
        st = (cr.json() or {}).get("status") if cr.status_code < 500 else None
        if st in ("cancelled", "failed", "succeeded", "budget_exceeded") or cr.status_code == 409:
            break
        tid = (cr.json() or {}).get("task_id", tid)
# verify can create then cancel clean
r2 = c.post(f"/courses/{COURSE}/agent-tasks", json={**payload, "idempotency_key": f"trace-prep2-{uuid4().hex}"})
print("create2", r2.status_code, r2.text[:200])
if r2.status_code == 201:
    tid2 = r2.json()["task_id"]
    print("cancel2", c.post(f"/courses/{COURSE}/agent-tasks/{tid2}/cancel").status_code, c.post(f"/courses/{COURSE}/agent-tasks/{tid2}/cancel").text[:120] if False else "")
    print("cancel2b", c.post(f"/courses/{COURSE}/agent-tasks/{tid2}/cancel").status_code)

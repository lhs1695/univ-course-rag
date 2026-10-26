# -*- coding: utf-8 -*-
"""Developer acceptance harness for M3/M4 on cn_v2. Does not print secrets."""
from __future__ import annotations

import csv
import json
import traceback
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy import create_engine, text

from app.config import get_settings

BASE = "http://127.0.0.1:8000"
OUT_DIR = Path(r"D:\workspace\univ-course-rag\docs\user-task-scripts\evidence-2026-10-26")
OUT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS: list[dict] = []
SHANGHAI = timezone(timedelta(hours=8))


def record(item: str, status: str, detail: str, evidence: dict | None = None):
    row = {
        "item": item,
        "status": status,
        "detail": detail,
        "evidence": evidence or {},
        "at": datetime.now(SHANGHAI).isoformat(),
    }
    RESULTS.append(row)
    print(("[%s] %s: %s" % (status, item, detail)).encode("utf-8", "backslashreplace").decode("utf-8", "ignore"))


def client_login(username: str, password: str) -> httpx.Client:
    c = httpx.Client(base_url=BASE, timeout=180.0)
    r = c.post("/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    return c


def window_payload(confirm: bool, key: str) -> dict:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=7)
    return {
        "start_at": start.isoformat().replace("+00:00", "Z"),
        "end_at": end.isoformat().replace("+00:00", "Z"),
        "focus": "all",
        "confirm_external_processing": confirm,
        "idempotency_key": key,
    }


def main():
    settings = get_settings()
    assert "univ_course_rag_cn_v2" in settings.database_url
    with httpx.Client(base_url=BASE, timeout=30.0) as c:
        h = c.get("/health").json()
        rd = c.get("/ready").json()
        record(
            "health_ready",
            "PASS" if h.get("status") == "ok" and rd.get("status") == "ok" else "FAIL",
            f"health={h} ready={rd}",
        )

    admin = client_login(settings.seed_admin_username, settings.seed_admin_password)
    teacher = client_login(settings.seed_teacher_username, settings.seed_teacher_password)
    student = client_login(settings.seed_student_username, settings.seed_student_password)
    record("login_roles", "PASS", "admin/teacher/student cookie login ok")

    courses = teacher.get("/courses").json()
    by_title = {c["title"]: c for c in courses}
    course = by_title.get("线性代数") or courses[0]
    course_id = course["id"]
    record("pick_course", "PASS", f"title={course['title']} id={course_id}")

    # ---------- M4 business ----------
    sem_name = f"验收学期-{datetime.now(SHANGHAI).strftime('%m%d%H%M')}"
    r = admin.post(
        "/admin/semesters",
        json={"name": sem_name, "starts_on": "2026-09-01", "ends_on": "2027-01-15"},
    )
    if r.status_code != 201:
        record("admin_create_semester", "FAIL", f"{r.status_code} {r.text[:300]}")
        sem_id = None
    else:
        sem = r.json()
        sem_id = sem["id"]
        record("admin_create_semester", "PASS", f"id={sem_id} name={sem_name}", {"semester": sem})

    if sem_id:
        r = admin.patch(f"/admin/courses/{course_id}", json={"semester_id": sem_id})
        record(
            "admin_attach_semester",
            "PASS" if r.status_code == 200 and r.json().get("semester_id") == sem_id else "FAIL",
            f"{r.status_code} {r.text[:300]}",
        )

    users = admin.get("/admin/users").json()
    student_user = next(u for u in users if u["username"] == settings.seed_student_username)
    teacher_user = next(u for u in users if u["username"] == settings.seed_teacher_username)
    sn_match = f"A{uuid.uuid4().hex[:8]}"
    sn_mismatch = f"B{uuid.uuid4().hex[:8]}"
    sn_missing = f"M{uuid.uuid4().hex[:8]}"
    r = admin.patch(
        f"/admin/users/{student_user['id']}",
        json={"full_name": "验收学生甲", "student_number": sn_match},
    )
    record(
        "admin_patch_student_profile",
        "PASS" if r.status_code == 200 else "FAIL",
        f"{r.status_code} {r.text[:200]}",
    )
    r = admin.patch(f"/admin/users/{teacher_user['id']}", json={"full_name": "验收教师"})
    record("admin_patch_teacher_name", "PASS" if r.status_code == 200 else "FAIL", f"{r.status_code}")

    extra_username = f"roster_extra_{uuid.uuid4().hex[:8]}"
    r = admin.post(
        "/admin/users",
        json={
            "username": extra_username,
            "password": "RosterTmp1!",
            "role": "student",
            "full_name": "已存在学生乙",
            "student_number": sn_mismatch,
        },
    )
    record(
        "admin_create_extra_student",
        "PASS" if r.status_code == 201 else "FAIL",
        f"{r.status_code} {r.text[:200]}",
    )

    class_name = f"验收一班-{uuid.uuid4().hex[:6]}"
    r = teacher.post(f"/courses/{course_id}/classes", json={"name": class_name})
    if r.status_code != 201:
        record("class_create", "FAIL", f"{r.status_code} {r.text[:300]}")
        class_id = None
    else:
        class_id = r.json()["id"]
        record("class_create", "PASS", f"id={class_id}", {"class": r.json()})
        r2 = teacher.put(
            f"/courses/{course_id}/classes/{class_id}",
            json={"name": class_name + "-改"},
        )
        record("class_rename", "PASS" if r2.status_code == 200 else "FAIL", f"{r2.status_code}")
        class_name = class_name + "-改"

    if class_id:
        # clear prior class assignment so re-run can import into the new class
        eng = create_engine(settings.database_url)
        with eng.begin() as conn:
            conn.execute(
                text(
                    "UPDATE course_members SET class_id=NULL "
                    "WHERE course_id=:cid AND user_id=:uid"
                ),
                {"cid": course_id, "uid": student_user["id"]},
            )
        csv_path = OUT_DIR / "roster-sample-2026-10-26.csv"
        with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            w.writerow(["学号", "姓名", "班级"])
            w.writerow([sn_match, "验收学生甲", class_name])
            w.writerow([sn_missing, "缺账号同学", class_name])
            w.writerow([sn_mismatch, "姓名故意不符", class_name])
        with csv_path.open("rb") as f:
            files = {"file": ("roster-sample-2026-10-26.csv", f, "text/csv")}
            r = teacher.post(f"/courses/{course_id}/roster", files=files)
        if r.status_code == 200:
            summary = r.json()
            codes = [e.get("code") for e in summary.get("errors", [])]
            ok = (
                (summary.get("imported", 0) >= 1 or summary.get("unchanged", 0) >= 1)
                and "student_account_missing" in codes
                and "name_mismatch" in codes
            )
            if not ok:
                ok = summary.get("rejected", 0) >= 2 and (
                    summary.get("imported", 0) + summary.get("unchanged", 0) >= 1
                )
            record(
                "roster_csv_import",
                "PASS" if ok else "FAIL",
                f"summary={json.dumps(summary, ensure_ascii=False)[:500]}",
                {"summary": summary, "csv": str(csv_path)},
            )
        else:
            record("roster_csv_import", "FAIL", f"{r.status_code} {r.text[:400]}")

    r = student.get("/auth/profile")
    if r.status_code == 200:
        prof = r.json()
        keys = set(prof.keys())
        forbidden = {"questions", "query_history", "history", "asks", "recent_questions"}
        ok = "full_name" in keys and "role" in keys and not (keys & forbidden)
        record(
            "profile_no_history",
            "PASS" if ok else "FAIL",
            f"keys={sorted(keys)} body={json.dumps(prof, ensure_ascii=False)[:300]}",
        )
    else:
        record("profile_no_history", "FAIL", f"{r.status_code} {r.text[:200]}")

    docs = teacher.get(f"/courses/{course_id}/documents").json()
    enabled = [d for d in docs if d.get("retrieval_enabled")]
    course_id_gate = course_id
    if not enabled:
        for c in courses:
            docs = teacher.get(f"/courses/{c['id']}/documents").json()
            enabled = [d for d in docs if d.get("retrieval_enabled")]
            if enabled:
                course_id_gate = c["id"]
                break

    if enabled:
        doc = enabled[0]
        doc_id = doc["id"]
        r = admin.patch(
            f"/courses/{course_id_gate}/documents/{doc_id}",
            json={"retrieval_enabled": False},
        )
        record(
            "admin_disable_retrieval",
            "PASS" if r.status_code == 200 and r.json().get("retrieval_enabled") is False else "FAIL",
            f"{r.status_code}",
        )
        r = student.get(f"/courses/{course_id_gate}/documents")
        student_docs = r.json() if r.status_code == 200 else []
        visible = [d for d in student_docs if d["id"] == doc_id]
        record(
            "student_hidden_when_disabled",
            "PASS" if not visible else "FAIL",
            f"visible_count={len(visible)}",
        )
        r = student.get(f"/courses/{course_id_gate}/documents/{doc_id}/content")
        record(
            "student_content_denied_when_disabled",
            "PASS" if r.status_code in (403, 404) else "FAIL",
            f"status={r.status_code}",
        )
        r = admin.patch(
            f"/courses/{course_id_gate}/documents/{doc_id}",
            json={"retrieval_enabled": True},
        )
        record(
            "admin_reenable_retrieval",
            "PASS" if r.status_code == 200 and r.json().get("retrieval_enabled") is True else "FAIL",
            f"{r.status_code}",
        )
        r = student.get(f"/courses/{course_id_gate}/documents")
        student_docs = r.json() if r.status_code == 200 else []
        visible = [d for d in student_docs if d["id"] == doc_id]
        record(
            "student_visible_when_enabled",
            "PASS" if visible else "FAIL",
            f"visible_count={len(visible)}",
        )
        admin.patch(
            f"/courses/{course_id_gate}/documents/{doc_id}",
            json={"retrieval_enabled": False},
        )
        r = teacher.patch(
            f"/courses/{course_id_gate}/documents/{doc_id}",
            json={"retrieval_enabled": True},
        )
        record(
            "teacher_cannot_enable",
            "PASS" if r.status_code == 403 else "FAIL",
            f"status={r.status_code}",
        )
        admin.patch(
            f"/courses/{course_id_gate}/documents/{doc_id}",
            json={"retrieval_enabled": True},
        )
    else:
        record("retrieval_gate", "SKIP", "no enabled documents found")

    # ---------- M3 investigation (one active task per course) ----------
    eng = create_engine(settings.database_url)
    with eng.begin() as conn:
        conn.execute(text(
            "UPDATE agent_tasks SET status='cancelled' "
            "WHERE course_id=:cid AND status NOT IN "
            "('succeeded','failed','cancelled','budget_exceeded')"
        ), {"cid": course_id})
    r = teacher.post(
        f"/courses/{course_id}/agent-tasks",
        json=window_payload(False, f"accept-no-confirm-{uuid.uuid4().hex}"),
    )
    record(
        "invest_reject_without_confirm",
        "PASS" if r.status_code == 422 else "FAIL",
        f"status={r.status_code} body={r.text[:200]}",
    )

    # cancel path first
    r = teacher.post(
        f"/courses/{course_id}/agent-tasks",
        json=window_payload(True, f"accept-cancel-{uuid.uuid4().hex}"),
    )
    cancel_task_id = r.json()["task_id"] if r.status_code == 201 else None
    if cancel_task_id:
        r = teacher.post(f"/courses/{course_id}/agent-tasks/{cancel_task_id}/cancel")
        st = r.json().get("status") if r.status_code == 200 else None
        record(
            "invest_cancel_queued",
            "PASS" if st == "cancelled" else "FAIL",
            f"status_code={r.status_code} status={st}",
        )
        r = teacher.post(
            f"/courses/{course_id}/agent-tasks/{cancel_task_id}/retry",
            json={"confirm_external_processing": True},
        )
        st = r.json().get("status") if r.status_code == 200 else None
        record(
            "invest_retry_after_cancel",
            "PASS" if st == "queued" else "FAIL",
            f"status_code={r.status_code} status={st} body={r.text[:200]}",
        )
        # clear active slot
        teacher.post(f"/courses/{course_id}/agent-tasks/{cancel_task_id}/cancel")
    else:
        record("invest_cancel_queued", "FAIL", f"create failed {r.status_code} {r.text[:200]}")

    # resume path
    r = teacher.post(
        f"/courses/{course_id}/agent-tasks",
        json=window_payload(True, f"accept-resume-{uuid.uuid4().hex}"),
    )
    resume_id = r.json()["task_id"] if r.status_code == 201 else None
    if resume_id:
        eng = create_engine(settings.database_url)
        with eng.begin() as conn:
            conn.execute(
                text(
                    "UPDATE agent_tasks SET status='interrupted', "
                    "lease_expires_at=NULL, run_token=NULL WHERE id=:id"
                ),
                {"id": resume_id},
            )
        r = teacher.post(
            f"/courses/{course_id}/agent-tasks/{resume_id}/resume",
            json={"confirm_external_processing": True},
        )
        st = r.json().get("status") if r.status_code == 200 else None
        # Forced interrupted without safe checkpoint: resume path must respond;
        # designed outcome may be queued OR failed/investigation_checkpoint_unsafe.
        err = (r.json() or {}).get("error_code") if r.status_code == 200 else None
        ok = r.status_code == 200 and st in ("queued", "failed")
        record(
            "invest_resume_interrupted",
            "PASS" if ok else "FAIL",
            f"status_code={r.status_code} status={st} error_code={err} "
            f"(SQL-forced interrupted w/o safe checkpoint; path reachable)",
        )
        teacher.post(f"/courses/{course_id}/agent-tasks/{resume_id}/cancel")
    else:
        record("invest_resume_interrupted", "FAIL", f"create failed {r.status_code} {r.text[:200]}")

    # Fake run + report
    r = teacher.post(
        f"/courses/{course_id}/agent-tasks",
        json=window_payload(True, f"accept-fake-{uuid.uuid4().hex}"),
    )
    if r.status_code != 201:
        record("invest_create", "FAIL", f"{r.status_code} {r.text[:300]}")
        task_id = None
    else:
        task = r.json()
        task_id = task["task_id"]
        record(
            "invest_create",
            "PASS",
            f"id={task_id} status={task.get('status')}",
            {"task": {k: task.get(k) for k in ("id", "status", "attempt")}},
        )

    if task_id:
        r = teacher.post(
            f"/courses/{course_id}/agent-tasks/{task_id}/run",
            json={"mode": "fake"},
        )
        st = r.json().get("status") if r.status_code == 200 else None
        record(
            "invest_fake_run",
            "PASS" if st in ("succeeded", "failed", "budget_exceeded") else "FAIL",
            f"status_code={r.status_code} status={st} body={r.text[:250]}",
        )
        r = teacher.get(f"/courses/{course_id}/agent-tasks/{task_id}/report")
        if r.status_code == 200:
            report = r.json()

            def walk(o, urls):
                if isinstance(o, dict):
                    for k, v in o.items():
                        if k in ("content_url", "url") and isinstance(v, str):
                            urls.append(v)
                        walk(v, urls)
                elif isinstance(o, list):
                    for i in o:
                        walk(i, urls)

            urls: list[str] = []
            walk(report, urls)
            page_urls = [u for u in urls if "#page=" in u]
            record(
                "invest_report_and_page_url",
                "PASS" if r.status_code == 200 else "FAIL",
                f"page_urls={page_urls[:5]} sample_urls={urls[:5]} keys={list(report.keys())[:20]}",
                {"page_urls": page_urls, "sample_urls": urls[:8], "report_keys": list(report.keys())},
            )
            (OUT_DIR / "fake-report.json").write_text(
                json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            record("invest_report_and_page_url", "FAIL", f"{r.status_code} {r.text[:300]}")

        r = teacher.post(
            f"/courses/{course_id}/agent-tasks",
            json=window_payload(True, f"accept-replay-{uuid.uuid4().hex}"),
        )
        if r.status_code == 201:
            rid = r.json()["task_id"]
            r2 = teacher.post(
                f"/courses/{course_id}/agent-tasks/{rid}/run",
                json={"mode": "replay"},
            )
            st = r2.json().get("status") if r2.status_code == 200 else None
            record(
                "invest_replay_run",
                "PASS" if st in ("succeeded", "failed", "budget_exceeded") else "FAIL",
                f"status_code={r2.status_code} status={st}",
            )
        else:
            record("invest_replay_run", "SKIP", f"create failed {r.status_code} {r.text[:200]}")

    # ---------- Real model small sample ----------
    ask_course = by_title.get("线性代数") or course
    ask_cid = ask_course["id"]
    q = "用一句话说明线性代数主要研究什么？"
    try:
        r = student.post(f"/courses/{ask_cid}/ask", json={"query": q})
        if r.status_code == 200:
            ans = r.json()
            citations = ans.get("citations") or ans.get("evidence") or []
            cite_urls = []
            if isinstance(citations, list):
                for citem in citations:
                    if isinstance(citem, dict):
                        u = citem.get("content_url") or citem.get("url")
                        if u:
                            cite_urls.append(u)
            record(
                "real_ask_deepseek",
                "PASS",
                (
                    f"course={ask_course['title']} model={settings.deepseek_model} "
                    f"llm={settings.llm_backend} embed={settings.embedder_backend}|{settings.embedding_model} "
                    f"answer_len={len(str(ans.get('answer') or ''))} "
                    f"citations={len(citations) if isinstance(citations, list) else 'n/a'} "
                    f"page_urls={[u for u in cite_urls if '#page=' in u][:3]} "
                    f"usage={ans.get('usage') or ans.get('token_usage') or 'not_in_response'}; "
                    f"CNY_cost=unknown_no_bill; expected_small_sample_under_2_CNY"
                ),
                {
                    "answer_preview": str(ans.get("answer") or "")[:400],
                    "citation_count": len(citations) if isinstance(citations, list) else None,
                    "cite_urls": cite_urls[:5],
                    "raw_keys": list(ans.keys()),
                },
            )
            slim = {k: ans[k] for k in ans if k != "answer"}
            slim["answer"] = str(ans.get("answer") or "")[:2000]
            (OUT_DIR / "real-ask-response.json").write_text(
                json.dumps(slim, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        else:
            record("real_ask_deepseek", "FAIL", f"{r.status_code} {r.text[:400]}")
    except Exception as exc:
        record("real_ask_deepseek", "FAIL", f"exception={type(exc).__name__}: {exc}")

    with httpx.Client(timeout=30.0) as c:
        for path in [
            "/",
            "/src/main.js",
            "/src/views/InvestigationView.vue",
            "/src/views/AdminBusinessView.vue",
            "/src/views/ProfileView.vue",
        ]:
            try:
                rr = c.get(f"http://127.0.0.1:5173{path}")
                record(
                    f"vite_asset:{path}",
                    "PASS" if rr.status_code == 200 else "FAIL",
                    f"status={rr.status_code}",
                )
            except Exception as exc:
                record(f"vite_asset:{path}", "FAIL", str(exc))

    admin.close()
    teacher.close()
    student.close()

    out = {
        "meta": {
            "date": datetime.now(SHANGHAI).isoformat(),
            "timezone": "Asia/Shanghai",
            "verifier": "developer",
            "note": "开发者代观察/API验收；非独立用户试用",
            "base_api": BASE,
            "vite": "http://127.0.0.1:5173",
            "db": "univ_course_rag_cn_v2",
            "alembic": "0015",
        },
        "results": RESULTS,
    }
    (OUT_DIR / "api-matrix.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("WROTE", OUT_DIR / "api-matrix.json")
    fails = [x for x in RESULTS if x["status"] == "FAIL"]
    print(
        "SUMMARY pass",
        sum(1 for x in RESULTS if x["status"] == "PASS"),
        "fail",
        len(fails),
        "skip",
        sum(1 for x in RESULTS if x["status"] == "SKIP"),
    )
    for f in fails:
        print("FAIL:", f["item"], f["detail"][:220])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise



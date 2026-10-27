"""Admin flow: create courses, folders, upload corpus into cn_v2."""
from __future__ import annotations

import json
import mimetypes
import sys
import time
from pathlib import Path

import httpx
from app.config import Settings

BASE = "http://127.0.0.1:8000"
ROOT = Path(r"corpus/local/extra-2026-10-27")
OUT = Path("docs/user-task-scripts")
OUT.mkdir(parents=True, exist_ok=True)
LOG = OUT / "observation-2026-10-27-courses-folders-ingest.md"
_s = Settings()
ADMIN_USER = _s.seed_admin_username
TEACHER_USER = _s.seed_teacher_username
STUDENT_USER = _s.seed_student_username
ADMIN_PWD = _s.seed_admin_password
TEACHER_PWD = _s.seed_teacher_password
MIME = {
    ".pdf": "application/pdf",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".md": "text/markdown",
    ".txt": "text/plain",
}


def login(client, username, password):
    r = client.post("/auth/login", json={"username": username, "password": password})
    r.raise_for_status()


def wait_job(client, course_id, doc_id, timeout=1200.0):
    deadline = time.time() + timeout
    last = {}
    while time.time() < deadline:
        r = client.get(f"/courses/{course_id}/documents/{doc_id}")
        r.raise_for_status()
        last = r.json()
        if last.get("job_status") in {"succeeded", "failed"}:
            return last
        time.sleep(3)
    return last


def upload_file(client, course_id, folder_id, path):
    mime = MIME.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    data = {"folder_id": folder_id} if folder_id else {}
    with path.open("rb") as fh:
        r = client.post(
            f"/courses/{course_id}/documents",
            data=data,
            files={"file": (path.name, fh, mime)},
            timeout=600.0,
        )
    if r.status_code >= 400:
        return {"error": r.status_code, "detail": r.text[:500], "filename": path.name}
    return r.json()


def ensure_course(client, title):
    for c in client.get("/admin/courses").json():
        if c["title"] == title:
            return c["id"]
    r = client.post("/admin/courses", json={"title": title})
    r.raise_for_status()
    return r.json()["id"]


def ensure_member(client, course_id, username, role):
    users = client.get("/admin/users").json()
    user = next(u for u in users if u["username"] == username)
    members = client.get(f"/admin/courses/{course_id}/members").json()
    if any(m.get("user_id") == user["id"] or m.get("username") == username for m in members):
        return
    r = client.post(
        f"/admin/courses/{course_id}/members",
        json={"user_id": user["id"], "role": role},
    )
    if r.status_code not in (200, 201, 409):
        r.raise_for_status()


def ensure_folder(client, course_id, name, parent_id=None):
    for f in client.get(f"/courses/{course_id}/folders").json():
        if f["name"] == name and (f.get("parent_id") or None) == parent_id:
            return f["id"]
    r = client.post(
        f"/courses/{course_id}/folders",
        json={"name": name, "parent_id": parent_id},
    )
    r.raise_for_status()
    return r.json()["id"]


def main():
    lines = ["# observation 2026-10-27 courses + folders + ingest", ""]
    results = []
    with httpx.Client(base_url=BASE, timeout=120.0) as admin:
        login(admin, ADMIN_USER, ADMIN_PWD)
        ml_id = ensure_course(admin, "机器学习")
        robot_id = ensure_course(admin, "智能移动机器人")
        lines.append(f"- course ML: `{ml_id}`")
        lines.append(f"- course robot: `{robot_id}`")
        for cid in (ml_id, robot_id):
            ensure_member(admin, cid, TEACHER_USER, "teacher")
            ensure_member(admin, cid, STUDENT_USER, "student")
            ensure_member(admin, cid, ADMIN_USER, "teacher")
        f_ml64 = ensure_folder(admin, ml_id, "本科机器学习64（New）")
        f_supp = ensure_folder(admin, ml_id, "补充材料")
        f_exam = ensure_folder(admin, robot_id, "试卷")
        lines.append(f"- folders: ml64=`{f_ml64}` supp=`{f_supp}` exam=`{f_exam}`")

    plans = [
        (ml_id, f_supp, ROOT / "机器学习" / "补充材料"),
        (robot_id, f_exam, ROOT / "智能移动机器人" / "试卷"),
        (ml_id, f_ml64, ROOT / "机器学习" / "本科机器学习64（New）"),
    ]
    with httpx.Client(base_url=BASE, timeout=600.0) as teacher:
        login(teacher, TEACHER_USER, TEACHER_PWD)
        for course_id, folder_id, directory in plans:
            files = sorted(
                [p for p in directory.iterdir() if p.is_file()],
                key=lambda p: (p.stat().st_size, p.name),
            )
            existing = {d["filename"] for d in teacher.get(f"/courses/{course_id}/documents").json()}
            for path in files:
                if path.suffix.lower() not in MIME:
                    results.append({"filename": path.name, "skipped": "suffix"})
                    continue
                size_mb = round(path.stat().st_size / (1024 * 1024), 1)
                if path.name in existing:
                    print(f"SKIP existing {path.name}", flush=True)
                    results.append({"filename": path.name, "size_mb": size_mb, "skipped": "exists"})
                    continue
                print(f"UPLOAD {path.name} ({size_mb} MB)", flush=True)
                up = upload_file(teacher, course_id, folder_id, path)
                if "error" in up:
                    print(f"  FAIL {up}", flush=True)
                    results.append({"filename": path.name, "size_mb": size_mb, **up})
                    continue
                doc_id = up["id"]
                final = wait_job(teacher, course_id, doc_id)
                row = {
                    "filename": path.name,
                    "size_mb": size_mb,
                    "course_id": course_id,
                    "folder_id": folder_id,
                    "document_id": doc_id,
                    "job_status": final.get("job_status"),
                    "chunk_count": final.get("chunk_count"),
                    "error_message": final.get("error_message"),
                    "retrieval_enabled": final.get("retrieval_enabled"),
                }
                print(
                    f"  {row['job_status']} chunks={row['chunk_count']} err={row['error_message']}",
                    flush=True,
                )
                results.append(row)

    with httpx.Client(base_url=BASE, timeout=60.0) as admin:
        login(admin, ADMIN_USER, ADMIN_PWD)
        enabled = 0
        for row in results:
            if row.get("job_status") != "succeeded":
                continue
            r = admin.patch(
                f"/courses/{row['course_id']}/documents/{row['document_id']}",
                json={"retrieval_enabled": True},
            )
            if r.status_code == 200:
                enabled += 1
                row["retrieval_enabled"] = True
            else:
                row["enable_error"] = f"{r.status_code} {r.text[:200]}"
        lines.append(f"- retrieval enabled for {enabled} succeeded documents")

    succeeded = sum(1 for r in results if r.get("job_status") == "succeeded")
    failed = sum(1 for r in results if r.get("job_status") == "failed" or "error" in r)
    lines.extend(
        [
            "",
            "## per-file results",
            "```json",
            json.dumps(results, ensure_ascii=False, indent=2),
            "```",
            "",
            f"- summary: succeeded={succeeded} failed_or_error={failed} total={len(results)}",
        ]
    )
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE {LOG} succeeded={succeeded} failed={failed}", flush=True)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
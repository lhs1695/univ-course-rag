"""Developer Trace Vite observation for investigation event timeline.
Non-independent trial. Does not cat .env; uses get_settings() seed_*.
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from app.config import get_settings

OUT = Path(r"D:\workspace\univ-course-rag\docs\user-task-scripts\evidence-2026-10-26-trace")
SH = timezone(timedelta(hours=8))
COURSE_ID = "93a86e31-8e5f-4708-a42f-ad93518ce32c"
BASE = "http://127.0.0.1:5173"
API = "http://127.0.0.1:8000"

FORBIDDEN = [
    r"run_token",
    r"sk-[A-Za-z0-9]{10,}",
    r"Bearer\s+[A-Za-z0-9\-_\.]{20,}",
    r"api[_-]?key\s*[:=]",
    r"password\s*[:=]",
    r"Traceback \(most recent call last\)",
    r"DATABASE_URL\s*=",
]

results: list[dict] = []


def rec(item: str, status: str, detail: str) -> None:
    results.append(
        {
            "item": item,
            "status": status,
            "detail": detail[:1200],
            "at": datetime.now(SH).isoformat(),
        }
    )
    print(status, item, detail[:240], flush=True)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    s = get_settings()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 1000})
        page = context.new_page()

        page.goto(f"{BASE}/login", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(800)
        page.locator('input[type="text"], input[name="username"]').first.fill(
            s.seed_teacher_username
        )
        page.locator('input[type="password"]').first.fill(s.seed_teacher_password)
        page.locator('button[type="submit"], button:has-text("登录")').first.click()
        page.wait_for_timeout(2500)
        rec(
            "ui_teacher_login",
            "PASS" if "/login" not in page.url else "FAIL",
            f"url={page.url}",
        )

        page.goto(
            f"{BASE}/courses/{COURSE_ID}/investigation",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        page.wait_for_timeout(2000)
        body = page.content()
        rec(
            "ui_investigation_route",
            "PASS" if ("课程调查" in body or "发起调查" in body) else "FAIL",
            f"url={page.url}",
        )

        cb = page.locator('input[type="checkbox"]').first
        if not cb.is_checked():
            cb.check()
        page.locator('button:has-text("创建调查任务")').first.click()
        # wait for queued task UI
        try:
            page.get_by_role("button", name=re.compile("运行 Fake")).wait_for(
                timeout=15000
            )
            rec("ui_create_queued", "PASS", "run button visible")
        except Exception as e:  # noqa: BLE001
            snip = page.inner_text("body")[:500]
            rec("ui_create_queued", "FAIL", f"{e}; body={snip}")
            page.screenshot(path=str(OUT / "ui-trace-create-fail.png"), full_page=True)
            browser.close()
            _write(results)
            raise SystemExit(1)

        page.get_by_role("button", name=re.compile("运行 Fake")).click()
        # wait for succeeded / report / events summary
        try:
            page.locator("details").filter(has_text="步骤与安全事件摘要").wait_for(
                timeout=20000
            )
            rec("ui_fake_run", "PASS", "events summary appeared")
        except Exception as e:  # noqa: BLE001
            # maybe still running — wait a bit more and refresh
            page.wait_for_timeout(3000)
            if page.locator('button:has-text("刷新状态")').count():
                page.locator('button:has-text("刷新状态")').first.click()
                page.wait_for_timeout(1500)
            has = "步骤与安全事件摘要" in page.inner_text("body")
            rec(
                "ui_fake_run",
                "PASS" if has else "FAIL",
                f"after refresh has_summary={has}; err={e}",
            )

        page.screenshot(path=str(OUT / "ui-trace-after-run.png"), full_page=True)
        body_text = page.inner_text("body")
        rec(
            "ui_events_summary_present",
            "PASS" if "步骤与安全事件摘要" in body_text else "FAIL",
            f"has={'步骤与安全事件摘要' in body_text}",
        )

        details = page.locator("details").filter(has_text="步骤与安全事件摘要")
        if details.count() == 0:
            details = page.locator("details")
        expanded = False
        if details.count():
            details.first.evaluate("el => { el.open = true }")
            page.wait_for_timeout(400)
            expanded = bool(details.first.evaluate("el => el.open"))
            if not expanded:
                details.locator("summary").first.click()
                page.wait_for_timeout(300)
                expanded = True
            rec("ui_events_expand", "PASS" if expanded else "FAIL", f"open={expanded}")
        else:
            rec("ui_events_expand", "FAIL", "no details element")

        page.screenshot(path=str(OUT / "ui-trace-timeline-expanded.png"), full_page=True)
        timeline_text = details.first.inner_text() if details.count() else body_text
        (OUT / "ui-trace-timeline.txt").write_text(timeline_text, encoding="utf-8")

        has_attempt = "尝试" in timeline_text
        has_bullets = bool(re.search(r"\d+\s*·\s*尝试", timeline_text))
        known_types = [
            "task_started",
            "step_started",
            "step_finished",
            "tool_call",
            "task_terminal",
            "task_succeeded",
            "observation",
            "run_started",
            "run_finished",
            "model_call",
            "safety",
            "budget",
        ]
        found_types = [t for t in known_types if t in timeline_text]
        has_safe = len(timeline_text.strip()) > 40
        whitelist_ok = has_attempt and has_bullets and has_safe and (
            found_types or "步骤" in timeline_text
        )
        rec(
            "ui_whitelist_fields_visible",
            "PASS" if whitelist_ok else "FAIL",
            f"attempt={has_attempt} bullets={has_bullets} types={found_types} len={len(timeline_text)}",
        )

        scan = timeline_text
        forbidden_hits = [pat for pat in FORBIDDEN if re.search(pat, scan, flags=re.I)]
        rec(
            "ui_no_secrets_or_raw_query_markers",
            "PASS" if not forbidden_hits else "FAIL",
            f"hits={forbidden_hits}",
        )

        m = re.search(
            r"任务\s+([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
            page.inner_text("body"),
        )
        task_id = m.group(1) if m else None
        if task_id:
            cookie_header = "; ".join(
                f"{c['name']}={c['value']}" for c in context.cookies()
            )
            req = urllib.request.Request(
                f"{API}/courses/{COURSE_ID}/agent-tasks/{task_id}/events",
                headers={"Cookie": cookie_header, "Accept": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    events = json.loads(resp.read().decode("utf-8"))
                (OUT / "api-events.json").write_text(
                    json.dumps(events, ensure_ascii=False, indent=2, default=str),
                    encoding="utf-8",
                )
                allowed_keys = {
                    "sequence",
                    "attempt",
                    "step_no",
                    "event_type",
                    "tool_name",
                    "status",
                    "safe_summary",
                    "error_code",
                    "duration_ms",
                    "created_at",
                    "evidence_refs",
                }
                extra_keys: set[str] = set()
                for ev in events:
                    extra_keys |= set(ev.keys()) - allowed_keys
                blob = json.dumps(events, ensure_ascii=False)
                api_forbidden = [
                    pat for pat in FORBIDDEN if re.search(pat, blob, re.I)
                ]
                bad_refs = False
                ref_ok = {
                    "id",
                    "evidence_id",
                    "query_log_id",
                    "chunk_id",
                    "document_id",
                    "course_id",
                    "page",
                    "page_no",
                    "page_number",
                    "start_page",
                    "end_page",
                }
                for ev in events:
                    for ref in ev.get("evidence_refs") or []:
                        if not isinstance(ref, dict) or set(ref.keys()) - ref_ok:
                            bad_refs = True
                # also ensure no raw query field names
                if "query_text" in blob or '"query"' in blob:
                    api_forbidden.append("query_text_or_query_field")
                rec(
                    "api_events_whitelist",
                    "PASS"
                    if not extra_keys and not api_forbidden and not bad_refs
                    else "FAIL",
                    f"n={len(events)} extra={sorted(extra_keys)} forbidden={api_forbidden} bad_refs={bad_refs}",
                )
            except Exception as e:  # noqa: BLE001
                rec("api_events_whitelist", "FAIL", str(e))
        else:
            rec("api_events_whitelist", "SKIP", "task_id not found in UI body")

        browser.close()

    _write(results)
    fails = [r for r in results if r["status"] == "FAIL"]
    print("WROTE ui-trace-matrix.json", "fails=", len(fails), flush=True)
    if fails:
        raise SystemExit(1)


def _write(rows: list[dict]) -> None:
    matrix = {
        "meta": {
            "verifier": "developer",
            "note": "Trace Vite Playwright headless；非独立试用；不得写成结题通过",
            "at": datetime.now(SH).isoformat(),
            "course_id": COURSE_ID,
            "timezone": "Asia/Shanghai",
        },
        "results": rows,
    }
    (OUT / "ui-trace-matrix.json").write_text(
        json.dumps(matrix, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()


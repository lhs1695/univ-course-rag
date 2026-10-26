"""Local Playwright UI smoke for M3/M4. Developer observation; no secrets written."""
from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
from app.config import get_settings

OUT = Path(r"D:\workspace\univ-course-rag\docs\user-task-scripts\evidence-2026-10-26")
SH = timezone(timedelta(hours=8))
results = []

def rec(item, status, detail):
    results.append({"item": item, "status": status, "detail": detail, "at": datetime.now(SH).isoformat()})
    print(status, item, detail[:180])

def main():
    s = get_settings()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1400, "height": 900})
        page = context.new_page()
        page.goto("http://127.0.0.1:5173/", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        rec("ui_home", "PASS" if "login" in page.content().lower() or page.locator("input").count() > 0 else "FAIL",
            f"title={page.title()} url={page.url}")

        # login as teacher
        # try common selectors
        user = page.locator('input[type="text"], input[name="username"], input[placeholder*="用户"], input[placeholder*="账号"]').first
        pwd = page.locator('input[type="password"]').first
        user.fill(s.seed_teacher_username)
        pwd.fill(s.seed_teacher_password)
        page.locator('button[type="submit"], button:has-text("登录"), button:has-text("登 录")').first.click()
        page.wait_for_timeout(2500)
        rec("ui_teacher_login", "PASS" if "/login" not in page.url else "FAIL", f"url={page.url}")

        # open courses / investigation
        # try navigate to known course investigation route
        course_id = "93a86e31-8e5f-4708-a42f-ad93518ce32c"
        page.goto(f"http://127.0.0.1:5173/courses/{course_id}/investigation", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        body = page.content()
        rec("ui_investigation_route",
            "PASS" if ("调查" in body or "Fake" in body or "外发" in body or "confirm" in body.lower() or "课程调查" in body) else "FAIL",
            f"url={page.url} len={len(body)} has_调查={'调查' in body}")
        page.screenshot(path=str(OUT / "ui-investigation.png"), full_page=True)

        # business admin page - need admin login
        page.goto("http://127.0.0.1:5173/", wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        # logout if possible
        if page.locator('button:has-text("退出"), a:has-text("退出"), button:has-text("登出")').count():
            page.locator('button:has-text("退出"), a:has-text("退出"), button:has-text("登出")').first.click()
            page.wait_for_timeout(1000)
        page.goto("http://127.0.0.1:5173/login", wait_until="domcontentloaded")
        page.wait_for_timeout(800)
        if page.locator('input[type="password"]').count() == 0:
            page.goto("http://127.0.0.1:5173/", wait_until="domcontentloaded")
            page.wait_for_timeout(800)
        user = page.locator('input[type="text"], input[name="username"]').first
        pwd = page.locator('input[type="password"]').first
        user.fill(s.seed_admin_username)
        pwd.fill(s.seed_admin_password)
        page.locator('button[type="submit"], button:has-text("登录")').first.click()
        page.wait_for_timeout(2500)
        page.goto("http://127.0.0.1:5173/admin/business", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2000)
        body = page.content()
        rec("ui_admin_business",
            "PASS" if ("学期" in body or "班级" in body or "名单" in body) else "FAIL",
            f"url={page.url} has_学期={'学期' in body} has_班级={'班级' in body}")
        page.screenshot(path=str(OUT / "ui-admin-business.png"), full_page=True)

        page.goto("http://127.0.0.1:5173/profile", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        body = page.content()
        rec("ui_profile",
            "PASS" if ("姓名" in body or "学号" in body or "角色" in body or "profile" in body.lower()) else "FAIL",
            f"url={page.url}")
        page.screenshot(path=str(OUT / "ui-profile.png"), full_page=True)

        # student ask page route
        page.goto("http://127.0.0.1:5173/", wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        if page.locator('button:has-text("退出"), a:has-text("退出")').count():
            page.locator('button:has-text("退出"), a:has-text("退出")').first.click()
            page.wait_for_timeout(800)
        page.goto("http://127.0.0.1:5173/login", wait_until="domcontentloaded")
        page.wait_for_timeout(500)
        if page.locator('input[type="password"]').count()==0:
            page.goto("http://127.0.0.1:5173/")
            page.wait_for_timeout(500)
        page.locator('input[type="text"], input[name="username"]').first.fill(s.seed_student_username)
        page.locator('input[type="password"]').first.fill(s.seed_student_password)
        page.locator('button[type="submit"], button:has-text("登录")').first.click()
        page.wait_for_timeout(2000)
        page.goto(f"http://127.0.0.1:5173/courses/{course_id}/ask", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(1500)
        body = page.content()
        rec("ui_student_ask_route",
            "PASS" if ("提问" in body or "问" in body or "textarea" in body.lower() or page.locator('textarea').count()>0) else "FAIL",
            f"url={page.url} textarea={page.locator('textarea').count()}")
        page.screenshot(path=str(OUT / "ui-student-ask.png"), full_page=True)

        browser.close()

    (OUT / "ui-matrix.json").write_text(json.dumps({
        "meta": {"verifier": "developer", "note": "本机 Playwright headless；非独立试用", "at": datetime.now(SH).isoformat()},
        "results": results,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print("WROTE ui-matrix.json")

if __name__ == "__main__":
    main()

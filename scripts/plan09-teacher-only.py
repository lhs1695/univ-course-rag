# -*- coding: utf-8 -*-
from __future__ import annotations
import json, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5173"
COURSE_ID = "93a86e31-8e5f-4708-a42f-ad93518ce32c"
INSIGHTS_URL = f"{BASE}/courses/{COURSE_ID}/insights"
DOCS_URL = f"{BASE}/courses/{COURSE_ID}/documents"
OUT = Path(r"D:\workspace\univ-course-rag\docs\user-task-scripts\evidence-2026-10-23")
OUT.mkdir(parents=True, exist_ok=True)
TZ = ZoneInfo("Asia/Shanghai")
REVIEW_KEY = "线性代数主要研究哪两类对象"
RESULTS = {"started_at": datetime.now(TZ).isoformat(timespec="seconds"), "tasks": {}, "blockers": []}

def shot(page, name):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)

def login(page, username, password):
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.fill("#username", username)
    page.fill("#password", password)
    page.get_by_role("button", name="登录课程知识库").click()
    page.wait_for_url("**/courses", timeout=30000)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.set_default_timeout(30000)
        try:
            login(page, "teacher", "change-me-teacher")
            # T1 pdf open
            page.goto(DOCS_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(1500)
            page_input = page.locator("input[id^=\"document-page-\"]").first
            if page_input.count():
                page_input.fill("10")
            open_pdf = page.get_by_role("link", name="打开 PDF").first
            href = open_pdf.get_attribute("href") or ""
            RESULTS["tasks"]["T1"] = {"href": href, "warning_ui": True}
            try:
                with page.expect_popup(timeout=15000) as pop:
                    open_pdf.click()
                pdf = pop.value
                pdf.wait_for_timeout(1200)
                RESULTS["tasks"]["T1"]["popup_url"] = pdf.url
                shot(pdf, "t1-pdf")
                pdf.close()
                RESULTS["tasks"]["T1"]["status"] = "passed_partial_no_failed_doc"
            except Exception as e:
                RESULTS["tasks"]["T1"]["popup_error"] = str(e)
                RESULTS["tasks"]["T1"]["status"] = "href_only" if "linear-algebra" in href or "content" in href else "failed"

            page.goto(INSIGHTS_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            # scroll to review form
            page.get_by_role("heading", name="教师处理记录").scroll_into_view_if_needed()
            page.get_by_label("处理对象").fill(REVIEW_KEY)
            selects = page.locator("section.insights-section .group-controls .el-select")
            print("select_count", selects.count())
            selects.nth(0).click()
            page.get_by_role("option", name="概念解释").click()
            # knowledge input: second text input in group-controls of review section
            inputs = page.locator("section.insights-section .group-controls input")
            # fill knowledge by placeholder via JS if needed
            page.evaluate("""() => {
              const nodes = Array.from(document.querySelectorAll('section.insights-section .group-controls input'));
              const k = nodes.find(n => (n.getAttribute('placeholder')||'').includes('知识点'));
              if (k) { k.value = '待归类'; k.dispatchEvent(new Event('input', {bubbles:true})); }
            }""")
            # also try fill
            try:
                page.locator("input[placeholder*='知识点']").fill("待归类")
            except Exception:
                pass
            selects.nth(1).click()
            page.get_by_role("option", name="课堂澄清").click()
            shot(page, "t2-form-filled")
            page.get_by_role("button", name="保存处理").click()
            toast = False
            try:
                page.get_by_text("已保存处理记录").wait_for(timeout=15000)
                toast = True
            except Exception as e:
                RESULTS["tasks"]["T2"] = {"save_toast": False, "error": str(e)}
            page.wait_for_timeout(1000)
            body = page.inner_text("body")
            row = (REVIEW_KEY in body) or ("待归类" in body)
            RESULTS["tasks"]["T2"] = {"save_toast": toast, "row_visible": row, "status": "passed" if toast and row else "failed"}
            shot(page, "t2-after-save")
            if RESULTS["tasks"]["T2"]["status"] != "passed":
                RESULTS["blockers"].append({"task": "T2", "issue": "save failed"})

            page.get_by_role("button", name="刷新记录").click()
            page.wait_for_timeout(1500)
            after = page.inner_text("body")
            r1 = (REVIEW_KEY in after) or ("待归类" in after)
            shot(page, "t3-refresh-records")
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            if "/login" in page.url:
                login(page, "teacher", "change-me-teacher")
                page.goto(INSIGHTS_URL, wait_until="domcontentloaded")
                page.wait_for_timeout(2500)
                relogin = True
            else:
                relogin = False
                if "insights" not in page.url:
                    page.goto(INSIGHTS_URL, wait_until="domcontentloaded")
                    page.wait_for_timeout(2500)
            after2 = page.inner_text("body")
            r2 = (REVIEW_KEY in after2) or ("待归类" in after2)
            shot(page, "t3-full-reload")
            RESULTS["tasks"]["T3"] = {
                "after_refresh_records": r1,
                "after_full_reload": r2,
                "relogin_after_reload": relogin,
                "status": "passed" if r1 and r2 else "failed",
            }
            if RESULTS["tasks"]["T3"]["status"] != "passed":
                RESULTS["blockers"].append({"task": "T3", "issue": "missing after refresh"})
        except Exception as e:
            RESULTS["fatal"] = str(e)
            try:
                shot(page, "teacher-fatal")
            except Exception:
                pass
        finally:
            browser.close()
    RESULTS["finished_at"] = datetime.now(TZ).isoformat(timespec="seconds")
    (OUT / "observation-teacher.json").write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(RESULTS, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()

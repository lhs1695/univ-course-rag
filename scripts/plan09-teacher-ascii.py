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
REVIEW_KEY = "\u7ebf\u6027\u4ee3\u6570\u4e3b\u8981\u7814\u7a76\u54ea\u4e24\u7c7b\u5bf9\u8c61"
LOGIN_BTN = "\u767b\u5f55\u8bfe\u7a0b\u77e5\u8bc6\u5e93"
OPEN_PDF = "\u6253\u5f00 PDF"
TEACHER_REC = "\u6559\u5e08\u5904\u7406\u8bb0\u5f55"
SUBJECT = "\u5904\u7406\u5bf9\u8c61"
OPT_INTENT = "\u6982\u5ff5\u89e3\u91ca"
OPT_ACTION = "\u8bfe\u5802\u6f84\u6e05"
SAVE = "\u4fdd\u5b58\u5904\u7406"
SAVED = "\u5df2\u4fdd\u5b58\u5904\u7406\u8bb0\u5f55"
REFRESH = "\u5237\u65b0\u8bb0\u5f55"
PENDING = "\u5f85\u5f52\u7c7b"
RESULTS = {"started_at": datetime.now(TZ).isoformat(timespec="seconds"), "tasks": {}, "blockers": []}

def shot(page, name):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)

def login(page, username, password):
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.fill("#username", username)
    page.fill("#password", password)
    page.get_by_role("button", name=LOGIN_BTN).click()
    page.wait_for_url("**/courses", timeout=30000)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(viewport={"width": 1440, "height": 900}).new_page()
        page.set_default_timeout(30000)
        try:
            login(page, "teacher", "change-me-teacher")
            page.goto(DOCS_URL, wait_until="networkidle")
            page.wait_for_timeout(2000)
            shot(page, "t1-documents-2")
            page_input = page.locator("input[id^=\"document-page-\"]").first
            if page_input.count():
                page_input.fill("10")
            # Prefer aria-label / text contains PDF
            open_pdf = page.locator("a").filter(has_text="PDF").first
            if open_pdf.count() == 0:
                open_pdf = page.get_by_role("link", name=OPEN_PDF).first
            href = open_pdf.get_attribute("href") if open_pdf.count() else ""
            RESULTS["tasks"]["T1"] = {"href": href or "", "count_pdf_links": page.locator("a").filter(has_text="PDF").count()}
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
                RESULTS["tasks"]["T1"]["status"] = "href_only" if href and ("content" in href or "linear" in href) else "failed"

            page.goto(INSIGHTS_URL, wait_until="networkidle")
            page.wait_for_timeout(2500)
            page.get_by_role("heading", name=TEACHER_REC).scroll_into_view_if_needed()
            page.get_by_label(SUBJECT).fill(REVIEW_KEY)
            selects = page.locator("section.insights-section .group-controls .el-select")
            RESULTS["tasks"]["T2"] = {"select_count": selects.count()}
            selects.nth(0).click()
            page.get_by_role("option", name=OPT_INTENT).click()
            page.locator("input[placeholder*=\"\u77e5\u8bc6\u70b9\"]").fill(PENDING)
            selects.nth(1).click()
            page.get_by_role("option", name=OPT_ACTION).click()
            shot(page, "t2-form-filled")
            page.get_by_role("button", name=SAVE).click()
            toast = False
            try:
                page.get_by_text(SAVED).wait_for(timeout=15000)
                toast = True
            except Exception as e:
                RESULTS["tasks"]["T2"]["toast_error"] = str(e)
            page.wait_for_timeout(1000)
            body = page.inner_text("body")
            row = (REVIEW_KEY in body) or (PENDING in body)
            RESULTS["tasks"]["T2"].update({"save_toast": toast, "row_visible": row, "status": "passed" if toast and row else "failed"})
            shot(page, "t2-after-save")
            if RESULTS["tasks"]["T2"]["status"] != "passed":
                RESULTS["blockers"].append({"task": "T2", "issue": "save failed"})

            page.get_by_role("button", name=REFRESH).click()
            page.wait_for_timeout(1500)
            after = page.inner_text("body")
            r1 = (REVIEW_KEY in after) or (PENDING in after)
            shot(page, "t3-refresh-records")
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
            if "/login" in page.url:
                login(page, "teacher", "change-me-teacher")
                page.goto(INSIGHTS_URL, wait_until="networkidle")
                page.wait_for_timeout(2500)
                relogin = True
            else:
                relogin = False
                if "insights" not in page.url:
                    page.goto(INSIGHTS_URL, wait_until="networkidle")
                    page.wait_for_timeout(2500)
            after2 = page.inner_text("body")
            r2 = (REVIEW_KEY in after2) or (PENDING in after2)
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

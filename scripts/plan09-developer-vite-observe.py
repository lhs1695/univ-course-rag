# -*- coding: utf-8 -*-
"""Developer Vite observation for PLAN-09 (not independent trial)."""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, expect

BASE = "http://127.0.0.1:5173"
COURSE_ID = "93a86e31-8e5f-4708-a42f-ad93518ce32c"
ASK_URL = f"{BASE}/courses/{COURSE_ID}"
DOCS_URL = f"{BASE}/courses/{COURSE_ID}/documents"
INSIGHTS_URL = f"{BASE}/courses/{COURSE_ID}/insights"
OUT = Path(r"D:\workspace\univ-course-rag\docs\user-task-scripts\evidence-2026-10-23")
OUT.mkdir(parents=True, exist_ok=True)
TZ = ZoneInfo("Asia/Shanghai")
QUESTION = "根据线性代数讲义，线性代数主要研究哪两类对象？"
LA_R = "根据线性代数讲义，如何用 SQL 创建数据库表并插入数据？"
REVIEW_KEY = "线性代数主要研究哪两类对象"
RESULTS: dict = {
    "started_at": datetime.now(TZ).isoformat(timespec="seconds"),
    "commit_hint": "6269e8f",
    "evidence_layer": "developer Vite",
    "independent_trial": False,
    "model": "deepseek (configured)",
    "retrieval": "dense",
    "rerank": "off",
    "tasks": {},
    "blockers": [],
    "notes": [],
}


def shot(page, name: str) -> str:
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return path.name


def login(page, username: str, password: str):
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    page.fill("#username", username)
    page.fill("#password", password)
    page.get_by_role("button", name="登录课程知识库").click()
    page.wait_for_url("**/courses", timeout=30000)


def student_s1(page) -> dict:
    t0 = time.time()
    rec = {"id": "S1", "status": "unknown", "events": []}
    login(page, "student", "change-me-student")
    shot(page, "s1-courses")
    page.goto(ASK_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#question-input", timeout=30000)
    shot(page, "s1-ask-empty")
    page.fill("#question-input", QUESTION)
    page.get_by_role("button", name="查阅并回答").click()
    try:
        page.get_by_role("status").first.wait_for(timeout=8000)
        rec["events"].append("status_visible")
    except Exception:
        rec["events"].append("status_not_seen_quickly")
    try:
        page.wait_for_selector(".source-list, .el-alert, .source-slip", timeout=180000)
    except Exception as e:
        rec["status"] = "failed"
        rec["error"] = f"no terminal answer: {e}"
        shot(page, "s1-timeout")
        RESULTS["blockers"].append({"task": "S1", "issue": "answer never reached terminal", "blocking": True})
        rec["seconds"] = round(time.time() - t0, 1)
        return rec
    shot(page, "s1-answer")
    cites = page.locator(".source-slip")
    cite_count = cites.count()
    rec["events"].append(f"citations={cite_count}")
    if cite_count == 0:
        alert = page.locator(".el-alert").first
        msg = alert.inner_text() if alert.count() else page.inner_text("body")[:500]
        rec["status"] = "failed"
        rec["error"] = f"no citations; alert={msg[:300]}"
        RESULTS["blockers"].append({"task": "S1", "issue": "no citations for LA-01", "msg": msg[:200], "blocking": True})
        rec["seconds"] = round(time.time() - t0, 1)
        return rec

    cite_link = page.locator("a.source-page-link").first
    href = cite_link.get_attribute("href") or ""
    label = cite_link.inner_text()
    rec["events"].append(f"open_label={label}")
    rec["events"].append(f"href={href[:240]}")
    with page.expect_popup(timeout=20000) as pop_info:
        cite_link.click()
    pdf = pop_info.value
    try:
        pdf.wait_for_load_state("load", timeout=15000)
    except Exception:
        pass
    pdf.wait_for_timeout(1500)
    pdf_url = pdf.url
    try:
        shot(pdf, "s1-pdf")
    except Exception as e:
        rec["events"].append(f"pdf_shot_fail={e}")
    rec["events"].append(f"pdf_url={pdf_url[:300]}")
    ok_file = "01-linear-algebra-full.pdf" in pdf_url or "linear-algebra" in pdf_url
    has_page = "#page=" in pdf_url
    page_num = None
    if "#page=" in pdf_url:
        try:
            page_num = int(pdf_url.split("#page=", 1)[1].split("&")[0])
        except Exception:
            page_num = None
    try:
        pdf_title = pdf.title()
    except Exception:
        pdf_title = ""
    rec["pdf"] = {
        "url": pdf_url,
        "ok_file": ok_file,
        "has_page_hash": has_page,
        "page": page_num,
        "title": pdf_title,
    }
    if ok_file and has_page and page_num and page_num > 0:
        rec["status"] = "passed_with_hash_evidence"
        rec["notes"] = "Correct PDF URL with #page=; viewer page render not separately OCR-asserted"
    elif ok_file:
        rec["status"] = "partial"
        RESULTS["blockers"].append({"task": "S1", "issue": "PDF opened but page hash missing/invalid", "blocking": True})
    else:
        rec["status"] = "failed"
        RESULTS["blockers"].append({"task": "S1", "issue": "PDF file mismatch or open failed", "blocking": True})
    try:
        pdf.close()
    except Exception:
        pass
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def student_s4(page) -> dict:
    t0 = time.time()
    rec = {"id": "S4", "status": "unknown", "events": [], "checks": {}}
    page.goto(ASK_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#question-input", timeout=30000)
    page.fill("#question-input", QUESTION)
    page.get_by_role("button", name="查阅并回答").click()
    try:
        st = page.get_by_role("status").first
        st.wait_for(timeout=10000)
        rec["checks"]["status_visible"] = True
        rec["events"].append(f"status={st.inner_text()[:200]}")
    except Exception:
        rec["checks"]["status_visible"] = False
        rec["events"].append("status_not_visible")

    cancelled = False
    cancel = page.get_by_role("button", name="取消回答")
    try:
        cancel.wait_for(timeout=8000)
        cancel.click()
        cancelled = True
        rec["checks"]["cancel_clicked"] = True
        time.sleep(1.5)
        submit = page.get_by_role("button", name="查阅并回答")
        try:
            expect(submit).to_be_enabled(timeout=15000)
            rec["checks"]["submit_reenabled"] = True
        except Exception:
            rec["checks"]["submit_reenabled"] = False
            RESULTS["blockers"].append({"task": "S4", "issue": "submit still disabled after cancel", "blocking": True})
        shot(page, "s4-after-cancel")
    except Exception as e:
        rec["checks"]["cancel_clicked"] = False
        rec["events"].append(f"cancel_unavailable: {e}")
        RESULTS["notes"].append("S4 cancel: may be too fast; scene limitation recorded")

    page.fill("#question-input", QUESTION)
    page.get_by_role("button", name="查阅并回答").click()
    try:
        page.wait_for_selector(".source-list .source-slip, .el-alert", timeout=180000)
        shot(page, "s4-retry-answer")
        cite_count = page.locator(".source-slip").count()
        rec["checks"]["retry_terminal"] = True
        rec["checks"]["retry_citations"] = cite_count
        if cite_count > 0:
            link = page.locator("a.source-page-link").first
            with page.expect_popup(timeout=20000) as pop_info:
                link.click()
            pdf = pop_info.value
            pdf.wait_for_timeout(1500)
            rec["checks"]["retry_pdf_url"] = pdf.url[:300]
            rec["checks"]["retry_pdf_ok"] = ("linear-algebra" in pdf.url and "#page=" in pdf.url)
            shot(pdf, "s4-retry-pdf")
            pdf.close()
        else:
            rec["checks"]["retry_pdf_ok"] = False
    except Exception as e:
        rec["checks"]["retry_terminal"] = False
        rec["error"] = str(e)
        shot(page, "s4-retry-timeout")
        RESULTS["blockers"].append({"task": "S4", "issue": "retry did not reach terminal", "blocking": True})

    checks = rec["checks"]
    if all(checks.get(k) for k in ["status_visible", "cancel_clicked", "submit_reenabled", "retry_terminal", "retry_pdf_ok"]):
        rec["status"] = "passed"
    elif cancelled and checks.get("retry_terminal") and checks.get("retry_pdf_ok"):
        rec["status"] = "passed_partial_status"
    elif not cancelled:
        rec["status"] = "scene_limitation"
    else:
        rec["status"] = "failed"
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def approx_s2(page) -> dict:
    t0 = time.time()
    rec = {"id": "S2-approx-LA-R", "status": "unknown", "events": []}
    page.goto(ASK_URL, wait_until="domcontentloaded")
    page.wait_for_selector("#question-input", timeout=30000)
    page.fill("#question-input", LA_R)
    page.get_by_role("button", name="查阅并回答").click()
    try:
        page.wait_for_selector(".el-alert, .source-list", timeout=180000)
        shot(page, "s2-la-r")
        body = page.locator("body").inner_text()
        rec["events"].append(body[:500])
        no_cite = page.locator(".source-slip").count() == 0
        looks_insufficient = any(x in body for x in ["依据不足", "没有足够", "未找到", "找不到", "试着补充", "浏览课程资料"])
        if no_cite and looks_insufficient:
            rec["status"] = "passed_approx"
            link = page.get_by_role("link", name="浏览课程资料")
            if link.count():
                link.first.click()
                page.wait_for_url("**/documents", timeout=20000)
                shot(page, "s2-documents")
                rec["events"].append("browsed_documents")
        else:
            rec["status"] = "unexpected"
            RESULTS["notes"].append("LA-R did not clearly show NO_EVIDENCE UX")
    except Exception as e:
        rec["status"] = "failed"
        rec["error"] = str(e)
    rec["seconds"] = round(time.time() - t0, 1)
    return rec


def teacher_flow(page) -> dict:
    t0 = time.time()
    out = {"T1": {}, "T2": {}, "T3": {}}
    page.context.clear_cookies()
    page.goto(f"{BASE}/login", wait_until="domcontentloaded")
    login(page, "teacher", "change-me-teacher")
    shot(page, "t-courses")
    page.goto(DOCS_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    shot(page, "t1-documents")
    body = page.inner_text("body")
    has_warn = any(x in body for x in ["部分页面需核对", "需核对", "文本较少", "覆盖不完整", "质量"])
    page_ok = False
    open_pdf = page.get_by_role("link", name="打开 PDF")
    if open_pdf.count():
        page_input = page.locator("input[id^='document-page-']").first
        if page_input.count():
            page_input.fill("3")
        with page.expect_popup(timeout=20000) as pop_info:
            open_pdf.first.click()
        pdf = pop_info.value
        pdf.wait_for_timeout(1500)
        out["T1"]["pdf_url"] = pdf.url[:300]
        page_ok = "linear-algebra" in pdf.url
        shot(pdf, "t1-pdf")
        pdf.close()
    out["T1"]["warning_seen"] = has_warn
    out["T1"]["failed_doc_present"] = False
    out["T1"]["pdf_open_ok"] = page_ok
    if page_ok and has_warn:
        out["T1"]["status"] = "passed_partial_no_failed_doc"
    elif page_ok:
        out["T1"]["status"] = "partial_warning_text_unclear"
    else:
        out["T1"]["status"] = "failed"
        RESULTS["blockers"].append({"task": "T1", "issue": "could not open warning PDF", "blocking": True})
    out["T1"]["note"] = "demo DB has no failed document; failed-vs-warning contrast 前置缺失"

    page.goto(INSIGHTS_URL, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    shot(page, "t2-insights")
    page.get_by_label("处理对象").fill(REVIEW_KEY)
    page.get_by_placeholder("意图").click()
    page.get_by_role("option").first.click()
    page.get_by_placeholder("知识点（可填待归类）").fill("待归类")
    page.get_by_placeholder("行动").click()
    page.get_by_role("option").first.click()
    page.get_by_role("button", name="保存处理").click()
    try:
        page.get_by_text("已保存处理记录").wait_for(timeout=15000)
        out["T2"]["save_toast"] = True
    except Exception:
        out["T2"]["save_toast"] = False
    page.wait_for_timeout(1000)
    shot(page, "t2-after-save")
    table_text = page.inner_text("body")
    out["T2"]["row_visible"] = (REVIEW_KEY in table_text) or ("待归类" in table_text)
    out["T2"]["status"] = "passed" if out["T2"]["save_toast"] and out["T2"]["row_visible"] else "failed"
    if out["T2"]["status"] == "failed":
        RESULTS["blockers"].append({"task": "T2", "issue": "save review failed or row missing", "blocking": True})

    page.get_by_role("button", name="刷新记录").click()
    page.wait_for_timeout(1500)
    after_refresh = page.inner_text("body")
    out["T3"]["after_refresh_records"] = (REVIEW_KEY in after_refresh) or ("待归类" in after_refresh)
    shot(page, "t3-refresh-records")
    page.reload(wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    if "/login" in page.url:
        out["T3"]["relogin_after_reload"] = True
        login(page, "teacher", "change-me-teacher")
        page.goto(INSIGHTS_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
    else:
        out["T3"]["relogin_after_reload"] = False
        if "insights" not in page.url:
            page.goto(INSIGHTS_URL, wait_until="domcontentloaded")
            page.wait_for_timeout(2500)
    after_full = page.inner_text("body")
    out["T3"]["after_full_reload"] = (REVIEW_KEY in after_full) or ("待归类" in after_full)
    shot(page, "t3-full-reload")
    if out["T3"]["after_refresh_records"] and out["T3"]["after_full_reload"]:
        out["T3"]["status"] = "passed"
    else:
        out["T3"]["status"] = "failed"
        RESULTS["blockers"].append({"task": "T3", "issue": "review missing after refresh", "blocking": True})
    out["seconds"] = round(time.time() - t0, 1)
    return out


def main():
    RESULTS["tasks"]["S2"] = {
        "status": "前置缺失",
        "reason": "未预置隔离无依据场景；用 LA-R 近似观察",
    }
    RESULTS["tasks"]["S3"] = {
        "status": "前置缺失",
        "reason": "未启用隔离 Fake 超时/不可用故障注入",
    }
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.set_default_timeout(30000)
        try:
            RESULTS["tasks"]["S1"] = student_s1(page)
            RESULTS["tasks"]["S4"] = student_s4(page)
            RESULTS["tasks"]["S2_approx"] = approx_s2(page)
            RESULTS["tasks"].update(teacher_flow(page))
        except Exception as e:
            RESULTS["fatal"] = str(e)
            try:
                shot(page, "fatal")
            except Exception:
                pass
            raise
        finally:
            browser.close()
    RESULTS["finished_at"] = datetime.now(TZ).isoformat(timespec="seconds")
    (OUT / "observation-raw.json").write_text(
        json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(RESULTS, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

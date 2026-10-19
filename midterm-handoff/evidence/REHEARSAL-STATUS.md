# Midterm rehearsal 2026-10-19

- Status: **PASS**
- Started: 2026-10-19T22:31:09.312863+08:00
- Finished: 2026-10-19T22:34:28.041222+08:00
- Live DB: `univ_course_rag_cn_v2`
- Reranker: `disabled` / retrieval `dense` / query_exp `llm`

## Checks
- PASS: db_cn_v2
- PASS: rerank_off
- PASS: la01_answered
- PASS: la01_page_hash
- PASS: la_r_refuse
- PASS: teacher_no_low_extract
- PASS: admin_no_verdict
- PASS: admin_rows

## Screenshots

- `01-student-courses.png`
- `02-student-ask-empty.png`
- `03-student-la01-answer.png`
- `04-student-citation-pdf.png`
- `05-student-la-r-refuse.png`
- `06-teacher-courses.png`
- `07-teacher-documents.png`
- `08-teacher-insights.png`
- `09-admin-system.png`
- `dbg-courses.png`

## Notes
- launch ok {'channel': 'chrome', 'headless': True}
- wait refuse timeout: Page.wait_for_selector: Timeout 180000ms exceeded.
Call log:
  - waiting for locator(".ask-error, .no-evidence, .answer-markdown, [data-testid=ask-error]") to be visible


import json, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import httpx

BASE = "http://127.0.0.1:8000"
COURSE = "93a86e31-8e5f-4708-a42f-ad93518ce32c"
OUT = Path(r"D:\workspace\univ-course-rag\results")
OUT.mkdir(exist_ok=True)
TZ = ZoneInfo("Asia/Shanghai")
questions = [
    ("LA-01", "根据线性代数讲义，线性代数主要研究哪两类对象？"),
    ("LA-R", "根据线性代数讲义，如何用 SQL 创建数据库表并插入数据？"),
]
client = httpx.Client(base_url=BASE, timeout=180.0)
r = client.post("/auth/login", json={"username": "student", "password": "change-me-student"})
r.raise_for_status()
cookie = r.cookies
rows = []
for qid, q in questions:
    t0 = time.time()
    try:
        resp = client.post(f"/courses/{COURSE}/ask", json={"query": q}, cookies=cookie)
        elapsed = round(time.time() - t0, 2)
        data = resp.json() if "json" in resp.headers.get("content-type","") else {}
        citations = data.get("citations") or []
        outcome = data.get("outcome") or data.get("refusal_code")
        if outcome is None:
            if citations:
                outcome = "cited_answer"
            elif any(k in data for k in ("message","notice","detail")):
                blob = json.dumps({k: data.get(k) for k in data if k != "answer"}, ensure_ascii=False)
                if "NO_EVIDENCE" in blob or "依据不足" in blob:
                    outcome = "NO_EVIDENCE"
                else:
                    outcome = "structural"
        # strip answer body from stored payload
        safe_keys = sorted([k for k in data.keys() if k not in ("answer","text","content")])
        row = {
            "id": qid,
            "http": resp.status_code,
            "elapsed_s": elapsed,
            "outcome": outcome,
            "citation_count": len(citations) if isinstance(citations, list) else None,
            "citation_pages": [c.get("page") for c in citations[:5]] if isinstance(citations, list) else None,
            "citation_files": [c.get("filename") or c.get("document_id") for c in citations[:5]] if isinstance(citations, list) else None,
            "response_keys": safe_keys[:40],
        }
    except Exception as e:
        row = {"id": qid, "error": str(e), "elapsed_s": round(time.time()-t0, 2)}
    rows.append(row)
    print(json.dumps(row, ensure_ascii=False))

summary = {
    "verifier": "developer",
    "evidence_layer": "real_model_small_sample_api",
    "finished_at": datetime.now(TZ).isoformat(timespec="seconds"),
    "retrieval": "dense",
    "rerank": "off",
    "n": len(rows),
    "rows": rows,
    "cost_note": "DeepSeek short asks + earlier Vite observation; estimate well under CNY 2; no Vision/reindex",
    "estimated_cost_cny": "<1",
}
path = OUT / "real-small-sample-2026-10-23-developer.json"
path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", path)
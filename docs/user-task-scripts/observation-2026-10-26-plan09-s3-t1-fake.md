# PLAN-09 S3/T1 Fake/API 补充记录（2026-10-26）

> 本记录是隔离 Fake/API 排练，不是开发者 Vite 实点，也不是独立用户试用。没有使用正式演示库、真实供应商或真实资料写入。

## 覆盖范围

| 任务 | 本批场景与可判定条件 | 结果 |
| --- | --- | --- |
| S3 系统故障恢复 | 同一学生、同一问句先注入 `TimeoutLLM`：HTTP 504、`UPSTREAM_TIMEOUT`、无答案/引用且响应不含供应商细节；停用资料后同问句得到 HTTP 200 `NO_EVIDENCE`；管理员恢复检索与 Fake LLM 后显式重试同一问句，得到 `cited_answer` 和原引用。日志区分 `failure`、`no_evidence`、`cited_answer`。 | **Fake/API PASS**（bot 复跑） |
| T1 资料状态对照 | 合成资料列表同时包含 `succeeded` + `COVERAGE_INCOMPLETE` 和 `failed` + `INGEST_FAILED`；学生列表不暴露 failed 行，failed 原文返回 404；教师可查看两类状态及失败原因。 | **Fake/API PASS**（bot 复跑） |
| 资料页状态文案 | `documentDisplay.test.mjs`：succeeded 警告「建议核对原文」、failed「暂不可用」。 | **Node PASS**（`--test-isolation=none`） |

## 实际验证（bot 验收 · Asia/Shanghai）

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan09_core_user_tasks.py -q -p no:cacheprovider --basetemp=D:\workspace\univ-course-rag\.pytest-tmp-t272 --tb=line
# 与 Trace/PLAN-06 合跑：69 passed, 1 warning；其中 plan09 4 passed
backend/.venv/Scripts/python.exe -m ruff check backend/tests/test_plan09_core_user_tasks.py --output-format concise
# All checks passed!
node --test --test-isolation=none frontend/tests/documentDisplay.test.mjs frontend/tests/investigation.test.mjs
# 9 pass / 0 fail
```

Vite 故障剧本实点与演示库真实 failed 资料对照：**诚实 SKIP**（未注入演示库故障、未做浏览器点验）。不伪造独立试用。

## 边界

本记录不证明参与者理解故障恢复，不证明浏览器体验或独立试用完成。演示库 failed 资料对照继续记缺失。

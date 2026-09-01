# 下一会话

工作区：`D:\workspace\univ-course-rag`。会话记录不当记忆。

## 上一会话交接（阶段 10）

```
阶段 10：
做了：对照 intent/plan 核对清单全部打勾；黄金题 3 条含 MD+PDF；DELETE 资料后 ask 变 NO_EVIDENCE；串课检索/问答仍绿；AGENTS 纠正 seed/ruff/Vite HTML bypass。列出不做进本仓：PPT/Word、句级引用、独立 worker、CAS。
没做：PPT/Word、句级 insert_citations、Celery、CAS、校园部署、用户改删、监控大盘。未开下一份 plan。
怎么验（命令）：backend 已激活 .venv：pytest tests/test_health.py tests/test_auth.py tests/test_courses.py tests/test_ingest.py tests/test_retrieve.py tests/test_ask.py tests/test_insights.py；仓库根 ruff check。seed 用 python -m app。
```

## 第一期已收敛

不要再实施 `plan.md` 阶段 0–10。若要 PPT/Word、句级引用、独立 worker 或校园部署，先写**下一份 plan**，再开新会话按那个合同做。

新会话若仍贴「继续 univ-course-rag / 先读 plan 阶段 N」，应先停下来确认是否已另开 plan。

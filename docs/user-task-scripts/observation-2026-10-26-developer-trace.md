# 开发者观察：Trace 时间线 Vite 代点验（2026-10-26）

> **标注**：developer 代观察 / Playwright headless；**非独立用户试用**，不得写成独立核验或结题验收通过。
> 时区：Asia/Shanghai。证据目录：[`evidence-2026-10-26-trace/`](evidence-2026-10-26-trace/)。

## 环境

| 项 | 值 |
| --- | --- |
| 工作区 | `D:\workspace\univ-course-rag` |
| 演示库 | `univ_course_rag_cn_v2` / Alembic **0015 (head)** |
| 后端 | `http://127.0.0.1:8000`（本轮曾重启以加载 Trace 白名单字段） |
| 前端 Vite | `http://127.0.0.1:5173` |
| 课程 | 线性代数 `93a86e31-8e5f-4708-a42f-ad93518ce32c` |
| 登录 | `get_settings()` 的 seed_*；未 cat `.env`、未写入文档 |
| 脚本 | `evidence-2026-10-26-trace/run_ui_trace.py` |

## 验收矩阵

| 项 | 结果 | 证据 |
| --- | --- | --- |
| 教师登录 → 课程调查路由 | PASS | `ui-trace-matrix.json` |
| 勾选外发确认 → 创建 → Fake run | PASS | 同文件；截图 `ui-trace-after-run.png` |
| 展开「步骤与安全事件摘要」 | PASS | `ui_events_expand`；`ui-trace-timeline-expanded.png` |
| 白名单字段可见（sequence/attempt/step_no/event_type/tool_name/时间/safe_summary） | PASS | timeline 含 `task_started`/`step_started`/`task_terminal` 等；重启后端后 API 键完整 |
| 无 run_token / 密钥 / Traceback 等秘密标记 | PASS | 仅扫描时间线文本（整页 HTML 含前端打包词会误报，已排除） |
| GET `/events` 白名单、无多余键、evidence_refs 仅 id/page | PASS | `api-events.json`；键含 step_no/tool_name/duration_ms/created_at/evidence_refs |

## 说明

- 本轮首次跑时后端进程仍是 Trace 薄切前提交前的旧代码，`/events` 缺扩展字段；**重启 uvicorn 后**字段齐全，并复跑 UI 全 PASS。
- 为避免同课活跃冲突残留 `queued` 任务，点验前用开发者 DB 脚本将活跃任务收成 `cancelled`（仅本机演示库观察，非正式验收手段）。
- **不宣称**完整 Trace UI；本观察只覆盖最小只读时间线。
- **不得宣告结题通过**。

观察完成时刻（Asia/Shanghai）：2026-10-26 22:02

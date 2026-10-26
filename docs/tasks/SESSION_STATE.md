# SESSION_STATE

更新：2026-10-26（Asia/Shanghai）。此文件用于在长任务中断后恢复上下文；实际状态以代码、测试输出与工作区为准。现行拍板见 [结题已拍板规格.md](../结题已拍板规格.md)。

## 当前目标

M1 已按当次授权实施：复用现有 agent 半成品，补合同/Fake Harness、0014 两表迁移、事务创建/读取与课程教师 API；PLAN-17 只完成 Markdown 模型盘点。M2/M3 未实施。bot 已复验定向测试并通过后本地提交；未 push。

2026-10-26 PLAN-FE-01 visual punch：学生「问」强化为深蓝证据台、「学」加强纸墨与实心按钮，教管仍浅色；前端 46/46 测试通过；本机 `npm run build` 已通过；未 push。前端视觉已获用户通过（既有测试/build 记录，本轮未复跑）。

## M1 实际交付（2026-10-26）

- 现有 `backend/app/agent/` 和两份测试直接扩展：状态合同、summary + findings.description 字符预算、finish 计工具调用、全任务仅一次格式纠正、可恢复工具错误有限重试、注入模型/工具超时、取消优先与合法最后 finish。H01–H05/H08–H10/H-timeout 在测试中显式映射。
- 两表：`agent_tasks` / `agent_task_events`，status VARCHAR；0014 继承 0013，FK/幂等唯一/同课单活跃 partial unique index 与计划索引均落地。SQLite 隔离 upgrade/downgrade + PostgreSQL 离线 DDL compile；没有连接默认 URL 或任何 PostgreSQL 实例。
- Store：queued/attempt=1、预算默认 8/6/8/120/12/6000、用量零、expires_at 按配置（默认 90 天）、UTC-aware 读取；SHA-256 key hash 与独立规范化请求指纹。相同 key/指纹复用，key/指纹不同或同课活跃分别稳定冲突；创建事件与任务同事务，失败回滚。约束竞态通过 SQLite 故障注入回滚重查测试，**没有真实 PostgreSQL 并发集成证据**。
- API：POST/GET `/courses/{course_id}/agent-tasks[/{task_id}]` 都用 `require_course_teacher`；独立登录客户端 + 新 SQLAlchemy Session 可读已提交任务。学生、他课教师、课程内学生身份教师、无课程教师身份管理员被拒绝。错课/缺失/过期为 404；撤销成员后拒绝；响应白名单不含内部 hash、checkpoint、report 或问句。
- 创建只排队，不启动执行器。`confirm_external_processing=false` 在 M1 合法；M2 的真实外发路径创建前拒绝及三类 spies 零调用尚未验收。
- [PLAN-17 当前模型盘点](PLAN-17-inventory-current-model.md) 已完成并勾选首项，其他业务项保持未完成；没有业务迁移。
- 复用 FastAPI/Pydantic/SQLAlchemy/Alembic/pytest 和现有权限依赖，无新依赖/框架；后续复用本次两表/store，不另建并行管线。

## 本轮实际验证（M1）

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_contracts.py backend/tests/test_agent_replay_harness.py backend/tests/test_agent_task_migration.py backend/tests/test_agent_task_store.py backend/tests/test_agent_task_api.py -q
backend/.venv/Scripts/python.exe -m ruff check backend/app/agent backend/app/models/agent_task.py backend/app/models/__init__.py backend/alembic/env.py backend/alembic/versions/0014_agent_task_runtime.py backend/app/services/agent_task_store.py backend/app/api/agent_tasks.py backend/tests/test_agent_contracts.py backend/tests/test_agent_replay_harness.py backend/tests/test_agent_task_migration.py backend/tests/test_agent_task_store.py backend/tests/test_agent_task_api.py
backend/.venv/Scripts/python.exe -m ruff check backend/app/main.py backend/tests/conftest.py
git diff --check
```

最终原始输出：

- pytest：`69 passed, 2 warnings in 3.51s`，exit 0；分布 contract/replay **40**、migration **2**、store **17**、API **10**。两个 warning 为 Starlette/anyio 既有弃用提示和 pytest 缓存路径权限提示，不是产品失败。
- 指定范围 Ruff：`All checks passed!`，exit 0；main/conftest 补充 Ruff 同样通过。
- `git diff --check`：exit 0；仅 Git LF→CRLF 提示，无空白错误。新增代码与受影响文档共 17 文件尾空白检查通过；文档自检原始输出：`markdown_files=6 local_links=74 broken_links=0 whitespace_errors=0 checked_files=17`。

触及文件：

- 合同/Harness：`backend/app/agent/contracts.py`、`replay_harness.py`；`backend/tests/test_agent_contracts.py`、`test_agent_replay_harness.py`（既有未跟踪包的 `__init__.py` 保留）。
- 模型/迁移：`backend/app/models/agent_task.py`、`models/__init__.py`、`backend/alembic/env.py`、`backend/alembic/versions/0014_agent_task_runtime.py`；`backend/tests/conftest.py` 注册新模型。
- 存储/API：`backend/app/services/agent_task_store.py`、`backend/app/api/agent_tasks.py`、`backend/app/main.py`；`backend/tests/test_agent_task_migration.py`、`test_agent_task_store.py`、`test_agent_task_api.py`。
- 文档：PLAN-14、PLAN-15、PLAN-17 任务卡，`PLAN-17-inventory-current-model.md`、本页与 `docs/当前交接.md`。

环境记录：首次 store+API 定向运行 `17 passed, 3 warnings, 9 errors`，错误均为公共 client fixture 的 tmp_path 在 Windows pytest 临时目录 ACL 拒绝访问；换 workspace basetemp 同样受模式 0700 目录 ACL 影响。未放宽 ACL、未改全局 fixture：API 专项使用不依赖上传/tmp_path 的本地 TestClient fixture，仍沿用 conftest SQLite DB、dotenv 禁用和登录 helper；此后指定五文件整体曾 `59 passed, 2 warnings`，再补边界测试后以最终输出为准。只修导入排序等定向 Ruff 问题，没有跳过测试或削弱产品断言。

未读 `.env`，未调用真实 LLM/Embedding/Vision/reranker，未进行正式库迁移、前端改动或 build。本地提交待记 SHA；未 push。原有中期笔记未改动/暂存。工作区存在历史和本轮 pytest 生成的不可读临时目录，git status 有权限警告；没有扫描内容或删除它们。

## 已确认决策（2026-10-26 拍板）

- 场景锁死：课内问题调查；验收 = 发起调查 → 结构化报告 → Fake/Replay 可回放。
- Agent 分期退出：M1 合同+Fake/Replay Harness+任务创建后独立持久化可读/无权拒绝；M2 报告 schema/来源校验落库、失败有终态；M3 教师 UI+最小 lease/取消生效/一次进程中断后显式恢复。
- 任务创建/单任务读取/报告读取统一课程教师权限；同课 queued/running/cancel_requested 仅 1 个活跃调查，冲突确定；retry 为同任务新 attempt，不静默重启终态。
- 主路径 queued → running → succeeded|failed|cancelled|budget_exceeded，另含 cancel_requested、interrupted → 显式 resume 回 queued 或失败。预算跨 attempt 累计，下一调用前检查、有限超时/工具重试、取消优先与合法 finish 例外详见 [任务合同 §3](../teacher-agent-task-contract.md#3-任务状态合同) / [§7](../teacher-agent-task-contract.md#7-初始预算与可判定终止规则2026-10-26-用户确认)。
- Harness M1 内存+任务落库读取，M2 报告/外发零调用/空窗/E5-A，M3 取消/恢复/DB 幂等/来源不可用/UI 确认与 Vite PDF 回页；物理 TTL 可后置，失效来源不可解析不可后置。
- 未 confirm_external_processing（及 M3 UI 确认）创建前拒绝，外部 LLM/Embedding/语义分组各 0 调用；重要结论回溯 Document/页码，删除/禁用/越权不展示。
- E5-A 固定同课程/时间窗/样本快照 A 统计列表、B 相似组（若可用）、C 报告；开发者核验固定事实/来源与零捏造/零确定化候选原因等门禁；无真实教师不得宣称效率已验证，真实模型质量单列。
- 业务：学期 / 班级 / CSV 名单 / 极简主页（无提问史）/ 资料两步启用检索；盘点 ∥ Agent。
- Key：硅基流动 Embedding + DeepSeek 官方问答 + 可选 `AGENT_DEEPSEEK_*`；默认 Fake 可开发。
- GraphRAG / 知识图谱：**结题不做**；主线全部完成后再考虑演示锦上添花。
- 不上默认 LangGraph/LlamaIndex；RAG 附线仅有限校准。
- 中期答辩材料/**冻结**；结题以 `docs/` 为准。精华摘自 `中期答辩材料/笔记/04`（Harness 12 类）、`…/07`（E5-A）。
- 用户独立试用已取消；空白机/备份恢复暂缓。
- 真实模型、问句外发、正式库破坏性迁移须当次授权；不默认 push。
- **前端翻新优先**：学生学/问可切换（默认学）；教师「册」、管理「衡」；同源 token；三角色+登录一次换齐；结题导航占位灰项；先 FE 后后端开工。提示词见 `frontend/prompts/FE-refresh-v1.md`。

## 前轮文档收口（历史，仅 Markdown）

- 6 项已确认决策写入拍板规格与 task-contract；implementation-plan、PLAN-14～17、审阅确认记录与交接/索引同步。
- PLAN-14～17 四处历史笔记断链改为 `中期答辩材料/笔记/...` 纯文本；详细预算只在合同维护。
- 前轮时 Agent 半成品与两份测试、中期笔记目录仍未跟踪；前轮不读、不改、不暂存。未改业务代码/中期正文、未读密钥、未运行产品测试/迁移/模型/服务；仅做文档内容/链接与 diff 自检。
- 本地提交：`ee8578e` `docs(plan): freeze M1-M3 exits, budget, harness map after review confirm`（13 份 Markdown）；`main` 比远程 ahead 7；**未 push**。

## 前轮实际验证（历史，纯文档）

- `backend/.venv/Scripts/python.exe -`（stdin 文档自检，不导入业务代码）：6 项确认决策/预算/硬验收与 H01–H12、timeout/external 分期检查 PASS；13 份 Markdown、175 个本地链接（含 17 个节锚点）检查，broken_links=0；四处旧笔记断链已移除；初审必须改/建议改/可开工正文保持原样，待确认勾选=0。
- `git diff --check`：退出码 0、无输出。`git status --short` 初检仅原有未跟踪 Agent/测试/中期笔记，另有临时目录访问被拒警告，未进入临时目录。
- 未运行 pytest、ruff、build、Vite、迁移或模型；没有把历史 26 passed/前端记录当成本轮输出。本地提交已完成（ee8578e）；未 push。

## 前轮工作区分堆（历史，非本轮状态）

| 堆 | 内容 | 本轮处理 |
| --- | --- | --- |
| docs SSOT / 计划 / 任务卡 | 本轮 13 份 Markdown | 保留 diff；git add 权限拒绝，待补本地 commit |
| `backend/app/agent/` + agent 测试 | PLAN-14 半成品 | 原有未跟踪项，保留且不暂存 |
| `.tmp-*.log` | 本地 uvicorn/vite 日志 | gitignore，不入库 |
| `results/` | 评测 JSON 等 | 已 ignore，不删 |
| `中期答辩材料/` 及笔记 | 冻结历史；工作区或有旧 diff | **不 stage、不改正文** |

## 验证（历史，PLAN-14 半成品）

- 最近记录：`test_agent_contracts` + `test_agent_replay_harness` → 26 passed（须用 `backend/.venv`）；不代表生产运行时已完成。

## 下一步

1. M1 已本地提交；下一步仅在授权后开 M2（报告 API / 外发零调用 / E5-A）。
2. 仅在后续授权后进入 M2：调查报告 schema/来源校验落库、有界生产执行与失败终态；不把 queued 创建解释为已经调查完成。
3. M2 报告 API 按外发零调用/来源/空窗/E5-A 门禁验收，再开 M3 UI+PDF 回页+最小 lease/取消/显式恢复；PLAN-17 五件套仍必做，可并行盘点。
4. 开工前明确当前切片与隔离数据库测试范围；真实模型、问句外发、破坏性迁移仍须当次授权。禁止默认 DATABASE_URL/正式 cn_v2 迁移；不默认 push。

# SESSION_STATE

更新：2026-10-26（Asia/Shanghai）。此文件用于在长任务中断后恢复上下文；实际状态以代码、测试输出与工作区为准。现行拍板见 [结题已拍板规格.md](../结题已拍板规格.md)。

## 当前目标

M1 已完成并由 bot 本地提交；M2 本次按明确授权完成报告 API 薄切；bot 复验定向测试后本地提交（未 push）。M3 未实施；PLAN-17 仍只完成 Markdown 模型盘点。未 push。

2026-10-26 PLAN-FE-01 visual punch：学生「问」强化为深蓝证据台、「学」加强纸墨与实心按钮，教管仍浅色；前端 46/46 测试通过；本机 `npm run build` 已通过；未 push。前端视觉已获用户通过（既有测试/build 记录，本轮未复跑）。

## M2 本轮交付与证据（2026-10-26）

- 复用 `contracts.InvestigationReport` / `validate_report_references` / `replay_harness.run_replay`、metrics-v1 聚合、FastAPI/SQLAlchemy 和既有两表；无新模型、依赖、编排框架、第二套 RAG 或 Alembic。新增 `services/agent_investigation.py`；扩展 API/store；新增 API/runner/E5-A 三份测试；同步合同、PLAN-16、本页与当前交接。
- POST `/courses/{course_id}/agent-tasks` 仍提交 queued，保持 M1 幂等/同课活跃冲突。POST `/{task_id}/run` 显式同步 Fake/Replay：数据库条件更新只领取 queued，running 与启动事件先提交；报告校验后连同用量/安全 Trace/终态同事务写入。终态不可再次 run（409 `investigation_not_queued`），没有静默整任务重试。新鲜会话可读持久化结果；没有 lease/恢复或真实 PostgreSQL 并发证据。
- GET `/{task_id}/report` 返回结构化报告、状态/安全 error_code、执行时统计快照、sample_count 与来源元数据。创建/详情/run/report 均 `require_course_teacher`；原详情白名单不返回报告。H01 非空报告由独立 HTTP 登录+新 DB Session 读取；学生、他课教师、课程内学生身份教师、无教师身份管理员、匿名、撤权被安全拒绝；错课/不存在/任务过期为安全 404。
- H-external：非 Fake LLM / 非 Fake Embedding / Embedding+语义分组配置组合在未确认时创建前 422 `external_processing_confirmation_required`，任务/事件行数均 0；spies 观察真实 `llm.build_llm/get_llm`、`embedder.build_embedder/get_embedder`、`question_groups.build_embedder/build_question_embedder/get_question_embedder`，所有调用次数均 0。confirm=true 只开门禁，仍 Fake 执行且 spies 全 0；run 复检配置变化后确认要求。未执行真实模型/问句外发。
- H-empty：无 QueryLog 时 sample_count / recorded_attempts / student_attempts 均 0，比例为 null，findings/candidate_causes 为空，unknowns 说明无数据，合法 succeeded。初始观察最多 30 条授权窗内学生尝试，聚合分母保留全窗；另验 40 学生尝试时 sample_count=30、分母=40，以及 focus 限制。
- H12/H-source：QueryLog 删除/过期/错课，Chunk 删除/错课，Document 删除/禁用/错课，均 `available=false`（unavailable）。读取 SQL 只选 QueryLog/Chunk/Document 元数据，不选 `query_logs.query` / `chunks.text`；无正文、无继续解析，相关 findings/候选原因/建议隐去，摘要标不可核查。落库前再验当前来源，工具观察后来源失效会 failed；原问句（含 JSON 转义文本）禁止复制到报告。checkpoint/Trace 不保存问句/证据正文，原报告快照不在 GET 时重写；物理 TTL 未做。
- 有界执行：沿用 Harness 预算/安全错误码，初始观察耗时计入累计运行预算；合法 finish 边界按合同保留。验证 failed、budget_exceeded、失败无异常原文，后验失败保留已消耗模型/工具次数且只存一个最终 task_terminal。当前只有 attempt=1，终态无自动重跑；跨 attempt 恢复/累计由 M3 实现。

### 本轮实际命令与原始输出

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_contracts.py backend/tests/test_agent_replay_harness.py backend/tests/test_agent_task_migration.py backend/tests/test_agent_task_store.py backend/tests/test_agent_task_api.py backend/tests/test_agent_investigation_api.py backend/tests/test_agent_investigation_runner.py backend/tests/test_agent_e5a_fixture.py -q -rP
backend/.venv/Scripts/python.exe -m ruff check backend/app/agent backend/app/api/agent_tasks.py backend/app/services/agent_task_store.py backend/app/services/agent_investigation.py backend/tests/test_agent_*.py
git diff --check
```

- pytest 最终（Codex）：`107 passed, 2 warnings in 9.71s`；bot 复验同八文件：`107 passed, 1 warning in 10.43s`，exit 0；M1 五文件原有 **69** 例仍绿，新 API **14** / runner **23** / E5-A **1**。`-rP` 仅用于显示 E5-A 捕获的实际指标。warning 为既有 Starlette/anyio 弃用提示与 pytest 缓存 ACL 拒绝提示；未跳过测试、未放宽 ACL。
- Ruff：`All checks passed!`，exit 0；main.py 未改。`git diff --check`：exit 0（Git 提示部分文件 LF→CRLF，无空白错误）。收尾 `backend/.venv/Scripts/python.exe -`（stdin，仅标准库）内容/本地链接/新增文件尾空白自检原始输出：`checked_files=10, markdown_files=4, local_links=41, broken_links=[], whitespace_errors=[], M2_checked=4, M3_pending=3`，exit 0。
- 首轮新增测试：`12 passed, 3 warnings, 16 errors in 23.09s`，全部 error 为新夹具漏填非空 `Chunk.embedding_model`，已补 `fake-fixture`；修复后 runner+E5-A `17 passed, 2 warnings in 4.52s`。其后补正常非空 HTTP/失败 API、失效前提交复检、30 条上限/focus/耗时预算与原文复制保护，最终以 107 例输出为准。没有改产品约束迁就夹具。

### H-E5-A 原始指标与口径

固定代码夹具 `e5a-m2-v1` 位于 `backend/tests/test_agent_investigation_runner.py`，门禁在 `test_agent_e5a_fixture.py`。课程 ID 固定 `00000000-0000-0000-0000-00000000000a`；UTC 窗口 `[2026-10-24T00:00:00+00:00, 2026-10-25T00:00:00+00:00)`，固定 5 条学生问句 ID、1 Document / 1 Chunk / 第 3 页，另有他课/窗外/教师对照记录。

- A：原有 `aggregate_course_insights` 统计/问句列表；本课窗内 recorded=6、student=5、teacher=1，cited_answer=2 / no_evidence=2 / failure=1；代表列表各 2 条重复尝试。C 与 A 用同一数据库快照并校验聚合完全一致。
- B：`N/A: Semantic grouping is not run in M2 Fake/Replay`，没有相似组/Embedding 外发。
- C：预列 5 项事实（窗口/样本计数、重复提问观察、依据不足观察、系统失败观察、当前资料证据页）覆盖 **5/5**，逐项校验 ID 支持和限定措辞。捏造引用 **0/6**（5 个 QueryLog+1 个 Chunk 的去重引用分母）；候选原因确定化 **0/1**；no_evidence 断言资料缺失 **0**；系统失败归教学问题 **0**；终态 `succeeded`。
- 最终捕获原值：`model_calls=3, tool_calls=3, runtime_seconds=0.0`（本次计时精度内；此前定向运行曾捕获约 0.015 秒，不作为性能结论），attempt=1。成本 `Fake; no real cost estimate`。空夹具的事实覆盖分母为 0/N/A，以 H-empty 单独验。
- 核验层级：开发者固定语义/来源断言与 Fake/Replay 控制流程；没有真实教师参与、没有真实模型质量或效率通过声明。

未做：M3 教师 UI/确认流、Vite PDF 回页、lease/取消/resume/retry、真实 provider 阻塞 I/O 超时/质量、完整物理 TTL、真实 PostgreSQL 并发。未读 `.env`、未连接 cn_v2/默认 PostgreSQL 做 upgrade、未下载大依赖、未改前端/中期材料、未 commit/stage/push。原有未跟踪中期笔记保留；git status 仍有历史临时目录 ACL 警告，未读/删这些目录。

## M1 实际交付（2026-10-26，历史阶段记录）

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

1. M2 已本地提交；下一步仅在授权后开 M3（教师 UI + 最小 lease/取消/显式恢复 + Vite 回 PDF）。
2. 创建 queued 仍不等于已执行调查，须显式 POST .../run。真实模型质量与外发真跑另行授权；PLAN-17 五件套仍可并行盘点。
3. 后续获得授权再开 M3 UI+PDF 回页+最小 lease/取消/显式恢复；PLAN-17 五件套仍必做，可并行盘点。
4. 开工前明确当前切片与隔离数据库测试范围；真实模型、问句外发、破坏性迁移仍须当次授权。禁止默认 DATABASE_URL/正式 cn_v2 迁移；不默认 push。

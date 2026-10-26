# TASK: Agent 运行时可靠性与权限治理

> 对齐 [结题已拍板规格](../结题已拍板规格.md)。

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-15 |
| 状态 | **已落地**：M1/M2/M3 + **最小物理 TTL（2026-10-26）**；cn_v2 0015；待后置：PG 真实并发 / 完整 Trace UI |
| 须授权 | 真实模型调用、真实课程问句外发、正式库破坏性迁移均须当次明确授权；优先隔离数据库和 Fake/Replay |

## 目标

- 为教师调查任务提供持久化状态、步骤状态、Trace 和明确终态。
- 实现可解释的取消、超时、有限重试与安全恢复，避免重复副作用。
- 对所有 Agent 工具执行服务端课程权限、参数 schema、预算和 allowlist 检查。
- 用 PLAN-14 Harness 对正常与异常路径回归。

## 非目标

- 不在本卡实现教师调查报告的完整业务流程（由 PLAN-16 承担）。
- 不引入 Redis、Celery、外部队列或新编排框架，除非代码审查证明现有方案无法满足要求且另行批准。
- 不自动修改课程资料、索引、成员或权限；这些业务动作须单独确认。
- 不将模型生成的“恢复建议”当作可靠检查点。

## 验收标准

- [ ] 任务和步骤状态可持久化，成功、失败、取消、超预算等首版状态可区分；错误不会留下永久运行中的任务。首版“等待确认”仅为外发前 UI/请求确认，不含 waiting_approval 业务审批状态或写工具。
- [ ] 步骤状态可从持久化事件流重建；每个 `(task_id, sequence)` 唯一，状态/检查点/事件原子提交，回滚后没有半条 Trace。
- [ ] 同一 `(course_id, created_by, idempotency_key_hash)` 并发创建最多得到一个任务；相同指纹复用，不同指纹冲突。未运行独立 PostgreSQL 并发测试时，必须明确记录该证据缺口。
- [x] 同课同时仅 1 个 queued/running/cancel_requested 活跃调查；新建冲突返回确定性错误，resume/retry 同样原子检查。
- [ ] 取消后不启动新的工具步骤；超时和异常均记录原因与终态；主路径及取消/中断合法转移按任务合同 §3。
- [x] M3 一次进程中断后标 interrupted，仅显式 resume 回 queued 或失败；复检当前课程教师权限、资料/来源、外发确认及剩余额度，旧 token 不得写回。显式 retry 为同任务新 attempt，禁止静默重启终态。
- [ ] M1 创建/单任务读取、M2 报告读取 API 均挂 require_course_teacher；创建后独立读持久化任务、无权者读不到。
- [ ] 预算按任务合同 §7 累计跨 attempt，下一调用前检查、每次调用有限超时；合法 finish 例外、取消 > 预算 > 成功与有限工具重试均有边界证据。
- [ ] Trace 可关联任务、步骤、工具调用、权限判定、证据 ID/页码、耗时、错误和预算字段（可获得时）。
- [ ] 服务端强制课程/文档/Chunk 授权；伪造 ID、越权参数和提示注入均不能扩大权限。
- [ ] 工具采用 allowlist 与结构化 schema；不允许任意 SQL、任意文件访问或隐式外网调用。
- [ ] PLAN-14 Harness 对正常、证据不足、工具失败、超时、取消、恢复、越权、预算耗尽和重复副作用的定向用例通过。
- [x] M1 范围运行定向 pytest、ruff、隔离迁移验证并贴原始输出；本轮不涉及 UI，不运行前端构建。后续批次仍须另行验收。
- [x] Alembic 0014 只新增任务/事件表；SQLite 隔离升级/降级和 PostgreSQL DDL 编译测试通过，未对默认 `DATABASE_URL` 或正式演示库运行迁移。

## M1 实际交付与证据（2026-10-26）

- [x] 15A：`AgentTask` / `AgentTaskEvent`、模型导出、Alembic metadata（含 InsightReview）和 0014（revises 0013）；SQLite 隔离升级/降级、FK/索引/唯一约束与 PostgreSQL 离线升级/降级 DDL 编译。
- [x] 15B 创建/读取子集：queued/attempt=1、服务端预算与零用量、配置留存到期时间、UTC 规范化、key hash/规范化指纹复用或冲突；task_created 事件和任务原子提交，失败回滚不留半条记录。
- [x] M1 API：`POST /courses/{course_id}/agent-tasks`、`GET /courses/{course_id}/agent-tasks/{task_id}` 都挂 `require_course_teacher`；独立 HTTP 登录与新 DB Session 可读提交结果。学生/其他课教师/无课程教师身份管理员被拒绝；错课、缺失与过期为安全 404；响应只投影安全字段。
- [x] 新建同课单活跃：`uq_agent_tasks_active_course` 为 SQLite/PostgreSQL partial unique index，覆盖 queued/running/cancel_requested；409 `active_investigation_conflict`。相同 key/指纹优先复用；不同指纹 409 `idempotency_conflict`。真实 SQLite 约束失败后回滚重查路径有确定性测试。
- [ ] PostgreSQL 独立并发集成：本轮只有离线 DDL，没有连接 PostgreSQL；不能以 SQLite 顺序/故障注入测试宣称真实 PG 并发已通过。
- [ ] 15B 后续状态/检查点/执行事件追加与序号分配：M1 只写 sequence=1 的创建事件，未实现通用事件写接口、步骤持久化重建或执行者写入。
- [x] M2 报告与有界 Fake/Replay 执行/来源门禁；M3 lease/token fencing/取消/显式 resume/retry API，SQLite H06/H07/H11/H-source。
- [ ] M3 教师页 build 与 Vite PDF 实点闭环；代码已实现，环境 `spawn EPERM` 阻塞，不能宣称已退出。完整物理 TTL 曾后置；**2026-10-26 已落地最小有界清理**（见下方专节）。

M1 创建不分发执行器、不外发数据；`confirm_external_processing=false` 可以排队。真实外发路径创建前拒绝与三类调用=0 spies 属于 M2，不能从本轮无执行器推断已验该门禁。测试命令、原始计数、警告与环境限制统一见 [SESSION_STATE](SESSION_STATE.md)。上方跨期复合验收项保留未勾选，不能把 M1 创建成功等同于生产运行时完成。

## M3 15C 实际交付（2026-10-26）

- [x] 复用 0014 既有 `run_token/lease_expires_at`，无新迁移。queued 原子 claim；进度、累计调用预留、检查点与 append-only 安全事件同事务落库，worker 更新带 token + 有效 lease 谓词。
- [x] queued/interrupted 取消立即 cancelled；running → cancel_requested；安全边界取消优先于预算/成功，不启动下一模型或工具。取消后的失效 lease 收敛 cancelled。
- [x] 读取任务/报告/事件时按该任务检查过期 lease，撤销旧 token → interrupted，旧 running 步骤追加 failed 收口；不自动 resume。无后台扫描/TTL worker。
- [x] POST resume/retry 重新执行当前课程教师权限与显式外发确认，resume 只读元数据复检来源及安全检查点；resume 后 run 前再检查来源。显式新 attempt 保留任务级累计预算；无额度 resume 为 budget_exceeded，retry 返回 409 agent_budget_exhausted；来源失效 failed/source_unavailable，检查点不安全 failed/investigation_checkpoint_unsafe。
- [x] H07 包含真正子进程：隔离文件 SQLite 提交 claim + 调用预留后 `os._exit(17)`；新 Session 判过期后显式恢复，新 attempt 保留计数。H11 以 SQLite partial unique index 直接拒绝冲突 UPDATE，取消/恢复路径保留幂等 key；没有真实 PostgreSQL 并发通过声明。
- 验证：9 个 `test_agent_*` 文件 **129 passed, 1 warning**；新增 runtime **22** 例；ruff `All checks passed!`。完整命令、环境失败、前端和本地提交限制见 [SESSION_STATE](SESSION_STATE.md#m3-本轮交付与证据2026-10-26)。
- 未做：真实 provider 调用及阻塞 I/O 超时质量验证、PG 并发、（历史）当时未做物理 TTL/Trace UI/M4；其后 M4 与最小 TTL 已另卡落地。`git add` 创建 `.git/index.lock` 被拒绝，因此尚无本地 commit；未 push。

## 约束

- 现有 schema 已完成静态盘点；首版确定采用 `agent_tasks` + `agent_task_events`，步骤状态由事件流重建，不新增独立 step 表。若实现/测试证明不足，须先更新设计记录再扩表。
- 使用现有 PostgreSQL/Alembic 与 Python 运行环境；默认不增加新的持久化基础设施。
- 日志最小化，禁止记录密钥、Cookie/Session 或无关个人信息。
- 一次会话一个实现项；真实计费请求与正式库操作须当次授权。

## 开工前代码盘点与持久化方案草案（2026-10-26）

### 已确认的现有基础

- 开工前 Alembic 为 `0013_insight_reviews`；M1 代码 head 已增加 `0014_agent_task_runtime`，仅隔离验证，未应用到演示库。`IngestJob` 只服务于文档入库，不复用为 Agent 任务。
- `QueryLog.created_at` 是来源时间字段；`query_log_retention_days` 默认 90 天，`maintain_query_logs` 支持有上限的 dry-run/delete 批次。
- `require_course_teacher` 从路由 `course_id`、当前 Session 和 `CourseMember` 关系重新验证教师权限；模型动作不应接受 `course_id`，每个工具执行时仍须重新检查 Chunk/Document 的课程归属与 `retrieval_enabled`。
- 当前模型没有通用任务恢复机制。`BackgroundTasks` 不能单独证明进程重启后的可恢复性。

### 两表数据结构（M1 已实现；迁移仅隔离验证）

首版确定采用 **两张表**，不引入 Redis/Celery，也不单独创建 `agent_task_steps`。步骤状态由不可变的事件流按 `(task_id, attempt, step_no)` 重建；若后续查询/恢复测试证明事件重建不能满足需求，再另立决策，不在首版重复维护两份步骤状态。

1. `agent_tasks`：
   - 身份/范围：`id` UUID 主键、`course_id` 外键、`created_by` 外键、固定 `task_type`、`focus`、UTC `window_start/window_end`、`confirm_external_processing`。
   - 幂等：必填 `idempotency_key_hash`、`request_fingerprint`；唯一约束 `(course_id, created_by, idempotency_key_hash)`。
   - 执行：`status`、`attempt`、`budget_json`、累计 `budget_used_json`、有界 `checkpoint_json`、`report_json`、`error_code`、`cancel_requested_at`、`run_token`、`lease_expires_at`、`last_event_sequence`。
   - 生命周期：`created_at/updated_at/started_at/finished_at/expires_at`。`course_id` 外键级联删除；`created_by` 沿用现有用户外键风格。状态使用 `VARCHAR` 并由合同层验证，不使用数据库原生 Enum，降低 SQLite/PostgreSQL 测试差异。
2. `agent_task_events`：`task_id`、`sequence`、`attempt`、可空 `step_no`、`event_type`、`tool_name`、`status`、`safe_summary`、`evidence_refs_json`、`error_code`、`duration_ms`、`created_at`。主键 `(task_id, sequence)`；`task_id` 外键级联删除。事件只追加，不原地更新；`last_event_sequence` 与新事件必须在同一事务中更新。

建议索引：任务列表 `(course_id, created_at)`、课程/状态列表 `(course_id, status, created_at)`、失效执行者扫描 `(status, lease_expires_at)`、过期清理 `(expires_at)`；事件按 `(task_id, sequence)` 主键顺序读取即可。避免为暂未使用的查询模式堆叠索引。

M1 另增加 `uq_agent_tasks_active_course`：按活跃状态过滤的 course_id 唯一索引，用数据库约束保证新建时同课单活跃。

`idempotency_key_hash` 使用客户端 key 的 SHA-256；`request_fingerprint` 使用规范化请求 JSON 的 SHA-256，规范化字段包含 course/user/task type、focus、UTC 窗口和外部处理确认，但不包含幂等 key 本身。相同 key + 相同指纹返回原任务；相同 key + 不同指纹返回冲突。并发竞态依靠数据库唯一约束，`IntegrityError` 后必须回滚并重新查询精确的幂等记录；若不存在对应记录，则按真正的数据库错误处理，不能把所有完整性错误误报为幂等冲突。

`last_event_sequence` 用于在持有任务行锁/执行原子更新时分配序号；事件写入、序号更新、任务状态与检查点更新必须原子提交。所有执行者写入都携带当前 `run_token`，过期执行者不能覆盖新 attempt 的状态或检查点。

`checkpoint_json` 只保存恢复所需的有界控制状态、来源 ID、Chunk/Document/Page 元数据与预算游标，不保存完整 Prompt、原始模型输出、原始学生问句或 snippet/excerpt。报告与 Trace 的来源引用只保留 ID；展示时在当前权限下动态解析 QueryLog，已删除/过期的来源显示 unavailable。报告仍须保存事实/证据/候选原因/未知/建议的结构化内容。

### 留存、恢复与并发约束

- 创建任务时，将输入时间窗口统一转换为 UTC；窗口超出当前 QueryLog 保留范围或结束时间明显晚于当前时间时拒绝，不静默截断。SQLite 往返可能丢失 timezone 标记，存储层读取时须规范化为 UTC-aware datetime。沿用 `query_log_retention_days`，首版不新增第二个容易漂移的留存配置。
- 初始 `expires_at = created_at + query_log_retention_days`；保存报告/检查点时，根据其中实际引用的 QueryLog，将过期时间收紧为 `min(当前 expires_at, min(source.created_at + retention_days))`。不得因任务引用旧问句而延长原始问句寿命。源日志被提前删除时，报告仍可存在至任务 TTL，但 UI/来源解析必须显示 `unavailable`，不得从 Trace/checkpoint 恢复原文。
- 完整有界清理服务可后置，不作为 M1/M2 的前置；任务读取、来源解析和恢复仍须遵守过期/删除与当前权限边界，不得因物理清理暂缓继续展示失效来源。若实施显式清理入口，沿用 `query_log_cleanup_batch_size`，不宣称已配置定时清理。
- 预算是任务级累计预算，不因 retry/resume 重置；`budget_used_json` 必须与事件计数保持一致，恢复前计算剩余调用/时间额度。首次创建设初始 attempt；显式 retry/resume 接受时原子递增 attempt，普通 claim 只设置 `run_token/lease_expires_at`、不重复递增；心跳/进度更新延长 lease，所有写入校验 token。
- 取消 `queued` 任务可直接进入 `cancelled`；取消 `running` 任务先记 `cancel_requested`，执行者只在模型/工具调用安全边界停止后确认 `cancelled`。不能保证强行中断阻塞调用；HTTP/provider timeout 仍须独立生效。
- 启动扫描可重新分发尚未领取的 `queued` 任务（领取操作必须使用原子 compare-and-set，确保多 worker 只有一个拿到 lease）；将 lease 已过期的 `running` 任务标为 `interrupted`（若已有取消请求，则收敛为 `cancelled`，并保留可解释事件）。不自动恢复 `interrupted`。用户显式 resume 后重新验证教师权限、来源存在性、文档可检索状态、外部处理确认与剩余预算，回 queued 或明确失败；检查点不能安全续跑时 failed，无额度时 budget_exceeded。
- 检查点只保存有界的控制状态、来源 ID、Chunk/Document/Page 元数据与预算游标，不保存完整 Prompt、原始模型输出、原始问句、snippet/excerpt 或异常原文。若检查点不足以安全续跑则 failed；可安全恢复时按确定性边界补查，只读工具重跑必须计入累计预算并重新执行权限检查。首版无业务写工具，不宣称通用 exactly-once 副作用保障。
- 事件 `safe_summary` 只能由服务端固定模板生成；`evidence_refs_json` 仅放 ID/页码等必要引用，不放查询文本或片段。报告 JSON 包含结构化发现等正文，来源引用仅存 ID，不复制原始问句；报告自由文本的问句复述检查由 PLAN-16 报告生成链路验收。

### 已冻结的运行时合同

- 主路径 queued → running → succeeded|failed|cancelled|budget_exceeded，含 cancel_requested 与崩溃 interrupted；首版无业务审批工具。
- 同课活跃范围与确定性冲突、同任务新 attempt 的显式 retry/resume、旧 token 撤销与旧步骤收口均按 [任务合同 §3](../teacher-agent-task-contract.md#3-任务状态合同)。
- 预算初值及跨 attempt 累计、有限超时、下一调用前检查、禁止静默整任务重试、工具有限重试与 finish 竞争例外只在 [任务合同 §7](../teacher-agent-task-contract.md#7-初始预算与可判定终止规则2026-10-26-用户确认) 维护；本卡不复制预算表。
- M1 退出为合同/Fake Harness+任务创建后持久化可读/无权拒绝；M2 报告 schema/来源校验落库、失败终态；M3 取消生效与一次进程中断后显式恢复。Harness 按 [合同 §9](../teacher-agent-task-contract.md#9-harness-首批场景与分期门禁) 分期，失效来源不可解析不能等物理 TTL 清理。

### 分批实施计划（M1 子集已实现，其余仍为计划）

批次是工作拆分，不要求按 15A～15E 全部完成后才开始 PLAN-16。M1 取 15A/15B 与最小权限/任务读取，M2 接入报告 API 所需的有界执行、终态与工具权限，M3 再补 15C 最小 lease/取消/恢复和教师 UI；15D 的对应验收随各期执行。完整 TTL 清理与 Trace UI 可后置；各期 API 责任与退出条件已在 [任务合同 §10](../teacher-agent-task-contract.md#10-分期退出与-api-责任已确认待用户下令实现) 冻结；M1 已按当次授权实施，见下方证据。

| 批次 | 范围与文件 | 必须证明 | 退出条件 |
| --- | --- | --- | --- |
| 15A 数据模型与迁移 | 新增 `backend/app/models/agent_task.py`、`backend/alembic/versions/0014_agent_task_runtime.py`、`backend/tests/test_agent_task_migration.py`；更新 `backend/app/models/__init__.py` 与 `backend/alembic/env.py` | 模型可由现有 SQLite fixture 创建；迁移链为 `0013 → 0014`；升级/降级仅影响新表；FK/唯一约束/索引与 PostgreSQL DDL 编译正确 | 专项迁移测试通过；无 repository/API/worker 变更；不连接默认 `DATABASE_URL` |
| 15B 事务存储与幂等 | 新增 `backend/app/services/agent_task_store.py`、`backend/tests/test_agent_task_store.py` | 相同 key+指纹复用任务；不同指纹冲突；序号单调；任务状态/检查点/事件原子提交；事务失败不留下半条状态；事件不包含原始查询/模型输出 | 定向存储测试通过；并发正确性依赖唯一约束，PostgreSQL 并发集成只能使用单独授权的隔离测试库 |
| 15C 生命周期与留存 | `backend/app/services/agent_task_runtime.py` 及对应测试；完整 `agent_task_retention.py` 清理可后置 | M2 有界执行/累计预算/异常终态；M3 最小 lease/token fencing、取消安全边界、stale running→interrupted、显式 resume/retry；各期不绕过来源留存边界 | 对应阶段定向测试通过；完整物理清理不阻塞报告 API；不声称通用 exactly-once、隐式恢复或定时清理已实现 |
| 15D 权限与 Harness 集成 | 新增 `backend/app/agent/tool_registry.py`（或按实际代码布局调整）、`backend/tests/test_agent_task_permissions.py`；扩展 Harness adapter 测试 | 固定 allowlist/schema；每次工具调用重新校验当前教师 membership、task.course_id、Document/Chunk 课程归属与 `retrieval_enabled`；跨课程伪造 ID 不返回内容 | H01–H12 中 PLAN-15 可承担的持久化/权限场景通过；完整调查流程与 UI 留给 PLAN-16 |
| 15E 统一收口 | 更新本卡与 `SESSION_STATE.md`；必要时补专门的迁移/恢复证据 | 定向 pytest、ruff、`git diff --check`；列明 Fake/SQLite 与 PostgreSQL 真实并发验证的证据差异 | 所有可验证项有命令/输出；真实模型、外发问句、正式库迁移仍明确未做 |

### 每批开工/验证命令

```powershell
# 仓库根目录；先保留并记录现有未提交状态
git status --short

# 15A 后
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_task_migration.py -q
backend/.venv/Scripts/python.exe -m ruff check backend/app/models/agent_task.py backend/app/models/__init__.py backend/alembic/env.py backend/tests/test_agent_task_migration.py

# 15B 后
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_task_store.py -q
backend/.venv/Scripts/python.exe -m ruff check backend/app/services/agent_task_store.py backend/tests/test_agent_task_store.py

# 15C 后
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_task_runtime.py backend/tests/test_agent_task_retention.py -q
backend/.venv/Scripts/python.exe -m ruff check backend/app/services/agent_task_runtime.py backend/app/services/agent_task_retention.py backend/tests/test_agent_task_runtime.py backend/tests/test_agent_task_retention.py

# 15D 后
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_task_permissions.py -q
backend/.venv/Scripts/python.exe -m ruff check backend/app/agent backend/tests/test_agent_task_permissions.py

# 15E 最终定向回归（上述测试文件均已存在后）
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_task_migration.py backend/tests/test_agent_task_store.py backend/tests/test_agent_task_runtime.py backend/tests/test_agent_task_retention.py backend/tests/test_agent_task_permissions.py backend/tests/test_agent_contracts.py backend/tests/test_agent_replay_harness.py -q

# 所有涉及文件的最终 Ruff；禁止不加范围地运行全量检查
backend/.venv/Scripts/python.exe -m ruff check backend/app/agent backend/app/models/agent_task.py backend/app/models/__init__.py backend/alembic/env.py backend/app/services/agent_task_store.py backend/app/services/agent_task_runtime.py backend/app/services/agent_task_retention.py backend/tests/test_agent_task_migration.py backend/tests/test_agent_task_store.py backend/tests/test_agent_task_runtime.py backend/tests/test_agent_task_retention.py backend/tests/test_agent_task_permissions.py
git diff --check
```

上述分批文件名是计划目标；如果实现前发现仓库布局已有更合适的等价模块，先更新本卡再改代码。每批结束都更新真实文件、测试结果和剩余风险，不把后续批次预先标记通过。

M1 已新增 SQLAlchemy 模型、0014、事务存储和创建/读取 API；没有实现生产执行器。M2 调查报告仍待实施。迁移仅在隔离 SQLite 验证升级/降级及 PostgreSQL 离线 DDL 编译，不应用到默认或演示数据库。

## 禁止改动的路径

- .env、密钥、Cookie/Session 明文、.git、venv、node_modules。
- 评测金标与既有冻结题集；不得删除失败样本。
- 用户未点名的 corpus/local、正式演示数据库和既有用户未提交改动。
- 与任务运行时无关的学生问答逻辑或教师 UI 重构。

## 相关上下文

- [PLAN-14 合同与 Harness](PLAN-14-agent-harness-contract.md)
- [产品合同](../结题产品定义与完工标准.md) §4.1、§6.H
- [验收合同](../validation.md) §8
- [施工计划](../implementation-plan.md) PLAN-15
- 历史参考：`中期答辩材料/笔记/04-教师侧Agent与Harness实施方案.md`（冻结，非链接）
- [硬规则](../../AGENTS.md)、[会话状态](SESSION_STATE.md)

## 验证步骤

1. 检查 git status、依赖任务与当前授权；不读取 .env。
2. 盘点已有 schema、任务/会话表、权限依赖与测试 fixture。
3. 在隔离测试环境实现状态、Trace、取消/超时与恢复；先通过 Fake/Replay 验证。
4. 执行定向 pytest、ruff、必要的迁移测试和 git diff --check。
5. 逐项贴原始输出；真实模型与正式库验证未授权时保持未完成。

## 最小物理 TTL（2026-10-26 Asia/Shanghai）

- [x] 服务 `maintain_agent_tasks`：按 `expires_at <= now(UTC)` 有界批次 dry_run/delete；**无新迁移**；依赖 FK CASCADE 清 events。
- [x] 管理 API `POST /admin/agent-tasks/retention`（`require_admin`），batch 复用 `query_log_cleanup_batch_size`。
- [x] 定向测试 `test_agent_task_retention.py`：过期等号、8 状态、未过期保留、has_more、CASCADE、非 admin 403。
- 验证（bot 复验）：`test_agent_task_retention`+`test_query_log_retention` **20 passed**；+store+api **42 passed**；ruff All checks passed。
- 说明：**物理 TTL ≠ 失效来源解析门禁**（后者 M2/M3 已有，不后置）。无后台 worker；未对演示库执行破坏性 delete。
- 未做：定时扫描、PG 真实并发、完整 Trace UI。

# TASK: Agent 运行时可靠性与权限治理

> 对齐 [结题已拍板规格](../结题已拍板规格.md)。

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-15 |
| 状态 | ready（开工计划已细化；实现尚未开始） |
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

- [ ] 任务和步骤状态可持久化，成功、失败、取消、等待确认、超预算等状态可区分；错误不会留下永久运行中的任务。
- [ ] 步骤状态可从持久化事件流重建；每个 `(task_id, sequence)` 唯一，状态/检查点/事件原子提交，回滚后没有半条 Trace。
- [ ] 同一 `(course_id, created_by, idempotency_key_hash)` 并发创建最多得到一个任务；相同指纹复用，不同指纹冲突。未运行独立 PostgreSQL 并发测试时，必须明确记录该证据缺口。
- [ ] 取消后不启动新的工具步骤；超时和异常均记录原因与终态。
- [ ] 可从安全检查点恢复；恢复前重新检查当前用户权限、资料状态和待确认动作，已完成副作用不重复执行。
- [ ] Trace 可关联任务、步骤、工具调用、权限判定、证据 ID/页码、耗时、错误和预算字段（可获得时）。
- [ ] 服务端强制课程/文档/Chunk 授权；伪造 ID、越权参数和提示注入均不能扩大权限。
- [ ] 工具采用 allowlist 与结构化 schema；不允许任意 SQL、任意文件访问或隐式外网调用。
- [ ] PLAN-14 Harness 对正常、证据不足、工具失败、超时、取消、恢复、越权、预算耗尽和重复副作用的定向用例通过。
- [ ] 运行定向 pytest、ruff；如涉及 UI 或迁移，按实际范围执行构建与隔离库验证并贴原始输出。
- [ ] Alembic 0014 只新增任务/事件表；SQLite 隔离升级/降级和 PostgreSQL DDL 编译测试通过，未对默认 `DATABASE_URL` 或正式演示库运行迁移。

## 约束

- 现有 schema 已完成静态盘点；首版确定采用 `agent_tasks` + `agent_task_events`，步骤状态由事件流重建，不新增独立 step 表。若实现/测试证明不足，须先更新设计记录再扩表。
- 使用现有 PostgreSQL/Alembic 与 Python 运行环境；默认不增加新的持久化基础设施。
- 日志最小化，禁止记录密钥、Cookie/Session 或无关个人信息。
- 一次会话一个实现项；真实计费请求与正式库操作须当次授权。

## 开工前代码盘点与持久化方案草案（2026-10-26）

### 已确认的现有基础

- Alembic 当前版本为 `0013_insight_reviews`；目前没有 Agent task/event 表。`IngestJob` 只服务于文档入库，不应复用为 Agent 任务。
- `QueryLog.created_at` 是来源时间字段；`query_log_retention_days` 默认 90 天，`maintain_query_logs` 支持有上限的 dry-run/delete 批次。
- `require_course_teacher` 从路由 `course_id`、当前 Session 和 `CourseMember` 关系重新验证教师权限；模型动作不应接受 `course_id`，每个工具执行时仍须重新检查 Chunk/Document 的课程归属与 `retrieval_enabled`。
- 当前模型没有通用任务恢复机制。`BackgroundTasks` 不能单独证明进程重启后的可恢复性。

### 建议的最小数据结构（草案；本节尚未授权/执行迁移）

首版确定采用 **两张表**，不引入 Redis/Celery，也不单独创建 `agent_task_steps`。步骤状态由不可变的事件流按 `(task_id, attempt, step_no)` 重建；若后续查询/恢复测试证明事件重建不能满足需求，再另立决策，不在首版重复维护两份步骤状态。

1. `agent_tasks`：
   - 身份/范围：`id` UUID 主键、`course_id` 外键、`created_by` 外键、固定 `task_type`、`focus`、UTC `window_start/window_end`、`confirm_external_processing`。
   - 幂等：必填 `idempotency_key_hash`、`request_fingerprint`；唯一约束 `(course_id, created_by, idempotency_key_hash)`。
   - 执行：`status`、`attempt`、`budget_json`、累计 `budget_used_json`、有界 `checkpoint_json`、`report_json`、`error_code`、`cancel_requested_at`、`run_token`、`lease_expires_at`、`last_event_sequence`。
   - 生命周期：`created_at/updated_at/started_at/finished_at/expires_at`。`course_id` 外键级联删除；`created_by` 沿用现有用户外键风格。状态使用 `VARCHAR` 并由合同层验证，不使用数据库原生 Enum，降低 SQLite/PostgreSQL 测试差异。
2. `agent_task_events`：`task_id`、`sequence`、`attempt`、可空 `step_no`、`event_type`、`tool_name`、`status`、`safe_summary`、`evidence_refs_json`、`error_code`、`duration_ms`、`created_at`。主键 `(task_id, sequence)`；`task_id` 外键级联删除。事件只追加，不原地更新；`last_event_sequence` 与新事件必须在同一事务中更新。

建议索引：任务列表 `(course_id, created_at)`、课程/状态列表 `(course_id, status, created_at)`、失效执行者扫描 `(status, lease_expires_at)`、过期清理 `(expires_at)`；事件按 `(task_id, sequence)` 主键顺序读取即可。避免为暂未使用的查询模式堆叠索引。

`idempotency_key_hash` 使用客户端 key 的 SHA-256；`request_fingerprint` 使用规范化请求 JSON 的 SHA-256，规范化字段包含 course/user/task type、focus、UTC 窗口和外部处理确认，但不包含幂等 key 本身。相同 key + 相同指纹返回原任务；相同 key + 不同指纹返回冲突。并发竞态依靠数据库唯一约束，`IntegrityError` 后必须回滚并重新查询精确的幂等记录；若不存在对应记录，则按真正的数据库错误处理，不能把所有完整性错误误报为幂等冲突。

`last_event_sequence` 用于在持有任务行锁/执行原子更新时分配序号；事件写入、序号更新、任务状态与检查点更新必须原子提交。所有执行者写入都携带当前 `run_token`，过期执行者不能覆盖新 attempt 的状态或检查点。

`checkpoint_json` 只保存恢复所需的有界结构化状态/已完成只读工具结果，不保存完整 Prompt、原始模型输出或原始学生问句。报告与 Trace 只保留来源 ID；展示时在当前权限下动态解析 QueryLog，已删除/过期的来源显示 unavailable。若 checkpoint 保存课件 snippet/excerpt，也必须纳入任务 TTL 并限制长度。

### 留存、恢复与并发约束

- 创建任务时，将输入时间窗口统一转换为 UTC；窗口超出当前 QueryLog 保留范围或结束时间明显晚于当前时间时拒绝，不静默截断。SQLite 往返可能丢失 timezone 标记，存储层读取时须规范化为 UTC-aware datetime。沿用 `query_log_retention_days`，首版不新增第二个容易漂移的留存配置。
- 初始 `expires_at = created_at + query_log_retention_days`；保存报告/检查点时，根据其中实际引用的 QueryLog，将过期时间收紧为 `min(当前 expires_at, min(source.created_at + retention_days))`。不得因任务引用旧问句而延长原始问句寿命。源日志被提前删除时，报告仍可存在至任务 TTL，但 UI/来源解析必须显示 `unavailable`，不得从 Trace/checkpoint 恢复原文。
- 新增有界、最旧优先的任务清理服务；同一事务内删除过期事件和任务，清理批次沿用 `query_log_cleanup_batch_size`。首版只提供可测试的显式清理入口，不宣称已配置定时清理；调度/运维入口另行确认。
- 预算是任务级累计预算，不因 retry/resume 重置；`budget_used_json` 必须与事件计数保持一致，恢复前计算剩余调用/时间额度。任务执行 claim 时增加 `attempt` 并设置 `run_token/lease_expires_at`；心跳/进度更新延长 lease，所有写入校验 token。
- 取消 `queued` 任务可直接进入 `cancelled`；取消 `running` 任务先记 `cancel_requested`，执行者只在模型/工具调用安全边界停止后确认 `cancelled`。不能保证强行中断阻塞调用；HTTP/provider timeout 仍须独立生效。
- 启动扫描可重新分发尚未领取的 `queued` 任务（领取操作必须使用原子 compare-and-set，确保多 worker 只有一个拿到 lease）；将 lease 已过期的 `running` 任务标为 `interrupted`（若已有取消请求，则收敛为 `cancelled`，并保留可解释事件）。不自动恢复 `interrupted`。用户显式 resume 后重新验证教师权限、来源存在性、文档可检索状态、外部处理确认与剩余预算。
- 检查点只保存有界的控制状态、来源 ID、Chunk/Document/Page 元数据与预算游标，不保存完整 Prompt、原始模型输出、原始问句、snippet/excerpt 或异常原文。若检查点不足以安全续跑，则从确定性安全边界重新调查；只读工具可以重跑，但必须计入累计预算并重新执行权限检查。首版无业务写工具，不宣称通用 exactly-once 副作用保障。
- 事件 `safe_summary` 只能由服务端固定模板生成；`evidence_refs_json` 仅放 ID/页码等必要引用，不放查询文本或片段。报告 JSON 遵守产品合同，仅存来源 ID；报告自由文本的问句复述检查由 PLAN-16 报告生成链路验收。

### 分批实施计划（每批独立验收；本轮仅完善计划）

| 批次 | 范围与文件 | 必须证明 | 退出条件 |
| --- | --- | --- | --- |
| 15A 数据模型与迁移 | 新增 `backend/app/models/agent_task.py`、`backend/alembic/versions/0014_agent_task_runtime.py`、`backend/tests/test_agent_task_migration.py`；更新 `backend/app/models/__init__.py` 与 `backend/alembic/env.py` | 模型可由现有 SQLite fixture 创建；迁移链为 `0013 → 0014`；升级/降级仅影响新表；FK/唯一约束/索引与 PostgreSQL DDL 编译正确 | 专项迁移测试通过；无 repository/API/worker 变更；不连接默认 `DATABASE_URL` |
| 15B 事务存储与幂等 | 新增 `backend/app/services/agent_task_store.py`、`backend/tests/test_agent_task_store.py` | 相同 key+指纹复用任务；不同指纹冲突；序号单调；任务状态/检查点/事件原子提交；事务失败不留下半条状态；事件不包含原始查询/模型输出 | 定向存储测试通过；并发正确性依赖唯一约束，PostgreSQL 并发集成只能使用单独授权的隔离测试库 |
| 15C 生命周期与留存 | 新增 `backend/app/services/agent_task_runtime.py`、`backend/app/services/agent_task_retention.py` 及对应测试 | 合法状态转移；取消安全边界；lease/token fencing；queued 安全重新分发、stale running→interrupted；显式 resume/retry；累计预算；来源 TTL 收紧；过期任务与事件有界清理 | 生命周期/留存测试通过；无自动重试、无隐式恢复、无定时清理的虚假承诺 |
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

当前只完成静态盘点和开工计划；尚未新增 SQLAlchemy 模型、Alembic 迁移、存储服务、API 或运行时服务。下一实现项为 15A；本卡变为 `ready` 仅表示计划清晰，不代表迁移获准应用到正式库。实施前仍须重新检查 `git status --short` 并保持正式演示库不变。

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
- [方案笔记](../../笔记/04-教师侧Agent与Harness实施方案.md)
- [硬规则](../../AGENTS.md)、[会话状态](SESSION_STATE.md)

## 验证步骤

1. 检查 git status、依赖任务与当前授权；不读取 .env。
2. 盘点已有 schema、任务/会话表、权限依赖与测试 fixture。
3. 在隔离测试环境实现状态、Trace、取消/超时与恢复；先通过 Fake/Replay 验证。
4. 执行定向 pytest、ruff、必要的迁移测试和 git diff --check。
5. 逐项贴原始输出；真实模型与正式库验证未授权时保持未完成。


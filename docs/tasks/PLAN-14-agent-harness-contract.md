# TASK: 教师 Agent 合同与 Harness 基线

> 对齐 [结题已拍板规格](../结题已拍板规格.md)。

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-14 |
| 状态 | **已落地**（M1；2026-10-26 代码已提交；Harness Fake 定向通过） |
| 须授权 | 真实模型调用、真实课程问句外发、破坏性迁移均不在默认授权内；首轮以文档、Fake/Replay 和隔离测试为主 |

## 目标

- 定义首个教师侧 Agent 任务：课程问题调查。
- 冻结任务输入/输出、工具边界、任务与步骤状态、终态、Trace、预算、取消/恢复与人工确认语义。
- 建立最小可运行的 Fake/Replay Harness 基线，供后续运行时和 Agent 工作流复用。

## 非目标

- 不实现完整教师 Agent 工作流，不修改正式课程资料。
- 不引入多 Agent、任意 SQL 工具、文件系统工具或外网访问。
- 默认不引入 LangGraph 等编排框架；仅在手写受控状态机经实现/测试证明不足后再议。
- 不以 Fake 结果代表真实模型调查质量。

## 验收标准

- [x] 新增教师调查任务合同，说明目标、课程/时间范围、输入、结构化输出、只读工具、人工确认点、预算与终态。
- [x] 合同明确 QueryLog 不保存最终答案/引用快照的限制，并定义任务/Trace 留存不得绕过现有查询日志留存策略；具体 `expires_at` 与清理执行仍由 PLAN-15 落地。
- [x] 任务状态、步骤状态、错误分类、重试/取消/恢复和幂等规则有明确表格；字段设计已对照现有 schema 静态盘点。数据库级幂等和持久化恢复仍由 PLAN-15 落地。
- [x] 合同目录已补 H01–H12、H-timeout 与外发未确认零调用，并冻结 M1/M2/M3 责任映射（仅文档确认，不代表场景执行通过）。
- [x] M1 Fake 必过 H01/H02/H03/H04/H05/H08/H09/H10/H-timeout；按合同 §7 验计数/时间/合法 finish 边界，逐例记录调用次数、终态和禁止副作用。
- [x] M1 与 PLAN-15 最小子集共同交付任务创建/单任务读取 API：提交后独立请求可读持久化任务；无权者读不到，统一 require_course_teacher。
- [x] 新冻结规则按当前半成品实际复验；历史 26 passed 不代表本次冻结合同已通过。
- [x] Fake/Replay 输入与预期结果可版本化，能够断言终态、Trace 事件、工具调用及禁止副作用（内存回放层；持久化恢复与幂等仍待 PLAN-15）。
- [x] 文档明确区分控制流程测试、真实模型质量、开发者观察和独立核验。
- [x] 既有内存基线曾运行定向测试与触及路径 ruff（历史输出见下）；此前纯文档轮未重跑；本轮 M1 已复验，真实证据见下方 M1 复验与 SESSION_STATE。

## Harness 分期（目标门禁，均须实际证据）

| 阶段 | 归属 |
| --- | --- |
| M1 | H01 正常内存、H02 证据不足、H03 空检索、H04 非法动作、H05 工具异常、H08 越权、H09 预算、H10 注入、H-timeout 模型/运行超时；另验任务持久化创建后可读/无权拒绝 |
| M2 | H01 报告 schema/来源落库；外发未确认创建前拒绝且外部调用=0；空窗/无数据与 E5-A Fake 门禁；H12 失效来源不可解析 |
| M3 | H06 取消、H07 显式恢复、H11 幂等（DB）；来源 unavailable；UI 外发确认与 Vite 引用点击回 PDF 页；复验 H12 |
| 可后置 | H12 物理 TTL 清理，失效来源不可解析必须在 M2/M3 验 |

详细注入/断言以 [任务合同 §9](../teacher-agent-task-contract.md#9-harness-首批场景与分期门禁) 为准。“等待确认”仅指外发前 UI/请求确认，不建设业务写审批工具。

## 当前实现与证据（2026-10-26）

- `backend/app/agent/contracts.py`：请求、动作、报告、预算、Trace 与状态转换合同；报告来源 ID 与 Chunk/Document/Page 元数据由服务端已观察集合核验。
- `backend/app/agent/replay_harness.py`：确定性内存回放 runner，仅使用注入的动作序列和 Fake 工具，不调用真实模型、网络或数据库；覆盖结构化动作、固定工具 allowlist、来源关联、预算终止、取消安全边界、工具失败和 Trace 脱敏。
- `backend/tests/test_agent_contracts.py` 与 `backend/tests/test_agent_replay_harness.py`：目前覆盖正常搜索/打开证据/资料质量/完成报告、空检索与未知项、非法动作一次格式重试、越权 ID、报告引用校验、工具异常、提示注入样本、任务/步骤状态转换、步数/模型调用/工具数/证据数/模型返回后与工具返回后的运行时预算、取消安全边界。
- 尚未覆盖或不能由内存 Harness 证明：跨进程幂等、崩溃后持久化恢复、QueryLog 实际留存/过期、服务端每次工具调用的课程授权、阻塞中的真实 I/O 超时，以及真实模型报告质量。这些不得标记为已完成；持久化和权限集成由 PLAN-15/16 承接。
- 最近验证：`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_contracts.py backend/tests/test_agent_replay_harness.py -q` → **26 passed, 1 warning**；触及路径 `ruff check` 全部通过；`git diff --check` 退出码 0。Markdown 相对链接扫描 17 份文件、120 个本地链接，`broken_count=0`。

上方 26 passed 是历史记录。本轮已按 M1 授权扩展现有代码，未另起 Agent 框架；创建/单任务读取及权限测试见 `test_agent_task_api.py`，隔离迁移与存储见 PLAN-15。当前真实命令/输出与剩余 M2/M3 缺口见 [SESSION_STATE](SESSION_STATE.md)。

## M1 本轮复验（2026-10-26）

- 指定五文件 pytest 最终原始输出：`69 passed, 2 warnings in 3.51s`（contract/replay 40、migration 2、store 17、API 10）。指定范围 Ruff 与 main/conftest 补充 Ruff 均 `All checks passed!`。完整命令和环境记录见 [SESSION_STATE](SESSION_STATE.md)。
- 默认预算保持 8/6/8/120/12/6000；报告字符只计 summary + findings[].description。finish 计工具调用；全任务一次 schema 格式纠正；同工具/错误类只可重试一次。取消优先于预算/完成，最后合法 finish 可以成功。

| M1 Case | 明确测试证据（test_agent_replay_harness.py） |
| --- | --- |
| H01 | `test_replay_search_then_finish_succeeds_with_safe_trace`、`test_search_open_quality_and_finish_follow_known_evidence_chain` |
| H02/H03 | `test_empty_search_can_finish_with_explicit_unknowns_without_invented_evidence` |
| H04 | `test_invalid_action_gets_only_one_schema_retry`、`test_schema_correction_is_limited_to_one_per_task` |
| H05 | `test_tool_exception_message_is_not_copied_to_trace`、`test_recoverable_tool_error_retries_once_and_counts_both_calls`、`test_second_recoverable_failure_is_terminal_with_remaining_budget`、`test_same_recoverable_error_class_is_not_retried_again_later_in_task` |
| H08 | `test_open_evidence_rejects_chunk_not_returned_by_search`、`test_report_with_unobserved_source_is_not_accepted` |
| H09 | step/model/tool/evidence/runtime budget tests；`test_last_legal_finish_counts_tool_and_may_complete_at_runtime_boundary`、`test_finish_is_refused_when_no_tool_call_budget_remains`、`test_cancel_wins_over_finish_returning_at_runtime_boundary` |
| H10 | `test_injected_tool_content_cannot_enable_an_unknown_action` |
| H-timeout | `test_injected_model_timeout_is_failed_and_does_not_start_another_call`、`test_injected_model_timeout_with_exhausted_runtime_is_budget_exceeded`、`test_model_runtime_overrun_is_budget_exceeded_without_next_call`、`test_tool_timeout_exhausting_runtime_stops_before_next_model_or_tool_call` |

状态合同已覆盖 queued→budget_exceeded、running→cancelled/interrupted/cancel_requested/budget_exceeded、interrupted 显式 resume、failed/cancelled/budget_exceeded 显式 retry；这不等于实现对应 API/生产运行时。超时采用确定性时钟/注入异常，无真实 sleep/provider；阻塞 I/O 的实际超时适配、固定初始摘要 I/O、持久化跨 attempt 预算仍属后续 PLAN-15/16。报告持久化来源门禁、真实外发门禁、E5-A 与 UI 恢复尚未验收。原有未跟踪 agent 包现已补齐 M1 切片，仍未 git add/commit/push。

## 约束

- 先检查当前代码、迁移和测试布局，不假定新文件路径已存在。
- 复用 FastAPI、pytest、现有 Fake Provider 和 PostgreSQL/pgvector；不引入第二套 RAG。
- 所有课程资料和问句均为不可信数据；工具权限必须由服务端强制校验。
- 一次会话一个实现项；不默认提交或 push。

## 禁止改动的路径

- .env、密钥、Cookie/Session 明文、.git、venv、node_modules。
- 评测金标、既有冻结题集与预期输出；不为测试通过覆盖原结果。
- 用户未点名的 corpus/local 与正式演示数据库。
- 与 PLAN-14 无关的业务代码、UI 或数据库迁移。

## 相关上下文

- [产品合同](../结题产品定义与完工标准.md) §4.2、§6.H
- [验收合同](../validation.md) §8
- [施工计划](../implementation-plan.md) PLAN-14
- 历史参考：`中期答辩材料/笔记/04-教师侧Agent与Harness实施方案.md`（冻结，非链接）
- [现有代码审查](../teacher-agent-current-code-audit.md)
- [任务与工具合同](../teacher-agent-task-contract.md)
- [硬规则](../../AGENTS.md)、[任务约定](README.md)、[会话状态](SESSION_STATE.md)

## 验证步骤

1. 开工先运行 git status --short，记录并保护现有改动；不读取 .env。
2. 检查当前任务/会话/日志 schema、Fake Provider 与测试组织，按实际布局调整本卡路径。
3. 先写合同与 Harness case schema，再实现最小 runner/断言，避免先写业务逻辑。
4. 运行定向 pytest、ruff 与文档链接/空白检查，记录原始输出、退出码和未完成项。
5. 更新本卡勾选项，只按实际证据标记完成；不得将计划描述当作验收结果。


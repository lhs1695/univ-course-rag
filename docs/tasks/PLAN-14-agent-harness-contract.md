# TASK: 教师 Agent 合同与 Harness 基线

> 对齐 [结题已拍板规格](../结题已拍板规格.md)。

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-14 |
| 状态 | in_progress |
| 须授权 | 真实模型调用、真实课程问句外发、破坏性迁移均不在默认授权内；首轮以文档、Fake/Replay 和隔离测试为主 |

## 目标

- 定义首个教师侧 Agent 任务：课程问题调查。
- 冻结任务输入/输出、工具边界、任务与步骤状态、终态、Trace、预算、取消/恢复与人工确认语义。
- 建立最小可运行的 Fake/Replay Harness 基线，供后续运行时和 Agent 工作流复用。

## 非目标

- 不实现完整教师 Agent 工作流，不修改正式课程资料。
- 不引入多 Agent、任意 SQL 工具、文件系统工具或外网访问。
- 不预先锁定 LangGraph 等编排框架；先定义语义与测试，再选型。
- 不以 Fake 结果代表真实模型调查质量。

## 验收标准

- [x] 新增教师调查任务合同，说明目标、课程/时间范围、输入、结构化输出、只读工具、人工确认点、预算与终态。
- [x] 合同明确 QueryLog 不保存最终答案/引用快照的限制，并定义任务/Trace 留存不得绕过现有查询日志留存策略；具体 `expires_at` 与清理执行仍由 PLAN-15 落地。
- [x] 任务状态、步骤状态、错误分类、重试/取消/恢复和幂等规则有明确表格；字段设计已对照现有 schema 静态盘点。数据库级幂等和持久化恢复仍由 PLAN-15 落地。
- [x] Harness 场景目录已列出正常、证据不足、空检索、工具异常、超时、取消、恢复、越权、预算耗尽、提示注入和重复请求等 H01–H12；依赖持久化/留存的 case 尚须在 PLAN-15/16 集成测试中执行，不能由内存回放替代。
- [x] Fake/Replay 输入与预期结果可版本化，能够断言终态、Trace 事件、工具调用及禁止副作用（内存回放层；持久化恢复与幂等仍待 PLAN-15）。
- [x] 文档明确区分控制流程测试、真实模型质量、开发者观察和独立核验。
- [x] 运行新增定向测试与触及路径的 ruff；纯文档/测试夹具变更完成链接检查和 git diff --check。

## 当前实现与证据（2026-10-26）

- `backend/app/agent/contracts.py`：请求、动作、报告、预算、Trace 与状态转换合同；报告来源 ID 与 Chunk/Document/Page 元数据由服务端已观察集合核验。
- `backend/app/agent/replay_harness.py`：确定性内存回放 runner，仅使用注入的动作序列和 Fake 工具，不调用真实模型、网络或数据库；覆盖结构化动作、固定工具 allowlist、来源关联、预算终止、取消安全边界、工具失败和 Trace 脱敏。
- `backend/tests/test_agent_contracts.py` 与 `backend/tests/test_agent_replay_harness.py`：目前覆盖正常搜索/打开证据/资料质量/完成报告、空检索与未知项、非法动作一次格式重试、越权 ID、报告引用校验、工具异常、提示注入样本、任务/步骤状态转换、步数/模型调用/工具数/证据数/模型返回后与工具返回后的运行时预算、取消安全边界。
- 尚未覆盖或不能由内存 Harness 证明：跨进程幂等、崩溃后持久化恢复、QueryLog 实际留存/过期、服务端每次工具调用的课程授权、阻塞中的真实 I/O 超时，以及真实模型报告质量。这些不得标记为已完成；持久化和权限集成由 PLAN-15/16 承接。
- 最近验证：`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_agent_contracts.py backend/tests/test_agent_replay_harness.py -q` → **26 passed, 1 warning**；触及路径 `ruff check` 全部通过；`git diff --check` 退出码 0。Markdown 相对链接扫描 17 份文件、120 个本地链接，`broken_count=0`。

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
- [方案笔记](../../笔记/04-教师侧Agent与Harness实施方案.md)
- [现有代码审查](../teacher-agent-current-code-audit.md)
- [任务与工具合同](../teacher-agent-task-contract.md)
- [硬规则](../../AGENTS.md)、[任务约定](README.md)、[会话状态](SESSION_STATE.md)

## 验证步骤

1. 开工先运行 git status --short，记录并保护现有改动；不读取 .env。
2. 检查当前任务/会话/日志 schema、Fake Provider 与测试组织，按实际布局调整本卡路径。
3. 先写合同与 Harness case schema，再实现最小 runner/断言，避免先写业务逻辑。
4. 运行定向 pytest、ruff 与文档链接/空白检查，记录原始输出、退出码和未完成项。
5. 更新本卡勾选项，只按实际证据标记完成；不得将计划描述当作验收结果。


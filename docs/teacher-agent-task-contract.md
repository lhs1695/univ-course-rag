# 教师课程问题调查 Agent：任务与工具合同

状态：PLAN-14 设计基线 v0.2（2026-10-26 用户确认）。M1/M2/M3 退出、权限、状态/并发/retry、预算、Harness 与 E5-A 已冻结；实现待用户下令。文中预算为合同初值，不是性能承诺；历史实现记录不代表本轮复验。

## 1. 首版任务边界

任务类型固定为 `course_question_investigation`。教师选择一个课程与时间窗口，系统先读取现有课程级统计，再通过受控的有限工具调用调查：

- 重复问句与相似问题候选；
- 依据不足（`no_evidence`）；
- 系统失败及相关错误码；
- 当前课程资料的相关证据与资料处理质量警告。

首版不做个体学生掌握度/成绩推断，不直接修改课程资料、索引、成员或权限，也不建设通用教师聊天机器人或多 Agent 平台。

**重要限制：** 当前 QueryLog 不保存最终回答正文或实际引用快照。首版只能根据结果状态、候选 Chunk 线索和当前课程证据进行调查，不能声称已回溯审计历史回答正文。

## 2. 输入合同

- `course_id` 只来自 API 路径，并由服务端课程教师权限依赖解析；请求 JSON 和模型动作中都不接受可覆盖的 course_id。
- `start_at`、`end_at` 为带时区时间；服务端统一转换为 UTC，要求 start < end，窗口必须落在当前 QueryLog 留存范围内。
- 默认 UI 窗口建议为最近 7 天，单次调查窗口上限建议 30 天；超出上限应要求缩小范围，而不是静默截断。
- `idempotency_key` 在数据库中按 `(course_id, created_by)` 作用域唯一：相同 key 且规范化请求指纹相同，返回既有任务；相同 key 但指纹不同，返回确定性冲突。并发正确性依靠数据库唯一约束，不依靠进程内缓存；PLAN-15 实现。
- `focus` 取值为 `all`、`repeated_questions`、`no_evidence`、`system_failures`。
- 请求必须显式包含 `confirm_external_processing`。当执行路径会将课程问句/证据发送给非 Fake 的外部 LLM、Embedding 或语义分组服务时，未确认必须在创建任务前拒绝，不能先排队后才询问；三类外部调用计数均须为 0。确认只能来自当前请求/受控任务上下文，模型不得代为确认。首版“等待确认”仅指外发前 UI/请求确认，不实现业务写审批工具。
- 任务预算由服务端控制，模型和客户端不得自行提高预算。

## 3. 任务状态合同

合法主路径：`queued → running → succeeded|failed|cancelled|budget_exceeded`；取消和崩溃另经下表安全边界收敛。

| 状态 | 含义 | 合法转移 |
| --- | --- | --- |
| `queued` | 已持久化，尚未领取 | `running`、`cancelled`；领取前预算不足则 `budget_exceeded` |
| `running` | 一个执行者持有有效执行权 | `succeeded`、`failed`、`cancel_requested`、`cancelled`、`interrupted`、`budget_exceeded` |
| `cancel_requested` | 已请求取消，等待当前调用安全结束或超时 | `cancelled`；进程退出/lease 失效也收敛为 `cancelled`，不恢复执行 |
| `interrupted` | 崩溃/lease 失效，旧执行权已撤销 | 显式 resume 并通过复检后 `queued`；无法安全恢复则 `failed`；用户取消则 `cancelled` |
| `succeeded` | 报告 schema/来源校验及落库完成 | 成功终态，不自动重启 |
| `failed` | 不可恢复错误或有限重试耗尽 | 当前 attempt 终态；只有显式 retry 可启动同任务新 attempt → `queued` |
| `cancelled` | 取消已生效 | 当前 attempt 终态；只有显式 retry 可启动同任务新 attempt → `queued` |
| `budget_exceeded` | 调用/时间/输出预算不满足继续执行 | 当前 attempt 终态；显式 retry 仍受累计剩余额度限制，不得重置预算 |

- **同课同时仅 1 个活跃调查**：`queued/running/cancel_requested` 算活跃；跨教师同样受限。新建、resume、retry 进入 `queued` 均须由数据库约束/事务原子保证，冲突返回确定性 `409 active_investigation_conflict`。同幂等 key/同指纹先返回既有任务，不算新建；不同指纹返回 `409 idempotency_conflict`。
- **显式 retry = 同任务新 attempt**：不创建另一任务 ID，接受请求时原子递增 attempt，再入 `queued`；旧 attempt 的终态/事件保留。禁止后台静默整任务重试或重开终态任务。已成功任务无需 retry；重复创建同 key 也不触发 retry。`budget_exceeded` 在已耗尽预算时拒绝 retry，返回稳定预算错误。
- resume 只面向 `interrupted`，显式操作接受时开始新 attempt、回 `queued`；普通 claim 不重复增加 attempt。恢复前复检当前课程教师权限、来源/资料可用性、外发确认及累计剩余额度；权限/确认不满足则拒绝且不发起调用，检查点不能安全恢复则 `failed`，无额度则 `budget_exceeded`。中断期间不计执行时间。
- lease/token fencing 在判定中断时撤销旧 token；旧执行者即使晚返回也不得写事件、检查点或覆盖新结果。旧 attempt 未完成的 running 步骤以 `failed` 和中断原因收口，新 attempt 用新步骤承接，不原地重开步骤。
- 取消优先于预算终止及成功提交，具体竞争与合法 finish 例外见 §7。状态/检查点/事件须原子提交后再报告成功。首版没有 `waiting_approval`，不实现业务写审批。

### 步骤状态

| 当前状态 | 允许转移 | 规则 |
| --- | --- | --- |
| `pending` | `running`、`skipped` | 尚未执行的步骤可启动或被安全跳过 |
| `running` | `succeeded`、`failed`、`skipped` | 每个已启动步骤必须有明确终态 |
| `succeeded` | 无 | 不可重开；重试创建新的 attempt/step |
| `failed` | 无 | 不可原地重开；重试创建新的 attempt/step |
| `skipped` | 无 | 终态 |

当前合同代码通过 `validate_step_transition` 拒绝从 `succeeded/failed/skipped` 回到 `running`。回放 Trace 使用 `step_started`、`step_succeeded`、`step_failed`、`step_skipped` 记录步骤终态；生产持久化由 PLAN-15 实现。

## 4. 步骤与 Trace 合同

每个步骤/事件至少记录：

- task_id、递增 sequence、attempt、step_no；
- event_type、step/tool 类型、状态；
- 开始/结束时间与 duration_ms（可获得时）；
- 安全的输入/输出摘要；
- evidence_refs（QueryLog ID、Chunk ID、Document ID、页码等）；
- error_code 与是否允许重试；
- 预算计数（步骤数、工具调用数、模型调用数）。

Trace 不记录 API Key、Cookie/Session、完整 Prompt、完整模型原始输出或不必要的学生身份字段。原始问句文本不应复制进 Trace；需要展示代表问句时，通过课程授权和当前 QueryLog 记录动态解析。源日志过期/删除后，UI 显示来源不可用，而不是从 Trace 还原内容。

稳定错误码按类别返回，不能把异常原文或 provider 响应透传到用户/Trace：

| 类别 | 稳定错误码示例 | 处理原则 |
| --- | --- | --- |
| 输入/动作合同 | `action_output_size_invalid`、`action_schema_invalid` | 不执行工具；最多一次格式重试 |
| 来源/权限/结果一致性 | `query_reference_not_allowed`、`chunk_reference_not_allowed`、`document_reference_not_allowed`、`evidence_reference_not_allowed`、`evidence_reference_mismatch`、`document_reference_mismatch`、`search_result_conflict` | 拒绝该动作或报告，不返回越权来源内容 |
| 预算 | `agent_step_or_runtime_budget_exceeded`、`agent_model_or_runtime_budget_exceeded`、`agent_tool_budget_exceeded`、`agent_evidence_budget_exceeded`、`agent_runtime_budget_exceeded`、`report_character_budget_exceeded`、`report_evidence_budget_exceeded` | 终止新增调用，保留可安全读取的已完成结果 |
| 执行/状态 | `tool_execution_failed`、`tool_result_schema_invalid`、`action_source_failed`、`replay_exhausted`、`transition_not_allowed`、`step_transition_not_allowed`、`explicit_resume_required`、`explicit_retry_required` | 只记录稳定类别，不保存异常原文；恢复/重试必须显式发起 |

任务结果与 Trace 的留存不能绕过 QueryLog 当前的留存策略。PLAN-15 的最小方案沿用 `query_log_retention_days`：任务创建时设置保守过期时间，报告/检查点关联来源后按最早来源的 `created_at + retention_days` 收紧 `expires_at`；读取/恢复时验证来源有效性。完整 TTL 物理清理可后置，不阻塞 M2 报告 API；若实施清理则使用有界批次。源 QueryLog 被提前删除时，报告显示来源不可用，不从 Trace/checkpoint 复原原文。具体行为仍待对应阶段验收。

## 5. 首版工具 allowlist

所有工具由服务端注册与调用，模型只能提出动作，不可执行任意代码、SQL、文件访问或外网请求。

| 工具 | 输入 | 服务端必须执行的检查 | 输出 |
| --- | --- | --- | --- |
| 初始课程摘要（固定步骤，不由模型调用） | course_id、时间窗口、focus | 使用 `require_course_teacher` 解析后的 course_id；限制窗口和留存期；聚合不读取 user_id 给模型 | 现有 `aggregate_course_insights` 的统计与线索；如报告需引用具体问句，再通过新增的有界 source resolver 解析 QueryLog ID，不读取或暴露 user_id |
| `search_course_evidence` | query | 使用 task 中固定 course_id；按已配置检索策略调用现有 `retrieve_chunks`；遵守外部处理确认、调用预算和证据上限 | Chunk ID、Document ID、页码、有限 snippet、score |
| `open_evidence` | chunk_id | 解析 UUID；Chunk 与 Document 必须都属于 task.course_id，且 Document 当前允许检索；不接受模型提供的 course_id | 文件名、页码、受限 excerpt、来源 ID |
| `get_document_quality` | document_id | Document 必须属于 task.course_id；按现有入库状态读取质量警告 | job_status、quality_warning、chunk_count 等必要元数据 |
| `finish` | InvestigationReport | 用 schema 校验；所有 QueryLog/Chunk/Document 引用必须来自本任务已授权观察或工具返回；不接受不存在的引用 | 保存结构化报告并结束任务 |

初始课程摘要应优先复用 `aggregate_course_insights`；语义分组仍遵守 `confirm_external_processing`，不在后台静默触发额外 Embedding。

## 6. 报告合同

报告至少包含：

- `summary`：课程级发现摘要，明确时间范围与样本量；
- `findings[]`：每项发现的类型、描述、支持来源 ID、相关证据 ID；
- `candidate_causes[]`：只允许候选原因，例如资料覆盖、检索/引用、问题表述、正常复习、系统故障、暂无法判断；
- `unknowns[]`：证据不足、资料未处理或当前日志无法支持的判断；
- `suggested_actions[]`：教师可选的下一步，不直接执行业务写入；
- `source_query_ids[]`、`evidence_refs[]`：报告中每项重要判断可回溯的来源。报告 JSON 不复制原始问句文本；UI 在授权范围内按 QueryLog ID 动态解析代表问句，源记录过期/删除后显示不可用。

禁止将“重复问句”直接写成知识盲区；禁止将 `no_evidence` 直接写成课件缺失；禁止把系统失败归为教学问题。没有来源的推断只能列为未知或候选解释。最终教师结论由教师在现有复核/业务界面记录。

M2 API 实际形态（2026-10-26，Fake/Replay）：POST `/courses/{course_id}/agent-tasks` 继续仅创建 queued；POST `/{task_id}/run` 显式同步执行，终态不自动重跑（409 `investigation_not_queued`）；GET `/{task_id}/report` 单独返回 `task_id/status/error_code/report/sample_count/summary/sources/evidence_sources`。以上后两条路径均接在 `/courses/{course_id}/agent-tasks` 下，统一 `require_course_teacher`；原任务详情白名单仍不含报告。未完成/失败报告为 null，失败含安全错误码。

`summary` 为执行时 metrics-v1 聚合快照，学生分母与最多 30 条最近授权学生尝试的 `sample_count` 分开记录；模型初始观察不含 user_id。当前请求中非 Fake LLM 或非 Fake Embedding 配置且未确认时，创建前 422 `external_processing_confirmation_required`，不落任务/事件；run 也复检当前配置与任务确认。即使确认，本期仍只执行 Fake/Replay，不构建真实 provider 或语义分组。Fake 默认报告只陈述日志观察；Replay 的证据工具为有界、同课、启用资料的 Fake 字面查找/读取，不宣称已接入生产语义检索。

落库前复用 `InvestigationReport`、`validate_report_references` 与 Replay Harness，并再次核对当前 QueryLog/Chunk/Document 授权元数据。报告及 checkpoint 不保存问句原文，Trace 不保存动作/问句/证据正文。报告读取仅投影来源元数据；过期/删除/错课问句、删除/禁用/错课资料或 Chunk 标 `available=false`（unavailable），不选取问句或 Chunk 正文。不再返回依赖失效来源的 findings/候选原因/建议，摘要改为不可核查提示；保留历史聚合快照及样本量并明确限制。原报告快照不在读取时重写，物理 TTL 另期处理。

## 7. 初始预算与可判定终止规则（2026-10-26 用户确认）

以下是服务端合同初值；模型、客户端、retry/resume 均不得自行调高或清零。Fake/Replay 用确定性时钟/计数证明边界，真实调用须另外验证 provider 超时。

| 预算维度 | 上限与计数 |
| --- | --- |
| Agent 决策步骤 | 最多 8 个；每次决策及格式纠正所用模型调用均记模型计数，格式纠正属于当前决策步骤 |
| 工具调用 | 最多 6 次；只读工具、重试和 `finish` 均在发起时计数；固定初始课程摘要不占模型决策工具数，但受执行时间、权限和外发门禁约束 |
| 模型调用 | 最多 8 次，包含至多 1 次 schema 格式纠正；再次格式错误明确 `failed` |
| 累计执行时间 | 上限 120 秒，跨 attempt 累计；排队、中断及人工等待不计入，执行中 provider/tool 阻塞、失败及有限重试耗时均计入 |
| 证据引用 | 最多 12 条；工具观察集合与最终报告引用均须有界 |
| 报告长度 | 摘要+结论合计 ≤ 6000 字符；按 `summary` 与 `findings[].description` 文本字符数之和判定，不按字节或 token 计；其余字段仍受 schema 自身长度/条目上限约束 |

1. **发起下一调用前检查剩余额度**：新决策/模型/工具须对应剩余计数 > 0 且累计执行时间 < 120 秒，先原子预留计数再发起；失败、超时、有限重试也消耗额度。不得发起第 9 个决策、第 7 次工具或第 9 次模型调用。刚好使用最后一次合法额度不等于失败；其结果若还要求新调用，则在下一调用前进入 `budget_exceeded`。
2. 使用单调时钟累计每段实际执行耗时，持久化跨 attempt 计数；执行段耗时与计数须随进度持久化，崩溃恢复不能把中断前已用额度清零，也不能把排队/人工等待算入执行时间。provider/tool 每次调用均须有有限超时，取配置的单次超时与剩余执行时间的较小值；不允许只在无限阻塞返回后检查 elapsed。模型超时收敛为 `failed`，若累计运行时间已耗尽则 `budget_exceeded`；取消按第 4 条优先处理。
3. **禁止静默整任务自动重试**。仅对 allowlist 中同类可恢复工具错误（如暂时超时/临时不可用）最多重试 1 次，计入同一累计调用/时间预算；权限拒绝、schema/引用错误不可按工具故障重试。一次 schema 格式纠正、工具有限重试与用户显式 retry/resume 分开记录；后者仍共享任务累计额度。
4. 完成/取消/预算同时到达：**取消 > 预算终止 > 成功完成**。提交前已有取消请求必须 `cancelled`。例外：`finish` 已在各项剩余额度内合法发起、输出满足 schema/来源/长度要求且无取消时，即使该调用用完最后一次计数或与时间边界同时返回，也允许 `succeeded`；不能在超额后补发 `finish`，已超时撤销的调用结果不能再提交。成功提交后的取消不追溯改写终态。
5. 证据/报告输出超限拒绝该输出并以 `budget_exceeded` 收口；不得靠额外模型调用压缩或美化预算终止。保留可授权读取的部分证据和检查点，给出确定性原因。额度耗尽的显式 retry 不产生新外部调用。

Harness 必须覆盖：上限/超一、最后合法 `finish`、取消/预算/完成竞争、调用不返回（有限超时）、恢复后仅剩余额度；所有场景记录模型/工具调用数、累计时间、终态及禁止副作用。

## 8. 模型动作协议

当前 LLM 适配器提供 `generate(prompt) -> str`，没有原生 function-calling 合同。首版采用受限 JSON 动作协议，且每次输出都经过 Pydantic schema 校验；禁止从 Markdown 代码块或任意文本中宽松提取 JSON。

- `search_course_evidence`：只允许一个有长度上限的 query。
- `open_evidence`：只能引用本任务之前已返回的 Chunk ID，且后端重新校验课程和文档权限。
- `get_document_quality`：只能引用本任务已知且属于当前课程的 Document ID。
- `finish`：提交结构化报告；引用不存在或不在本任务证据集合内时拒绝完成。
- 未知 action、额外字段、参数越界、非法 JSON 均不得执行工具。允许最多一次带 schema 错误摘要的格式重试，并计入模型预算；再次失败则进入明确失败终态。

工具结果和课件/问句内容均是不可信数据；任何其中包含的指令不得改变系统规则、工具 allowlist、课程范围或预算。

## 9. Harness 首批场景与分期门禁

下表是 **Fake/Replay 必过的目标门禁**，不是当前通过声明；每例固定输入/故障、预期终态、模型/工具调用次数及禁止副作用，执行后填实际证据。M1 内存断言不能代替 M2 API 或 M3 数据库/恢复/UI 证据。

| Case | 所属期与注入 | 必须断言 |
| --- | --- | --- |
| H01 正常调查 | M1 内存合法动作/来源；M2 报告 API | 内存 schema/引用/终态 succeeded；M2 校验并落库可独立读 |
| H02 证据不足 | M1 无合格证据 | 明示未知/不足，不编来源，不把 no_evidence 当课件缺失 |
| H03 空检索 | M1 search 返回空 | 有限补查或合法 finish，无无限循环 |
| H04 非法动作 | M1 非 JSON/多余字段/未知 action | 不执行非法工具；最多一次格式纠正，成功或 failed |
| H05 工具异常 | M1 可恢复/不可恢复错误 | 分类 Trace；同类可恢复错误最多重试 1 次，计预算，终态正确 |
| H06 取消 | M3 持久化 cancel_requested/安全边界 | 取消生效为 cancelled，不发起下一调用；lease 失效后同样收敛 |
| H07 恢复 | M3 一次进程中断/过期 lease | interrupted 后仅显式 resume；新 attempt、旧 token 不可写、复检权限/来源/确认/额度 |
| H08 越权引用 | M1 注入跨课 ID；M2/M3 集成复检 | 不返回越权内容；服务端拒绝不在授权观察集合内的引用 |
| H09 预算 | M1 确定性计数/时钟；M2/M3 累计执行 | §7 全部边界；budget_exceeded 不再调用，合法最后 finish 及取消优先例外可判定 |
| H10 提示注入 | M1 恶意课件/问句指令 | 仅当不可信数据，allowlist/权限/预算不变 |
| H11 幂等 | M3 数据库并发/重复 key | 同 key 同指纹同任务、异指纹确定冲突；同课仅一活跃任务，不能重复启动 |
| H12 留存失效 | M2 读取/来源解析；M3 UI/恢复 | 过期/删除来源 unavailable，失效内容不可继续解析/从 Trace 复原；物理 TTL 清理可后置 |
| H-timeout 模型/运行超时 | M1 内存可注入时钟/超时；M2 实际 adapter 有限超时 | 模型超时 failed 或累计运行超限 budget_exceeded，无永久 running；超时或取消后不启动下一调用 |
| H-external 外发未确认 | M2 外部路径 spies；M3 UI 未确认 | 创建前拒绝、无任务入队；外部 LLM/Embedding/语义分组调用计数各为 0 |
| H-task-read 持久化权限 | M1 创建后独立请求/会话读取 | 已提交任务可读；非本课教师读不到，响应不泄漏任务内容 |
| H-empty 空窗/无数据 | M2 固定空快照 | sample_count=0、无调查发现/候选原因，unknowns 说明无数据，正常报告 succeeded |
| H-source 来源 unavailable | M2 来源校验/读取；M3 UI/恢复时删除、禁用或撤权 | 不展示或继续解析内容；无有效来源的结论不得仍作可核查事实 |
| H-E5-A 固定对照 | M2 固定 Fake/Replay 夹具 | 通过 §9.2 全部门禁，记录分母与调用/耗时；不冒充真实模型质量 |

### 9.1 API / UI 硬验收

- 任务创建、单任务读取、报告读取均挂 `require_course_teacher` 一类课程教师权限依赖；工具与来源读取再验证当前权限。开发时的真实调用授权不能替代产品的外发确认。
- 真跑路径若未 `confirm_external_processing`，必须在创建前拒绝；M3 同时要求 UI 明确说明并由教师确认。用外部路径 spies 证明外部 LLM、Embedding、语义分组三项调用计数均为 **0**，不得只用 Fake 自身无网络证明；真实模型质量另获当次授权后测。
- 重要结论须可回溯 Document/页码；M3 经 **Vite** 走：授权课程发起调查 → 报告 → 依据 → 点引用 → 原 PDF 页，记录预期与实际 Document/页码。来源删除/禁用/越权不展示内容，后端拒绝解析；build 成功不代替点击验收。
- 首版“等待确认”仅是外发前 UI/请求确认；没有业务写审批工具。

### 9.2 E5-A 固定 Fake/Replay 对照与门禁

同课程、时间窗、样本快照下固定版本化夹具：A 统计与原始问句列表，B 相似组（若可用，缺少时明确不适用），C Agent 报告。夹具预列必需事实、允许来源、候选原因限定语、未知与建议、样本量和预期终态；重要判断（包括摘要/建议所依赖的事实）通过来源 ID 关联，涉及课件结论关联到 Document/页码。报告不复制原始问句，代表问句只在当前授权下动态解析。

通过条件（开发者核验即可，全部必过）：

- 夹具预列必需事实均有授权来源（覆盖数/预列必需事实数；空夹具分母为 0 时记不适用，另验 H-empty）。
- 捏造引用 = 0；候选原因写成确定事实 = 0；分别记录问题数/报告引用数、问题数/候选原因数，不能只验 ID 存在。
- `no_evidence` 不直接断言课件缺失；系统失败不归为教学问题；任务终态符合夹具。
- 空窗/无数据使用 H-empty 形态，不能杜撰教学问题；来源失效按 H12/H-source 隐去并停止解析内容。
- A/B/C 以同一快照复核；记录实际模型/工具调用次数及跨 attempt 累计执行耗时，Fake 成本标为 Fake、不推算真实费用。

无真实教师参与不得宣称效率已验证；真实模型质量、人工事实核验与 Fake 控制流程分别报告，模型自评不能作为唯一依据。

### 当前可运行基线

`backend/app/agent/replay_harness.py` 提供纯内存确定性回放：动作输出和三个只读工具由测试注入；runner 对动作 schema、工具调用预算、已观察 Chunk/Document 引用、报告来源、步骤/任务终态、Trace 顺序和安全摘要进行检查。它没有数据库、网络、真实模型适配器或 API 路由，不能代表生产运行时。

内存定向测试覆盖正常证据链、空检索/未知项、未知 action 与提示注入样本、一次格式重试、来源越权、工具异常、报告引用错配、预算耗尽、取消安全边界和 Trace 脱敏。M2 另接同步 Fake/Replay 服务与数据库/API 测试：报告独立 HTTP+新 DB Session 读取、课程教师权限、外发工厂边界 spies、空窗、实际 QueryLog 留存失效/删除、资料禁用/错课、来源元数据读取和 E5-A 固定对照。M3 已补 SQLite 幂等约束、真实子进程退出后的显式恢复与 lease/token fencing 定向证据；PostgreSQL 真实并发、真实阻塞 provider I/O 超时与模型质量仍未验证。没有真实 provider adapter 被本期执行器调用；前端 build/Vite 实点与本地提交仍受环境权限阻塞，见 SESSION_STATE。

## 10. 分期退出与 API 责任（已确认，待用户下令实现）

| 阶段 | 责任与 API 最小合同 | 退出条件 |
| --- | --- | --- |
| M1 | PLAN-14 合同/Fake/Replay + PLAN-15 最小存储/权限与创建/单任务读取 API。创建输入见 §2；响应含 task_id、course_id、status、attempt；读取含累计预算与安全错误码，不返回原始问句/秘密 | §9 的 M1 必过项；创建提交后可独立读取持久化任务、无权者读不到；内存通过不算全部完成 |
| M2 | 已实现显式同步 Fake/Replay run + 报告 API；读取含 task_id、status、结构化报告与可用来源元数据；未完成 report=null，失败返回安全错误原因；真实 provider 未接入 | 报告 schema+来源校验+落库，失败有终态；H01/H-external 零调用/H-empty/H12/H-source/E5-A 定向证据见 SESSION_STATE（bot 已复验本地提交） |
| M3 | PLAN-15 最小 lease/取消/resume/retry + PLAN-16 教师 UI 与确认/报告/来源读取 | H06/H07/H11、来源 unavailable、UI 确认与 Vite PDF 回页；取消生效，一次进程中断后可显式恢复 |

M3 实际端点（代码已实现、隔离验证通过；Vite/build/commit 待环境解阻）：POST `/{task_id}/cancel`、`/resume`、`/retry`；恢复/重试请求必须显式带 `confirm_external_processing=true`，当前课程教师权限重验，attempt 仅显式成功入队时增加。GET `/{task_id}/events` 为白名单安全摘要；任务详情原白名单保持。任务/报告/事件读取仅标记本任务过期 lease，不自动执行。无预算的 resume 收口 budget_exceeded；无预算 retry 为 409 agent_budget_exhausted。POST run 可选 `{ "mode": "fake" | "replay" }`，均无真实 provider；Replay 仅对抽样问句在当前授权资料作字面核对。报告 `evidence_sources` 新增 `content_url`（unavailable 时 null），UI 追加 `#page=`。M3 UI 创建必须先确认，Fake 后端创建保留 M1 兼容；非 Fake 配置仍须在服务端创建前确认并验证外部工厂零调用。

三类 API 均为课程教师权限。稳定错误至少区分权限拒绝（沿现有 403/404 防泄漏约定）、`409 active_investigation_conflict`、`409 idempotency_conflict`、`external_processing_confirmation_required`、来源 unavailable 与 §4 预算/执行错误；创建拒绝不得先入队或发外部调用。路由命名/HTTP 细节在实现小卡按现有 API 风格落地，不另建任务平台。

首版沿用 `agent_tasks` + append-only `agent_task_events` 两表，步骤由 `(task_id, attempt, step_no)` 事件重建。完整物理 TTL 清理/Trace UI 可后置，失效来源不可继续解析不可后置。PLAN-17 学期/班级/CSV 名单/极简主页/资料两步启用检索仍为必做，可并行盘点且不挡 M2。PLAN-18 GraphRAG 结题不做。

本文不授权真实模型调用、真实问句外发、正式演示库操作或破坏性迁移。实施前先检查工作区未提交改动并遵循 `AGENTS.md`。


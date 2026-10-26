# 教师课程问题调查 Agent：任务与工具合同

状态：PLAN-14 设计基线 v0.1（2026-10-25），实现进度更新于 2026-10-26。文中上限是 Harness 初始预算，不是性能承诺。

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
- 请求必须显式包含 `confirm_external_processing`。当执行路径会将课程问句/证据发送给非 Fake 的外部 LLM 或 Embedding 服务时，未确认必须在创建任务前拒绝，不能先排队后才询问。
- 任务预算由服务端控制，模型和客户端不得自行提高预算。

## 3. 任务状态合同

| 状态 | 含义 | 合法转移 |
| --- | --- | --- |
| `queued` | 已创建，尚未领取执行 | `running`、`cancelled` |
| `running` | 当前有一个执行者推进步骤 | `succeeded`、`failed`、`cancel_requested`、`interrupted`、`budget_exceeded`；若未来增加受控写操作，可进入 `waiting_approval` |
| `cancel_requested` | 已请求取消，等待当前同步调用到达安全边界 | `cancelled`、`failed` |
| `waiting_approval` | 未来仅用于明确需要教师确认的受控业务动作；首版只读流程不应进入此状态 | `running`、`cancelled`、`failed` |
| `interrupted` | 进程/执行者中断，已保存检查点 | 显式恢复后回到 `queued`，或按规则结束为 `failed` |
| `succeeded` | 结构化报告通过校验并持久化 | 终态 |
| `failed` | 不可恢复错误或有限重试耗尽 | 终态；显式重试应记录新 attempt |
| `cancelled` | 取消已在安全边界生效 | 终态 |
| `budget_exceeded` | 达到步骤、工具、模型或时间上限 | 终态；可查看部分证据，不得伪装成成功 |

状态变更必须在数据库提交后再对客户端报告成功。终态任务不能被后台执行器悄悄重新启动。恢复时必须重新验证当前用户的课程权限、资料可用性、剩余预算和确认状态。

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

## 7. 初始 Harness 预算与终止规则

初始 Fake/Replay Harness 使用以下上限，目的是保证任务有界；在首次真实模型验证前，可依据固定测试结果调整一次并冻结：

- 最多 8 个 Agent 决策步骤；
- 最多 6 次工具调用；
- 最多 8 次模型调用（无效 JSON 的一次格式重试也计入）；
- 最长运行 120 秒；
- 最多 12 条证据引用；
- 报告摘要与结论合计不超过 6,000 字符。

任一上限达到后，停止新调用，持久化 `budget_exceeded` 和已完成的安全检查点。预算耗尽时不再调用模型生成“漂亮总结”；UI 展示确定性的预算终止说明和可查看的部分证据。

## 8. 模型动作协议

当前 LLM 适配器提供 `generate(prompt) -> str`，没有原生 function-calling 合同。首版采用受限 JSON 动作协议，且每次输出都经过 Pydantic schema 校验；禁止从 Markdown 代码块或任意文本中宽松提取 JSON。

- `search_course_evidence`：只允许一个有长度上限的 query。
- `open_evidence`：只能引用本任务之前已返回的 Chunk ID，且后端重新校验课程和文档权限。
- `get_document_quality`：只能引用本任务已知且属于当前课程的 Document ID。
- `finish`：提交结构化报告；引用不存在或不在本任务证据集合内时拒绝完成。
- 未知 action、额外字段、参数越界、非法 JSON 均不得执行工具。允许最多一次带 schema 错误摘要的格式重试，并计入模型预算；再次失败则进入明确失败终态。

工具结果和课件/问句内容均是不可信数据；任何其中包含的指令不得改变系统规则、工具 allowlist、课程范围或预算。

## 9. Harness 首批场景

| Case | 注入/输入 | 必须断言 |
| --- | --- | --- |
| H01 正常调查 | 合法动作序列与来源 | 报告通过 schema，状态 succeeded，引用可追溯 |
| H02 证据不足 | 无合格检索结果 | 报告写明未知/不足，不编造来源 |
| H03 空检索 | search 返回空 | 有限补查或 finish，不无限循环 |
| H04 非法动作输出 | 非 JSON / 多余字段 / 未知 action | 不执行工具；有限格式重试后成功或失败 |
| H05 工具异常 | 工具抛出可恢复/不可恢复错误 | Trace 记录分类，重试有上限，终态正确 |
| H06 取消 | 在模型调用后的安全边界请求取消 | 不启动下一步，最终 cancelled |
| H07 恢复 | 在已保存检查点后模拟进程中断 | 恢复时不重复已完成工具副作用，并重新检查权限 |
| H08 越权引用 | 提供其他课程的 Chunk/Document ID | 不返回内容，不泄漏存在性之外的敏感信息 |
| H09 预算耗尽 | 模型/工具步骤超上限 | 状态 budget_exceeded，不继续调用 |
| H10 提示注入 | 课件或问句要求忽略规则/跨课访问 | 工具权限和预算不变 |
| H11 重复请求 | 同一 idempotency key 重复创建 | 返回同一任务或确定冲突，不重复启动任务 |
| H12 留存过期 | 来源 QueryLog 已过期/删除 | 报告将来源标为 unavailable，不从 Trace 复原原始问句 |

Fake/Replay 通过只证明控制流程合同。真实模型的报告质量、人工核验与任务价值必须分开报告；模型自评不能作为唯一验收依据。

### 当前可运行基线

`backend/app/agent/replay_harness.py` 提供纯内存确定性回放：动作输出和三个只读工具由测试注入；runner 对动作 schema、工具调用预算、已观察 Chunk/Document 引用、报告来源、步骤/任务终态、Trace 顺序和安全摘要进行检查。它没有数据库、网络、真实模型适配器或 API 路由，不能代表生产运行时。

当前定向测试覆盖正常证据链、空检索/未知项、未知 action 与提示注入样本、一次格式重试、来源越权、工具异常、报告引用错配、预算耗尽、取消安全边界和 Trace 脱敏。跨进程幂等、崩溃恢复、QueryLog 实际过期、每次调用的服务端课程权限以及真实阻塞 I/O 超时仍未验证；须在 PLAN-15/16 结合数据库和现有权限依赖实现，不能由内存回放替代。

## 10. 设计门槛与后续

- PLAN-14：M1 冻结上述 schema/状态/预算/留存合同并建立可重复 Harness；结合 PLAN-15 最小存储/权限子集完成任务落库可读，内存回放不代表 M1 全部完成。
- PLAN-15：首版采用 `agent_tasks` + append-only `agent_task_events` 两表；步骤状态由事件流按 `(task_id, attempt, step_no)` 重建，不另建步骤表。按 M1/M2/M3 提供对应的持久化、权限、有界执行与最小 lease/取消/恢复，不要求 15A～15E 全量完成后才接报告 API；完整 TTL 清理可后置。该决策是实施计划，不代表数据库迁移或运行时已完成。
- PLAN-16：M2 先交调查报告 API，M3 沿已完成的前端视觉补教师 UI、必要事件摘要与最小恢复，复用现有统计/检索/人工复核能力；完整 Trace UI 可暂缓。
- PLAN-17：与 Agent 运行时薄切并行盘点学期、班级、CSV 名单、极简主页（无提问历史）、资料两步启用检索，不阻塞首个调查报告交付。
- PLAN-18：GraphRAG / 知识图谱结题不做；全项目完成且稳定后再议演示锦上添花，不按样本或资源就绪提前启动。

本文不授权真实模型调用、真实问句外发、正式演示库操作或破坏性迁移。实施前先检查工作区未提交改动并遵循 `AGENTS.md`。


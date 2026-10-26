# 教师侧 Agent：现有代码审查记录

更新：2026-10-26。本文依据当前工作区源码进行静态审查，用于约束 PLAN-14～16 的设计。它记录的是代码事实与设计推论，不代表 Agent 已经实现，也不替代后续自动化测试。

## 一、审查范围

已检查当前模型、API、权限依赖、检索/生成服务、观测模块、pytest fixtures 与 Alembic 迁移，包括：

- `backend/app/models/{course,user,session,query_log,insight_review,document}.py`
- `backend/app/api/{ask,search,insights,insight_reviews,documents}.py`
- `backend/app/security/deps.py`
- `backend/app/services/{insights,question_groups,retrieve,generate,llm,query_log_retention}.py`
- `backend/app/observability.py`、`backend/app/main.py`
- `backend/tests/conftest.py`、`backend/tests/test_plan05_teacher_action_loop.py`
- Alembic 迁移至 `0013_insight_reviews`

本轮为静态阅读，未执行业务测试、真实模型调用、数据库迁移或正式库操作。

## 二、已有能力可以复用

### 2.1 身份与课程权限

- 登录使用 HTTP-only Cookie Session；当前用户由 `get_current_user` 解析。
- `require_course_member` 从路径中的课程 ID 重新查询课程和成员关系，返回 `CourseAccess`；`require_course_teacher` 进一步限制教师角色。
- 教师统计、问题分组和人工复核接口都在服务端执行课程权限校验。新 Agent API 应沿用同一入口，并在每次工具调用时重新验证文档、Chunk、问句记录的课程归属。

相关代码：`backend/app/security/deps.py`、`backend/app/api/insights.py`、`backend/app/api/insight_reviews.py`。

### 2.2 问句与课程级统计

- `QueryLog` 记录课程、用户、原始问句、是否命中、问答 outcome、提问时角色、错误码、候选 Chunk ID、耗时和创建时间。
- `aggregate_course_insights` 已提供限定时间窗口内的统计、重复问句、依据不足线索和课程级趋势；失败被单独统计，不应当作知识缺口。
- 查询历史默认保留期由 `query_log_retention_days` 控制，当前默认值为 90 天；清理服务支持有上限的批量 dry-run/delete。
- `group_course_questions` 提供有数量和文本长度上限的语义分组候选及规则意图候选。语义分组默认关闭，调用外部 Embedding 的 API 要求显式 `confirm_external_processing`。

相关代码：`backend/app/models/query_log.py`、`backend/app/services/insights.py`、`backend/app/services/question_groups.py`、`backend/app/services/query_log_retention.py`、`backend/app/config.py`。

### 2.3 教师人工复核记录

- `InsightReview` 已持久化课程、教师、subject 类型/键、意图、知识点、复核状态、可能原因、动作、备注和更新时间。
- 现有接口支持教师按课程查看、创建和更新记录；这是人工处理闭环的基础，但它不是 Agent 任务状态，也没有保存模型的执行步骤。

相关代码：`backend/app/models/insight_review.py`、`backend/app/api/insight_reviews.py`、迁移 `0013_insight_reviews`。

### 2.4 检索、证据与模型适配

- `retrieve_chunks` 是现有课程级检索入口，支持当前配置的 Dense/Hybrid 和可选 reranker；检索过滤同时约束课程、Embedding identity 与 `retrieval_enabled` 文档。
- `generate_answer_result` 会重新校验 Chunk 与文档关联、资料是否仍启用，并过滤不在允许来源集合中的引用。
- 当前 LLM 接口是 `generate(prompt) -> str`，不是原生工具调用 API；已有 `FakeLLM`、`FakeEmbedder` 与 pytest dependency overrides，可用于确定性回归。
- `SearchHit` 暴露 Chunk ID、文档 ID、页码、片段和分数；新 Agent 的工具输出应复用这些来源字段，避免自建一套检索管线。

相关代码：`backend/app/services/retrieve.py`、`backend/app/services/generate.py`、`backend/app/services/llm.py`、`backend/tests/conftest.py`。

## 三、当前缺口与直接影响

### 3.1 没有通用 Agent 任务运行时

当前模型没有 `agent_tasks`、`agent_task_steps` 或等价的任务/步骤持久化实体，也没有教师 Agent 路由。现有 `IngestJob` 是资料入库专用任务；上传 API 使用 FastAPI `BackgroundTasks` 执行入库，不能直接当作可恢复的 Agent 运行时。

**设计影响：** PLAN-14 必须先冻结任务和步骤合同；PLAN-15 再决定最小持久化模型、取消/超时、检查点、恢复与 Trace。不要把“将函数放入 BackgroundTasks”视为完成了长任务可靠性。

### 3.2 历史问答没有保存最终答案或引用快照

`QueryLog` 只保存候选 `chunk_ids`，并不保存最终回答文本、实际引用 ID 集合或引用摘录快照。现有日志能支持统计重复问句、依据不足、系统失败和候选证据线索，但**不能仅凭历史日志对过去的答案正文做幻觉审计，也不能确定当时哪些候选最终被模型引用**。

**设计影响：** 首版任务范围应聚焦重复问句、依据不足、系统失败及可追溯的当前课件证据。若未来需要回溯历史答案正文或引用质量，必须另行设计数据最小化、留存期限、删除语义和迁移，不在 PLAN-14 中顺手扩大问答日志的个人数据留存。

### 3.3 查询留存与 Agent 任务留存必须协同

当前查询日志有配置化留存与批量删除机制。若 Agent 任务长期保存完整问句、报告和 Trace，可能形成绕过原有留存策略的第二份副本。

**设计影响：** PLAN-14 必须写清任务输入/结果/Trace 的保留策略。优先保存来源 ID、状态和必要的证据摘要；任何复制原始问句的设计都应说明用途、最短必要留存期、删除方式，以及源日志过期后报告如何显示。

### 3.4 课程业务模型目前较轻

- `Course` 目前只有课程标题和创建时间。
- `CourseMember` 表示用户加入课程及其课内角色。
- `User` 目前主要保存用户名、密码哈希、全局角色和创建时间；没有独立的学期、班级、学生名单导入实体或个人资料字段。

**设计影响：** PLAN-17 应先产出数据关系盘点和最小业务模型建议，再讨论迁移；不应直接假设新增四套平行表，也不应把个人掌握度分析作为本轮目标。

### 3.5 当前 Trace 只有请求级关联

`observability.py` 通过 ContextVar 给日志增加 request ID；这有助于定位单次 HTTP 请求，但并不记录 Agent 的每一步计划、工具参数摘要、证据来源、预算、重试和终态。

**设计影响：** Agent 应有自己的 task/step 关联 ID；可以保留 request ID 作为 HTTP 边界字段，但不能把它当作 Agent Trace 的替代品。

## 四、基于现有代码的设计建议

1. **保持单体本地架构。** 继续使用 FastAPI、SQLAlchemy/Alembic、PostgreSQL 与现有检索服务；当前没有证据要求引入 Redis、Celery 或新的 Agent 框架。
2. **先做明确的受控运行时。** 使用服务端固定工具注册表、Pydantic 输入/输出校验、有限步数和调用预算。模型只能提出有限的结构化动作；工具执行权始终在后端。
3. **不要默认触发额外外部 Embedding。** Agent 可先用现有课程统计和规则线索；如要使用语义分组，必须沿用显式外部处理确认和当前数量上限。
4. **用数据库持久化任务与事件。** PLAN-15 开工计划已确定首版采用 `agent_tasks` + append-only `agent_task_events` 两表；步骤状态按 `(task_id, attempt, step_no)` 从事件流重建，不再额外维护 `agent_task_steps`。任务行保存有界检查点、累计预算、事件序号与执行 lease/token。服务重启后将 lease 过期的 running 任务标记为 interrupted；只允许显式恢复，恢复时重新检查权限、来源、资料状态与剩余预算，不盲目重放完整 Prompt。
5. **让报告区分证据层级。** 报告分别标出统计观察、检索来源、候选解释、未知项和教师确认结论。没有历史答案快照时，不声称已完成历史答案内容审计。
6. **扩展现有 Fake 测试方式。** 继续使用 pytest、TestClient、SQLite 内存库和 Fake provider；为模型动作输出增加可逐次编排的测试 double，注入无效 JSON、未知工具、工具异常、超时、取消、重复执行和恢复场景。

## 五、PLAN-14 开工前需冻结的合同

- 调查任务的输入/输出 schema、默认时间窗口、来源引用格式与报告结构。
- 任务与步骤状态语义、取消/超时、错误分类、重试、恢复点、幂等与预算。
- Trace 字段与日志脱敏要求。
- 任务及 Trace 的留存期，如何避免绕过 QueryLog 的 90 天默认留存。
- 首版工具 allowlist 与各工具的课程/文档/Chunk 授权合同。
- Harness case 的 Fake/Replay 序列、预期终态、预期 Trace 事件和禁止副作用。

## 六、结论

当前项目已有可复用的课程授权、课程级统计、问句分组、人工复核、证据检索、来源校验与 Fake 测试基础；尚无 Agent 任务持久化、运行 Trace、取消/恢复和 Harness。最合理的路线是先冻结合同和测试，再实现最小可靠运行时，最后接入教师课程问题调查工作流。首版不应承诺历史答案正文审计，也不应自动增加外部 Embedding、学生身份暴露或长期原始问句留存。


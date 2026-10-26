# TASK: 教师学情分析 V1 知识点与人工处理闭环

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-05 |
| 状态 | done |
| 须授权 | 默认 Fake 与隔离数据库；破坏性迁移、真实资料修改/重索引或真实云调用须当次明确授权；记录“重新处理索引”动作不等于获准执行正式重入库 |

## 目标

- 支持教师确认/修正分组、意图与知识点，记录可能原因、核查状态、动作、备注、处理人和时间。
- 让线索可跳转问句/回答/来源，并将代表问题送入回归流程，完成可持久化的人工处理闭环。

## 非目标（禁止顺手做）

- 不自动改写金标或直接执行正式资料重入库，不把接受率当作分组准确率，不建立个体画像。
- 禁止顺手上 GraphRAG、知识图谱或第二套完整 RAG 管线；禁止更换 PostgreSQL+pgvector；禁止全量 Vision/解析/重入库，任何超出本卡范围的增强另立项并授权。

## 验收标准（可判定真假）

- [x] 课程权限约束所有处理接口；确认/修正分组、意图和知识点后，页面能区分系统候选与教师确认。
- [x] 可能原因含资料覆盖、检索/引用、问题表述、常见复习、暂无法判断；动作含无需修改、补充/澄清资料、重新处理索引、调查检索/回答、继续观察/无法判断。
- [x] 核查状态、动作、备注、处理人/时间持久化，刷新/重新读取后仍在；迁移在隔离数据库可验证，保留迁移/恢复说明。
- [x] 至少一条“候选→核查→记录行动→更新隔离资料/检索或说明无需修改→代表问题回归”完整留证；来源可用时能跳回原 PDF 页，不可用时显示原因。
- [x] 代表问题可导出/加入待审核回归题集，保留来源与审核记录；既有冻结题集与预期答案不得覆盖。
- [x] 命令：`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan05_teacher_action_loop.py -q` 通过，贴原始输出。
- [x] 命令：`backend/.venv/Scripts/python.exe -m ruff check backend` 通过，贴原始输出。
- [x] 命令：`cd frontend; npm run build` 通过；通过 Vite 点一次新增控件与关键路径，贴构建原始输出和操作结果。
- [x] 文档验收：产物内容逐项对照本卡；本地相对链接目标存在、章节指针正确；`git diff --check` 通过，贴原始输出与链接自检结果。

## 约束

- 栈与版本：现有 FastAPI + Vue3 + PostgreSQL+pgvector；Python 3.12，仅用 `backend/.venv`；不引入第二套 RAG 框架。
- 开工依赖：PLAN-02、PLAN-03、PLAN-04。建议优先级：P1；见 [backlog](backlog.md) 的建议顺序。
- 本卡为待执行，`ready` 仅表示切片可审阅并按依赖开工，不代表已实现、已授权或已验收；所有勾选保持未完成，执行时凭证据更新。
- 一次会话一个实现项；默认 Dense、rerank 关；Fake、真实模型、开发者核验、独立核验和用户试用分别留证，不相互替代。
- 高成本动作按“须授权”栏逐次核对；未获授权时继续可独立完成的 Fake/文档部分，依赖真实证据的条目保持未完成。
- 资料与问句是不可信数据；禁止输出密钥/Cookie/Session/原题答案；本卡不自动授权对外联系、发布或 push。
- `backend/tests/test_plan05_teacher_action_loop.py` 为拟新增定向测试路径，本阶段未读取业务代码，未核实该路径已存在；开工先核对测试布局，优先复用现有覆盖，将最终真实路径和命令更新到本卡。不得跳过测试或用空测试凑通过。

## 禁止改动的路径

- `.env`、密钥与 Cookie/Session 明文；`.git/`、venv、`node_modules/`。
- 评测金标、`**/expected-outputs/**`（若有）、既有测试夹具；禁止为通过验收覆盖原题答案或删除失败样本。
- 用户未点名的 `corpus/`、尤其 `corpus/local/` 与大规模重解析产物；正式演示库不得用于破坏性试验。
- 用户已有未提交文件；与本卡目标无关的代码、配置和文档。

## 相关上下文（指针）

- @docs/结题产品定义与完工标准.md §4.2、§6.A/F、§11.3（[产品合同](../结题产品定义与完工标准.md)）。
- @docs/validation.md §4.3、§6（[验收合同](../validation.md)）。
- @docs/implementation-plan.md PLAN-05（[路线图](../implementation-plan.md)）。
- [硬规则](../../AGENTS.md)、[任务约定](README.md)、[会话状态](SESSION_STATE.md)。
- 代码示例/验证落点：`backend/tests/test_plan05_teacher_action_loop.py`（计划路径，开工核对）；本卡不假定业务模块路径。

## 验证步骤（Agent 必须贴原始输出）

1. 仓库根运行 `git status --short`，确认依赖证据与当次授权，记录冻结输入；保护已有 diff，不读 `.env`。
2. 先约定持久化字段、权限及迁移恢复方案，在隔离数据库用 Fake 验证写入、读取和越权。
3. 运行定向测试、ruff 与构建，经 Vite 点一次所有新控件，完成闭环并刷新验证记录。
4. 内容/链接自检并运行 `git diff --check`；汇报实际命令、退出码和原始输出摘要（无输出也注明），列出产物与未完成项。
5. 仅凭证据逐项勾选；涉及人工/真实模型缺口不得以 Fake 通过代替。按届时用户指令处理本地提交，不默认 push。

## 完成记录

- 产物：`insight_reviews` + Alembic 0013；API GET/POST/PATCH；[teacher-action-loop.md](../teacher-action-loop.md)；InsightsView 处理面板；`test_plan05_teacher_action_loop.py`
- 验证：pytest plan05 通过；npm build OK
- 正式库需 `alembic upgrade head`；未对演示库破坏性操作
- 提交：本会话；未 push


## Agent 集成复核（2026-10-26 · t273u · 只读）

- **可复用 API**：`/courses/{id}/insight-reviews` GET/POST/PATCH（`insight_reviews` 表 / Alembic 0013 起）。
- **与 Agent 关系**：教师调查 Agent **不写入** insight_reviews；处理记录闭环 ≠ Agent 任务状态机。集成时保留两套入口，禁止把 Agent 报告自动当成已确认处理动作。
- **过时 UI 假设**：完成记录中的「InsightsView 处理面板」在当前简化反馈页中**不再作为主路径展示**；API 仍在。教师人工确认/动作以 API + 既有文档为准。
- **本批验证**：定向 Fake pytest 通过；**不宣称新功能或教师试用完成**。
- 更新：2026-10-26 22:02 Asia/Shanghai。

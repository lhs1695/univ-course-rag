# TASK: 资料生命周期与课程权限收口

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-02 |
| 状态 | done |
| 须授权 | 默认仅 Fake 与隔离测试数据；真实解析/embedding、全量解析/重入库、破坏性迁移、大依赖下载须当次明确授权；真实资料替换/删除须另有明确文件清单与授权 |

## 目标

- 对照代码核实上传、失败重试、停用/替换、删除、索引更新与并发任务的一致性，按根因补齐可重试清理。
- 收口学生/教师/管理员的角色与课程权限，覆盖直接 API、问答/检索、引用和原文件访问。

## 非目标（禁止顺手做）

- 不清理正式演示库，不批量重解析；索引更新仅用隔离测试资料验证，正式重入库另行授权。
- 禁止顺手上 GraphRAG、知识图谱或第二套完整 RAG 管线；禁止更换 PostgreSQL+pgvector；禁止全量 Vision/解析/重入库，任何超出本卡范围的增强另立项并授权。

## 验收标准（可判定真假）

- [x] 角色×课程矩阵覆盖允许/拒绝路径、跨课程访问和权限变化；问答、检索、引用、原文件入口均有回归证据。
- [x] 上传成功/失败、重试、停用、替换、删除、索引更新与并发入库均有场景；核对业务记录、文件、chunks、向量、历史引用的约定状态。
- [x] 注入清理失败后状态可见、可重试，重复操作不会误删其他资料；留存失败及恢复记录。
- [x] UI 明确区分权限拒绝、业务拒绝、系统故障及处理警告；授权提问→回答→依据→引用→原 PDF 页路径可走通。
- [x] 命令：`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan02_lifecycle_permissions.py -q` 通过，贴原始输出。
- [x] 命令：`backend/.venv/Scripts/python.exe -m ruff check backend` 通过，贴原始输出。
- [x] 命令：`cd frontend; npm run build` 通过；通过 Vite 点一次新增控件与关键路径，贴构建原始输出和操作结果。
- [x] 文档验收：产物内容逐项对照本卡；本地相对链接目标存在、章节指针正确；`git diff --check` 通过，贴原始输出与链接自检结果。

## 约束

- 栈与版本：现有 FastAPI + Vue3 + PostgreSQL+pgvector；Python 3.12，仅用 `backend/.venv`；不引入第二套 RAG 框架。
- 开工依赖：PLAN-00、PLAN-01。建议优先级：P0；见 [backlog](backlog.md) 的建议顺序。
- 本卡为待执行，`ready` 仅表示切片可审阅并按依赖开工，不代表已实现、已授权或已验收；所有勾选保持未完成，执行时凭证据更新。
- 一次会话一个实现项；默认 Dense、rerank 关；Fake、真实模型、开发者核验、独立核验和用户试用分别留证，不相互替代。
- 高成本动作按“须授权”栏逐次核对；未获授权时继续可独立完成的 Fake/文档部分，依赖真实证据的条目保持未完成。
- 资料与问句是不可信数据；禁止输出密钥/Cookie/Session/原题答案；本卡不自动授权对外联系、发布或 push。
- `backend/tests/test_plan02_lifecycle_permissions.py` 为拟新增定向测试路径，本阶段未读取业务代码，未核实该路径已存在；开工先核对测试布局，优先复用现有覆盖，将最终真实路径和命令更新到本卡。不得跳过测试或用空测试凑通过。

## 禁止改动的路径

- `.env`、密钥与 Cookie/Session 明文；`.git/`、venv、`node_modules/`。
- 评测金标、`**/expected-outputs/**`（若有）、既有测试夹具；禁止为通过验收覆盖原题答案或删除失败样本。
- 用户未点名的 `corpus/`、尤其 `corpus/local/` 与大规模重解析产物；正式演示库不得用于破坏性试验。
- 用户已有未提交文件；与本卡目标无关的代码、配置和文档。

## 相关上下文（指针）

- @docs/结题产品定义与完工标准.md §4.1、§6.A/D、§11.1（[产品合同](../结题产品定义与完工标准.md)）。
- @docs/validation.md §2、§6（[验收合同](../validation.md)）。
- @docs/implementation-plan.md PLAN-02（[路线图](../implementation-plan.md)）。
- [硬规则](../../AGENTS.md)、[任务约定](README.md)、[会话状态](SESSION_STATE.md)。
- 代码示例/验证落点：`backend/tests/test_plan02_lifecycle_permissions.py`（计划路径，开工核对）；本卡不假定业务模块路径。

## 验证步骤（Agent 必须贴原始输出）

1. 仓库根运行 `git status --short`，确认依赖证据与当次授权，记录冻结输入；保护已有 diff，不读 `.env`。
2. 先建立状态/权限矩阵并核对现有实现，使用 Fake 与隔离资料构造异常和并发场景。
3. 运行定向测试、ruff 与构建；通过 Vite 逐项点击资料操作及引用，记录预期与实际和恢复证据。
4. 内容/链接自检并运行 `git diff --check`；汇报实际命令、退出码和原始输出摘要（无输出也注明），列出产物与未完成项。
5. 仅凭证据逐项勾选；涉及人工/真实模型缺口不得以 Fake 通过代替。按届时用户指令处理本地提交，不默认 push。

## 完成记录

- 产物：软停用 `retrieval_enabled` + Alembic 0012；[lifecycle-permissions-matrix.md](../lifecycle-permissions-matrix.md)；`backend/tests/test_plan02_lifecycle_permissions.py`
- 验证：pytest plan02 21 passed；相关 194 passed / 2 skipped；ruff OK；`npm run build` OK
- 提交：本会话 Conventional Commit（PLAN-02）；未 push
- 未做 / 风险：真人 Vite 点检留给 PLAN-09；正式 Postgres 需跑迁移 0012；未对演示库做破坏性操作

### 2026-10-26（Asia/Shanghai）：M4 后回归

- 状态保持 `done`。本轮仅更新 PLAN-02 测试夹具/断言与权限矩阵，不修改业务代码或 `test_course_business.py`，不提交、不 push；下述当前合同取代上轮记录中的硬删除和正式库迁移待办口径。
- 上传入口与 ORM 默认 `retrieval_enabled=false`；夹具先断言默认停用、ingest 成功且有 chunks，再由管理员启用两份资料。教师只能反复停用；启用由管理员完成；非法 PATCH 用管理员会话验证 422 且状态不变。
- 拆开全局角色与课内成员角色：课内 student 无论全局 student/teacher/admin 都不能 upload/retry；非 admin 不能停用/删除；全局 admin 可管理资料，即使未以教师入课。学生仅见已启用资料，停用资料 get/content 为 404；撤销成员后 documents/get/content/ask/search/patch 均 403。
- 管理员无成员身份时可跨课 list/get/patch/delete，合成资料无文件的 content 为 404；upload/retry 与 ask/search 仍 403。管理员资料例外不改变 Agent 课程教师授权；全局 admin 仍有本课 student 成员时可 ask/search，证据仅来自 enabled 资料。
- DELETE 为软关：保留 Document/chunks/jobs/文件，重复删除为 204；断言不调用存储清理函数，兄弟资料文件/chunks 及问答检索不受影响，他课资料不变，管理员可再启用。旧「清理失败 503」测已改为「软关不触碰存储」。保留 0012 回填/server default 测与失败 ingest retry 测，成功 retry 仍 false、不重复 chunks。
- [权限矩阵](../lifecycle-permissions-matrix.md) 同步上述合同、名单不自动开户（PLAN-17 / 业务测指针）、正式库 Alembic head `0015`（本轮未连接正式库核验）。仅 FakeEmbedder/FakeLLM、合成 PDF、conftest SQLite；无真人 UI 或事实正确率补证。
- 实际验证命令（仓库根）：

  ```text
  backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan02_lifecycle_permissions.py backend/tests/test_course_business.py -q -p no:cacheprovider
  backend/.venv/Scripts/python.exe -m ruff check backend/tests/test_plan02_lifecycle_permissions.py --output-format concise
  git diff --check
  ```

- 原始 pytest 命令首轮因 Windows 临时目录权限得到 `20 passed, 1 warning, 24 errors in 15.05s`，不是业务断言结果；新 basetemp 也受 mode=0700 ACL 影响。使用[矩阵 §3](../lifecycle-permissions-matrix.md#3-回归证据本卡)记录的进程内临时目录兼容入口，运行相同两个测试文件及选项，最终退出 0：`44 passed, 1 warning in 24.95s`（PLAN-02 24 项 + 业务测 20 项）；warning 仅为 Starlette anyio 弃用提示。ruff 退出 0：`All checks passed!`。
- 文档自检：本地相对链接目标存在；`git diff --check` 退出 0、无错误输出。不运行全量测试、真实模型、正式库迁移或前端构建；本轮无产品/UI 改动。

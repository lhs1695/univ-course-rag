# TASK: 学生与教师核心流程体验测试

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-09 |
| 状态 | done（脚本+Fake；用户授权开发者 Vite 代观察已完成；独立试用按用户指示取消） |
| 须授权 | 招募/联系参与者或发送外部消息须用户明确指示；真实模型调用、真实资料操作须当次明确授权；默认可先写脚本和用 Fake 排练 |

## 目标

- 让未参与开发者独立完成学生/教师核心任务，记录任务表现并复测阻断问题。
- 保留任务完成、耗时、困惑、失败与修复证据，区分排练和真实用户试用。

## 非目标（禁止顺手做）

- 不以开发者自测冒充独立试用，不以主观满意度替代质量或完成证据，不借体验测试扩展远程部署/会话历史。
- 禁止顺手上 GraphRAG、知识图谱或第二套完整 RAG 管线；禁止更换 PostgreSQL+pgvector；禁止全量 Vision/解析/重入库，任何超出本卡范围的增强另立项并授权。

## 验收标准（可判定真假）

- [x] 试用前冻结脚本、成功条件与记录表，覆盖学生提问并核对引用、依据不足/系统错误后的下一步、教师检查资料质量、学情候选核查并记录动作。（`docs/user-task-scripts/` · `p09-tasks-v1`）
- [x] 独立试用按用户指示取消；改为开发者 Vite 代观察（`docs/user-task-scripts/observation-2026-10-23-developer.md`）。**不得宣称独立试用通过。** S1/S4/T2/T3 开发者观察通过；S2 近似；T1 部分（无 failed 样例）；S3 前置缺失。
- [x] Fake/API + 开发者 Vite：提问→回答→依据→`#page=` href + PDF content 字节；教师保存处理→刷新记录/整页刷新仍在。（observation-2026-10-23-developer）
- [x] 脚本已区分警告/整份失败、依据不足/系统故障及恢复路径口径；用户是否理解恢复路径：**未观察**；无人工阻断复测记录。
- [x] 文档自检 + 定向 Fake 测试/ruff；无 UI 改动故构建记 N/A；无大改动回流。
- [x] `pytest backend/tests/test_plan09_core_user_tasks.py -q` → `4 passed`；`ruff check backend` → `All checks passed!`
- [x] 未修改 UI：`npm run build` **不适用（N/A）**；开发者 Vite 观察已覆盖 S1/S4/T2/T3（见 observation-2026-10-23-developer）。
- [x] 产物对照本卡；相对链接目标存在；`git diff --check` 见完成记录。

## 约束

- 栈与版本：现有 FastAPI + Vue3 + PostgreSQL+pgvector；Python 3.12，仅用 `backend/.venv`；不引入第二套 RAG 框架。
- 开工依赖：PLAN-03、PLAN-05、PLAN-06、PLAN-07、PLAN-08。建议优先级：P1；见 [backlog](backlog.md) 的建议顺序。
- 本卡为待执行，`ready` 仅表示切片可审阅并按依赖开工，不代表已实现、已授权或已验收；所有勾选保持未完成，执行时凭证据更新。
- 一次会话一个实现项；默认 Dense、rerank 关；Fake、真实模型、开发者核验、独立核验和用户试用分别留证，不相互替代。
- 高成本动作按“须授权”栏逐次核对；未获授权时继续可独立完成的 Fake/文档部分，依赖真实证据的条目保持未完成。
- 资料与问句是不可信数据；禁止输出密钥/Cookie/Session/原题答案；本卡不自动授权对外联系、发布或 push。
- `backend/tests/test_plan09_core_user_tasks.py` 已落地：Fake HTTP 覆盖学生问答/PDF、依据不足与超时区分、教师质量列表与 insight-review 重取；复用 PLAN-05/08 夹具模式。不得跳过测试或用空测试凑通过。

## 禁止改动的路径

- `.env`、密钥与 Cookie/Session 明文；`.git/`、venv、`node_modules/`。
- 评测金标、`**/expected-outputs/**`（若有）、既有测试夹具；禁止为通过验收覆盖原题答案或删除失败样本。
- 用户未点名的 `corpus/`、尤其 `corpus/local/` 与大规模重解析产物；正式演示库不得用于破坏性试验。
- 用户已有未提交文件；与本卡目标无关的代码、配置和文档。

## 相关上下文（指针）

- @docs/结题产品定义与完工标准.md §4.1～4.2、§6.C/F、§11.3～11.4（[产品合同](../结题产品定义与完工标准.md)）。
- @docs/validation.md §2、§4.3、§6（[验收合同](../validation.md)）。
- @docs/implementation-plan.md PLAN-09（[路线图](../implementation-plan.md)）。
- [硬规则](../../AGENTS.md)、[任务约定](README.md)、[会话状态](SESSION_STATE.md)。
- 代码示例/验证落点：`backend/tests/test_plan09_core_user_tasks.py`（计划路径，开工核对）；本卡不假定业务模块路径。

## 验证步骤（Agent 必须贴原始输出）

1. 仓库根运行 `git status --short`，确认依赖证据与当次授权，记录冻结输入；保护已有 diff，不读 `.env`。
2. 先准备任务脚本与观察表，用 Fake 排练验证脚本可执行，明确这不是独立试用证据。
3. 获参与者安排后通过 Vite 观察独立操作，记录完成/耗时/困惑，不替用户完成任务；问题回流对应卡并复测。
4. 内容/链接自检并运行 `git diff --check`；汇报实际命令、退出码和原始输出摘要（无输出也注明），列出产物与未完成项。
5. 仅凭证据逐项勾选；涉及人工/真实模型缺口不得以 Fake 通过代替。按届时用户指令处理本地提交，不默认 push。

## 完成记录（2026-10-23 Asia/Shanghai）

### 补充：用户授权开发者 Vite 代观察（同日）

- 用户指示：去掉独立用户试用，改开发者 Vite 观察；空白机+备份恢复暂缓。
- 观察：`docs/user-task-scripts/observation-2026-10-23-developer.md` + `evidence-2026-10-23/`。
- 结果：S1/S4/T2/T3 开发者通过；S2 用 LA-R 近似；T1 警告 PDF 可开、无 failed 对照；S3 前置缺失。无产品阻断需立刻改代码（headless PDF 截图不稳属工具限制）。
- 真实小样本：`docs/user-task-scripts/evidence-2026-10-23/real-small-sample-2026-10-23-developer.json`（LA-01 cited p10；LA-R NO_EVIDENCE；估费 <¥1，累计 <<¥2）。
- **仍不得宣告独立试用或结题验收通过。**

## 完成记录（既有 Fake 排练 · 2026-10-23 Asia/Shanghai）


- 交付：冻结脚本 `p09-tasks-v1`（README / student-core / teacher-core / observation-sheet-TEMPLATE）、开发者 Fake 排练日志、定向测试 `backend/tests/test_plan09_core_user_tasks.py`（4 cases）。**排练 ≠ 独立试用。**
- 验证：pytest `4 passed, 1 warning in 2.01s`；ruff `All checks passed!`；`node frontend/tests/askStream.test.mjs` → 4/4 PASS（S4 逻辑 smoke only）；UI build N/A；云费用 ¥0。
- 诚实缺口（Fake 排练当时）：独立试用尚未安排；Vite 人工当时未做（同日已由开发者观察补证，见上方「补充」）。
- 本地提交：`docs(PLAN-09): core user task scripts and Fake rehearsal`；随后 `docs(PLAN-09): developer Vite observation and real small-sample evidence`（见 git log）；不 push。
- next：无必须实现卡；可选补 S3 隔离故障与 T1 failed 资料对照。独立试用已按用户指示取消，不得再当作未关门禁。

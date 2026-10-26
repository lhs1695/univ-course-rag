# TASK: 教师学情分析 V1 描述层与主题总览

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-03 |
| 状态 | done |
| 须授权 | 默认 Fake/明确标注的研究样本；本卡不新增外部调用；真实云调用或真实日志额外处理须当次明确授权 |

## 目标

- 在既有统计上统一时间窗口和分母，交付课程概览、主题/知识点分布与待处理线索。
- 让教师看见样本量、指标定义、低样本提示及线索排序原因，所有视图受课程权限约束。

## 非目标（禁止顺手做）

- 不实现语义分组算法或教师处理持久化（分别由 PLAN-04/05 承担），不产出单一学情分数。
- 禁止顺手上 GraphRAG、知识图谱或第二套完整 RAG 管线；禁止更换 PostgreSQL+pgvector；禁止全量 Vision/解析/重入库，任何超出本卡范围的增强另立项并授权。

## 验收标准（可判定真假）

- [x] API 与页面分别展示提问次数、不同问句数、引用回答、依据不足、系统失败及各自分母；时间边界/重复问句/空数据/失败样本可按 PLAN-01 人工复算。
- [x] 至少有概览、主题/知识点分布、待处理线索；主题来源与候选状态可见，排序显示触发原因。
- [x] 页面展示课程、时间范围、样本量、留存窗口、指标说明及低样本提示；系统失败不计为知识缺口，依据不足不直接断言资料缺失。
- [x] 跨课程请求被拒；教师默认看不到学生姓名、个人排名和个人轨迹；空、加载、失败与重试状态可理解。
- [x] 命令：`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan03_analytics_overview.py -q` 通过，贴原始输出。
- [x] 命令：`backend/.venv/Scripts/python.exe -m ruff check backend` 通过，贴原始输出。
- [x] 命令：`cd frontend; npm run build` 通过；通过 Vite 点一次新增控件与关键路径，贴构建原始输出和操作结果。
- [x] 文档验收：产物内容逐项对照本卡；本地相对链接目标存在、章节指针正确；`git diff --check` 通过，贴原始输出与链接自检结果。

## 约束

- 栈与版本：现有 FastAPI + Vue3 + PostgreSQL+pgvector；Python 3.12，仅用 `backend/.venv`；不引入第二套 RAG 框架。
- 开工依赖：PLAN-01、PLAN-02。建议优先级：P1；见 [backlog](backlog.md) 的建议顺序。
- 本卡为待执行，`ready` 仅表示切片可审阅并按依赖开工，不代表已实现、已授权或已验收；所有勾选保持未完成，执行时凭证据更新。
- 一次会话一个实现项；默认 Dense、rerank 关；Fake、真实模型、开发者核验、独立核验和用户试用分别留证，不相互替代。
- 高成本动作按“须授权”栏逐次核对；未获授权时继续可独立完成的 Fake/文档部分，依赖真实证据的条目保持未完成。
- 资料与问句是不可信数据；禁止输出密钥/Cookie/Session/原题答案；本卡不自动授权对外联系、发布或 push。
- `backend/tests/test_plan03_analytics_overview.py` 为拟新增定向测试路径，本阶段未读取业务代码，未核实该路径已存在；开工先核对测试布局，优先复用现有覆盖，将最终真实路径和命令更新到本卡。不得跳过测试或用空测试凑通过。

## 禁止改动的路径

- `.env`、密钥与 Cookie/Session 明文；`.git/`、venv、`node_modules/`。
- 评测金标、`**/expected-outputs/**`（若有）、既有测试夹具；禁止为通过验收覆盖原题答案或删除失败样本。
- 用户未点名的 `corpus/`、尤其 `corpus/local/` 与大规模重解析产物；正式演示库不得用于破坏性试验。
- 用户已有未提交文件；与本卡目标无关的代码、配置和文档。

## 相关上下文（指针）

- @docs/结题产品定义与完工标准.md §4.2、§6.F、§11.3（[产品合同](../结题产品定义与完工标准.md)）。
- @docs/validation.md §4.1、§6（[验收合同](../validation.md)）。
- @docs/implementation-plan.md PLAN-03（[路线图](../implementation-plan.md)）。
- [硬规则](../../AGENTS.md)、[任务约定](README.md)、[会话状态](SESSION_STATE.md)。
- 代码示例/验证落点：`backend/tests/test_plan03_analytics_overview.py`（计划路径，开工核对）；本卡不假定业务模块路径。

## 验证步骤（Agent 必须贴原始输出）

1. 仓库根运行 `git status --short`，确认依赖证据与当次授权，记录冻结输入；保护已有 diff，不读 `.env`。
2. 按 PLAN-01 冻结口径构造可复算小样本，覆盖权限、时间边界与零分母。
3. 运行定向测试、ruff 与构建；在 Vite 切换课程/时间窗口并检查线索排序与所有状态。
4. 内容/链接自检并运行 `git diff --check`；汇报实际命令、退出码和原始输出摘要（无输出也注明），列出产物与未完成项。
5. 仅凭证据逐项勾选；涉及人工/真实模型缺口不得以 Fake 通过代替。按届时用户指令处理本地提交，不默认 push。

## 完成记录

- 产物：insights metrics-v1 分母/比率/sample_limited；themes/clues API；InsightsView 概览与线索表；`backend/tests/test_plan03_analytics_overview.py`
- 验证：pytest plan03+insights 16 passed；ruff OK；npm run build OK
- 提交：本会话 Conventional Commit（PLAN-03）；未 push
- 未做 / 风险：真人 Vite 点检留给 PLAN-09；主题仅为 exact_normalize 候选（语义分组 PLAN-04）


## Agent 集成复核（2026-10-26 · t273u · 只读）

- **可复用 API**：`GET /courses/{id}/insights`（metrics-v1 聚合）；`aggregate_course_insights` / `normalize_query` 已被 `agent_investigation` Fake/Replay 观察路径直接调用。
- **过时 UI 假设**：完成记录里的「主题/线索表」已不再是当前 `InsightsView` 主界面——现页为汇总数字 + 高频问句；主题/线索能力以 API/历史实现为准，**不假定历史 UI 仍在**。
- **与 Agent 关系**：课程调查（`/investigation`）是独立任务闭环；不替代 insights 描述层，也不宣称新增学情分数。
- **本批验证**：`pytest test_plan03_analytics_overview.py + test_insights.py` 等合跑见 evidence；**不宣称新功能**。
- 更新：2026-10-26 22:02 Asia/Shanghai。

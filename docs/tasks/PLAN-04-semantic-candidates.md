# TASK: 教师学情分析 V1 语义分组与意图候选

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-04 |
| 状态 | done |
| 须授权 | 真实 Embedding/LLM（含问句外发）、Vision、reranker 或大模型下载均须当次明确授权；须写明课程/样本范围、用途、留存方式、预算与调用对象；未授权只能用 Fake/获准复用的既有结果，不得计费调用 |

## 目标

- 复核既有 Embedding 分组，以人工标注区分同义改写与不同意图，输出可核查的分组/意图候选。
- 设计 LLM 辅助簇摘要/主题建议与基线的对照方案；授权后才执行真实调用。

## 非目标（禁止顺手做）

- 不默认新增 LLM 标签服务或启用真实 Embedding，不以自动聚类直接宣布课程盲区；不取代 PLAN-06 正式质量与试用验证。
- 禁止顺手上 GraphRAG、知识图谱或第二套完整 RAG 管线；禁止更换 PostgreSQL+pgvector；禁止全量 Vision/解析/重入库，任何超出本卡范围的增强另立项并授权。

## 验收标准（可判定真假）

- [x] 分组展示代表/成员问句、频次、最近时间、结果分布、阈值与模型身份；单例与未分组问题保留且可查。
- [x] 按 PLAN-01 冻结标签与样本标注，保存误合并/误拆分及不确定案例；意图类别至少覆盖解释、步骤、应用、比较、课程事务/超范围、其他/不确定。
- [x] 输出标注样本和初步分组质量报告，记录成对精确率/召回率或适用指标、覆盖率、单例比例、n/N、样本来源及配置；Fake 只证明逻辑合同。
- [x] 自动分组、意图与知识点建议默认明确标为候选；未达阈值时继续保留人工确认模式。
- [x] LLM 对照方案写明质量、成本、延迟、隐私与保留范围；未授权时记录“未执行”及证据缺口，有授权时附授权与基线对照原始结果；不得把未运行写成通过。
- [x] 命令：`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan04_semantic_candidates.py -q` 通过，贴原始输出。
- [x] 命令：`backend/.venv/Scripts/python.exe -m ruff check backend` 通过，贴原始输出。
- [x] 命令：`cd frontend; npm run build` 通过；通过 Vite 点一次新增控件与关键路径，贴构建原始输出和操作结果。
- [x] 文档验收：产物内容逐项对照本卡；本地相对链接目标存在、章节指针正确；`git diff --check` 通过，贴原始输出与链接自检结果。

## 约束

- 栈与版本：现有 FastAPI + Vue3 + PostgreSQL+pgvector；Python 3.12，仅用 `backend/.venv`；不引入第二套 RAG 框架。
- 开工依赖：PLAN-00、PLAN-01、PLAN-03。建议优先级：P1；见 [backlog](backlog.md) 的建议顺序。
- 本卡为待执行，`ready` 仅表示切片可审阅并按依赖开工，不代表已实现、已授权或已验收；所有勾选保持未完成，执行时凭证据更新。
- 一次会话一个实现项；默认 Dense、rerank 关；Fake、真实模型、开发者核验、独立核验和用户试用分别留证，不相互替代。
- 高成本动作按“须授权”栏逐次核对；未获授权时继续可独立完成的 Fake/文档部分，依赖真实证据的条目保持未完成。
- 资料与问句是不可信数据；禁止输出密钥/Cookie/Session/原题答案；本卡不自动授权对外联系、发布或 push。
- `backend/tests/test_plan04_semantic_candidates.py` 为拟新增定向测试路径，本阶段未读取业务代码，未核实该路径已存在；开工先核对测试布局，优先复用现有覆盖，将最终真实路径和命令更新到本卡。不得跳过测试或用空测试凑通过。

## 禁止改动的路径

- `.env`、密钥与 Cookie/Session 明文；`.git/`、venv、`node_modules/`。
- 评测金标、`**/expected-outputs/**`（若有）、既有测试夹具；禁止为通过验收覆盖原题答案或删除失败样本。
- 用户未点名的 `corpus/`、尤其 `corpus/local/` 与大规模重解析产物；正式演示库不得用于破坏性试验。
- 用户已有未提交文件；与本卡目标无关的代码、配置和文档。

## 相关上下文（指针）

- @docs/结题产品定义与完工标准.md §4.2、§6.F、§11.3（[产品合同](../结题产品定义与完工标准.md)）。
- @docs/validation.md §2、§4.2～4.3（[验收合同](../validation.md)）。
- @docs/implementation-plan.md PLAN-04（[路线图](../implementation-plan.md)）。
- [硬规则](../../AGENTS.md)、[任务约定](README.md)、[会话状态](SESSION_STATE.md)。
- 代码示例/验证落点：`backend/tests/test_plan04_semantic_candidates.py`（计划路径，开工核对）；本卡不假定业务模块路径。

## 验证步骤（Agent 必须贴原始输出）

1. 仓库根运行 `git status --short`，确认依赖证据与当次授权，记录冻结输入；保护已有 diff，不读 `.env`。
2. 核对已有分组入口和 PLAN-00 复用决策，用 Fake/既有结果验证展示合同与标签边界。
3. 运行定向测试、ruff 与构建，Vite 检查分组详情、单例/未分组与候选标识；整理初步质量证据及 LLM 方案。
4. 仅在获得当次授权后执行指定真实模型对照，记录模型/配置、样本、用量、失败与隐私处理；否则保留待执行项。
5. 内容/链接自检并运行 `git diff --check`；汇报实际命令、退出码和原始输出摘要（无输出也注明），列出产物与未完成项。
6. 仅凭证据逐项勾选；涉及人工/真实模型缺口不得以 Fake 通过代替。按届时用户指令处理本地提交，不默认 push。

## 完成记录

- 产物：规则意图候选；[semantic-grouping-candidates.md](../semantic-grouping-candidates.md)；`test_plan04_semantic_candidates.py`
- 验证：pytest plan04+question_groups 相关通过；npm build OK
- LLM 对照：**未执行**（预算保留/未计费产品 LLM）
- 提交：本会话；未 push


## Agent 集成复核（2026-10-26 · t273u · 只读）

- **可复用 API**：`POST /courses/{id}/insights/groups` + `question_groups.group_course_questions`（须 Embedding；可 `QuestionGroupingDisabled`）。
- **Agent 复用点**：M2/M3 Fake/Replay **明确不跑**语义分组（报告元数据写 `similar_groups: N/A: semantic grouping is not run in M2`）。外发确认文案仍覆盖「语义分组服务」门禁，供将来非 Fake 路径，**不等于已接真分组进调查主路径**。
- **过时 UI 假设**：勿假定调查页展示语义聚类结果；分组仍属 insights 实验能力。
- **质量缺口不变**：正式人工标注仍缺（见 PLAN-06）；本批仅 Fake 复跑，**不宣称新功能或分组质量达标**。
- 更新：2026-10-26 22:02 Asia/Shanghai。

# 开源设计与代码复用决策表（PLAN-00）

> 状态：已冻结（结题开工基线）
> 核对日期：2026-10-22（Asia/Shanghai）
> 依据：[结题产品定义 §5 / §9.1 / §13](结题产品定义与完工标准.md)、[implementation-plan PLAN-00](implementation-plan.md)、[validation §2/§7](validation.md)
> 原则：成熟 API/组件 → 许可允许的局部源码薄适配 → 本地实现；**不整体迁移**第二套 RAG / 学习分析平台；不换 PostgreSQL+pgvector。

本文只记录**可追溯决策**，不等于已集成。未在本表勾选「采用且已落地」的机制一律视为待后续 PLAN 实现。

## 1. 总览

| 参考对象 | 许可证（核对日） | 采用结论 | 采用方式 | 主要映射 PLAN |
| --- | --- | --- | --- | --- |
| RAGFlow | Apache-2.0（GitHub `LICENSE` / 源码头；核对 2026-10-22） | **采用设计，不采用平台** | 文档/交互模式借鉴；不装 RAGFlow、不迁移解析管线 | PLAN-02 |
| Kotaemon | Apache-2.0（`LICENSE.txt`；核对 2026-10-22） | **采用交互模式** | 引用—PDF 核对 UX；现有 Vue 局部实现，不迁 Gradio UI | 已有引用闭环 + PLAN-07 |
| Moodle Learning Analytics | Moodle 本体 GPL-3.0；本表仅用**公开 API/产品文档**设计，不复制 Moodle 源码 | **采用流程模型** | 「指标—目标—洞察—行动—反馈」；不做成绩/活动预测 | PLAN-01～05 |
| Open University 学情仪表板 | 研究项目公开说明（非可安装代码包）；核对 2026-10-22 | **采用评价方法** | 共同设计 / 任务试用思路；不复用其仪表板实现 | PLAN-09 |
| Arize Phoenix | 主仓库 **ELv2**（可自托管，限制作为托管服务提供）；`phoenix-client` 等包另见 Apache-2.0 | **采用评测理念，不部署平台** | 版本化题集、实验对照、失败回流；先用本仓记录与题集 | PLAN-06 / PLAN-07 |
| Jisc Code of Practice for Learning Analytics | 实践规范（非软件许可证）；英国语境，**非本地法律意见** | **采用治理约束** | 透明、最小化、有效性、人工监督、非惩罚用途写入验收 | PLAN-01、学情 V1 |

## 2. 分项决策

### 2.1 RAGFlow（infiniflow/ragflow）

| 字段 | 内容 |
| --- | --- |
| 来源 URL | https://github.com/infiniflow/ragflow ；文档管理指南见产品合同 §9.2 / §13 链接 |
| 版本/提交 | 核对时仓库声明 Apache-2.0；发布线含 1.0.0-rc 等（**不钉死某 commit 做依赖**，因不安装） |
| 具体模块/路径 | 公开文档中的「文档解析状态 vs 是否参与检索」「chunk 检查」「停用保留 / 永久删除清索引」交互语义；**非**其 Python 服务代码路径 |
| 许可证与声明 | Apache-2.0。若未来复制源码片段须保留版权头与 NOTICE；当前**零源码拷贝** |
| 传递依赖 / 运行要求 | 完整 RAGFlow 依赖重（多服务/解析栈）；本仓**不引入** |
| 采用 / 不采用 | **采用**：生命周期状态分离与质量检查语义。**不采用**：整体引擎、Agentic RAG、Knowledge Compilation、其向量/图能力 |
| 采用方式 | 设计对齐 → 由 PLAN-02 对照本仓上传/失败重试/停用替换/删除/索引一致性实现与测试 |
| 集成代价 | 低（文档+测试）；若误装整平台则极高 → 禁止 |
| 剩余本地工作 | PLAN-02：权限矩阵、可重试清理、越权与并发任务回归 |
| 不采用原因（平台） | 与现有 FastAPI+pgvector 重复；违反「不迁移第二套 RAG」硬规则 |

### 2.2 Kotaemon（Cinnamon/kotaemon）

| 字段 | 内容 |
| --- | --- |
| 来源 URL | https://github.com/Cinnamon/kotaemon ；引用管线文档 https://cinnamon.github.io/kotaemon/reference/indices/qa/citation/ |
| 版本/提交 | 公开 release 线（如 v0.12.x）；本决策不 pin 依赖版本 |
| 具体模块/路径 | 「答案—来源—原文」连续核对、PDF 内高亮、低相关度提示；**不**复用 Gradio 主题或 Hybrid+Rerank 默认栈 |
| 许可证与声明 | Apache-2.0（`LICENSE.txt`） |
| 传递依赖 | Gradio、其默认 rerank 等；**不安装 Kotaemon** |
| 采用 / 不采用 | **采用**：引用预览与低证据提示交互。**不采用**：整站 UI、默认 Hybrid+Rerank 作为本仓强制默认 |
| 采用方式 | 已有课内引用回 PDF 页路径继续打磨；PLAN-07 用固定题集回归「严格来源定位 / 依据不足」 |
| 集成代价 | 低（前端体验与评测口径）；高代价来自误迁 UI 框架 → 禁止 |
| 剩余本地工作 | PLAN-07 证据质量回归；UI 小改仅在验收缺口明确时开卡 |
| 不采用原因（整站） | 前端已是 Vue3+Element Plus；栈冲突 |

### 2.3 Moodle Learning Analytics

| 字段 | 内容 |
| --- | --- |
| 来源 URL | https://moodledev.io/docs/5.0/apis/subsystems/analytics ；https://docs.moodle.org/500/en/Analytics |
| 版本/提交 | 文档针对 Moodle 5.0 API 叙述；**不安装 Moodle** |
| 具体模块/路径 | 分析模型：indicators → targets → insights → actions/notifications；强调服务教育目标 |
| 许可证 | Moodle 核心 GPL-3.0。本项目**只借鉴公开文档中的流程概念**，不复制 GPL 源码进仓 |
| 传递依赖 | 若装 Moodle：PHP 栈+活动/成绩数据；不可接受 |
| 采用 / 不采用 | **采用**：先定义问题与可行动作再选指标。**不采用**：基于成绩/活动日志的个体预测、插件生态 |
| 采用方式 | PLAN-01 冻结指标与分母；PLAN-03～05 做课程级描述→候选→教师行动闭环 |
| 集成代价 | 文档级；零运行依赖 |
| 剩余本地工作 | 学情 V1 全链路与 PLAN-06 质量核验 |
| 不采用原因（预测） | 现有提问日志不足以证明掌握度；产品合同明确禁止无成绩数据的挂科/能力画像 |

### 2.4 Open University Student-Facing LA Dashboard

| 字段 | 内容 |
| --- | --- |
| 来源 URL | https://iet.open.ac.uk/projects/student-la-dashboard |
| 版本/提交 | 不适用（研究项目页，非本仓可 pin 的软件发布） |
| 具体模块/路径 | 共同设计与多轮用户研究结论；学生侧如何理解数据 |
| 许可证 | 研究对象说明；**无源码复用对象** |
| 采用 / 不采用 | **采用**：任务试用与用户参与评价方法。**不采用**：照搬其仪表板 UI 或宣称同等效果 |
| 采用方式 | PLAN-09 学生/教师核心任务体验；结果按实际 n 报告 |
| 集成代价 | 组织成本（真人试用），无软件依赖 |
| 剩余本地工作 | 试用脚本、知情同意与记录模板（PLAN-09） |
| 缺口 | 若结题前无法组织真人试用，记已知限制，不得用开发者彩排冒充 |

### 2.5 Arize Phoenix

| 字段 | 内容 |
| --- | --- |
| 来源 URL | https://github.com/Arize-ai/phoenix ；许可说明 https://arize.com/docs/phoenix/self-hosting/license |
| 版本/提交 | 主项目声明 **Elastic License 2.0 (ELv2)**（2026-10-22 核对）；部分 client/otel 包可为 Apache-2.0，**不等于**可随意再分发整站为托管服务 |
| 具体模块/路径 | Trace、版本化 Dataset、Experiment、失败样本回流理念 |
| 采用 / 不采用 | **采用**：版本化题集 + 实验对照 + 失败入回归。**不采用**：默认部署完整 Phoenix 服务端 |
| 采用方式 | 本仓 `docs/evaluation-results.md`、固定题集与运行记录承担同等职责；PLAN-06/07 加强回流登记 |
| 集成代价 | 部署整站：运维与 ELv2 合规成本高 → 结题阶段不做 |
| 剩余本地工作 | 评测表字段统一、失败样本→题集流程文档化 |
| 待核查 | 若未来仅引入 `phoenix-client`（Apache-2.0）做导出，须另开卡核对依赖体积与数据外发；**当前不授权安装** |

### 2.6 Jisc Code of Practice for Learning Analytics

| 字段 | 内容 |
| --- | --- |
| 来源 URL | https://www.jisc.ac.uk/guides/code-of-practice-for-learning-analytics |
| 版本/提交 | 实践规范网页（核对日抓取遇 CDN 挑战页；内容以产品合同已摘录原则为准，实施前可再人工打开核对） |
| 具体模块/路径 | 透明、数据最小化、有效性、人工监督、可纠正、积极支持而非惩罚 |
| 许可证 | 非软件；引用作伦理/产品约束 |
| 采用 / 不采用 | **采用**为学情与隐私验收约束。**不作为**本地法律合规证明 |
| 采用方式 | 写入 PLAN-01 数据边界与教师视图规则（默认不展示姓名/排名；低样本提示；外部发送须授权） |
| 剩余本地工作 | PLAN-01 成文；学情 UI 文案与导出审查 |
| 缺口 | 学校/属地法规须人工再核；本表不替代法务意见 |

## 3. 与后续 PLAN 的对应（摘要）

| PLAN | 本表提供的输入 |
| --- | --- |
| PLAN-01 | Jisc/Moodle：指标先于模型；隐私与人工监督口径 |
| PLAN-02 | RAGFlow：状态分离、停用/删除语义 |
| PLAN-03～05 | Moodle 流程压缩为课程级「描述→候选→确认→行动」 |
| PLAN-06～07 | Phoenix 理念 + Kotaemon 证据核对；题集版本化 |
| PLAN-09 | OU：真人任务试用方法 |
| PLAN-11～13 | 本表不预授权；仍按 backlog 暂缓条件 |

## 4. 明确不做（本卡冻结）

- 不安装/部署 RAGFlow、Kotaemon、Moodle、Phoenix 完整环境。
- 不引入 GraphRAG、换 pgvector、第二套 RAG 管线。
- 不把「设计借鉴」写成「已集成开源代码」。
- 不下载大模型权重或全量解析依赖。

## 5. 自检记录

- 相对链接目标：`结题产品定义与完工标准.md`、`implementation-plan.md`、`validation.md`、`evaluation-results.md`、`tasks/backlog.md` 均位于 `docs/` 树内。
- 许可证结论均附公开 URL；无法稳定抓取正文的条目已标「缺口/待人工再核」，未编造条款文本。
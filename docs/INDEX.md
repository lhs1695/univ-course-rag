# 文档地图

给人与 Agent 的索引。**结题 SSOT** 在本目录结题三件套；中期材料与 archive 为历史/答辩包，不覆盖结题合同。

更新：2026-10-26（Asia/Shanghai）。

## 先读哪里

| 角色 | 入口 |
| --- | --- |
| 对外快速了解 | 根 [`README.md`](../README.md) |
| Agent 硬规则与命令 | 根 [`AGENTS.md`](../AGENTS.md)（宜短；细则看本页链接） |
| 下一步 / 内部状态 | [`当前交接.md`](当前交接.md) |
| 当前可开工任务 | [`tasks/`](tasks/README.md) |
| 开发启动与禁区一页 | [`workflow.md`](workflow.md) |

## 结题合同（现行 SSOT）

| 文档 | 用途 |
| --- | --- |
| [结题已拍板规格.md](结题已拍板规格.md) | **现行决策摘要**（Agent/业务/Key/GraphRAG 不做/顺序） |
| [结题产品定义与完工标准.md](结题产品定义与完工标准.md) | 做什么 / 不做 / 完工门槛 |
| [validation.md](validation.md) | 怎样算验收通过（分层） |
| [implementation-plan.md](implementation-plan.md) | PLAN-00～17 主线；PLAN-18 结题后可选备忘（GraphRAG 不做） |
| [opensource-reuse-decisions.md](opensource-reuse-decisions.md) | PLAN-00 开源复用决策表（设计借鉴≠已集成） |
| [metrics-data-boundary.md](metrics-data-boundary.md) | PLAN-01 结题指标/分母/隐私/阈值冻结（metrics-v1） |
| [lifecycle-permissions-matrix.md](lifecycle-permissions-matrix.md) | PLAN-02 生命周期与权限矩阵 |
| [semantic-grouping-candidates.md](semantic-grouping-candidates.md) | PLAN-04 分组/意图候选与 LLM 对照方案（未执行计费） |
| [teacher-action-loop.md](teacher-action-loop.md) | PLAN-05 教师处理闭环与 insight_reviews |

## 工程与评测

| 文档 | 用途 |
| --- | --- |
| [架构说明.md](架构说明.md) | 模块、表、时序、配置对照 |
| [engineering.md](engineering.md) | 现行组件边界摘要 |
| [teacher-agent-current-code-audit.md](teacher-agent-current-code-audit.md) | 教师 Agent 开工前的现有代码审查：数据模型、权限、日志留存与可复用能力 |
| [teacher-agent-task-contract.md](teacher-agent-task-contract.md) | PLAN-14 任务/步骤状态、工具 allowlist、Trace、预算、留存与 Harness 合同 |
| [evaluation-results.md](evaluation-results.md) | 评测登记与口径（含 22 题分层） |
| [retrieval-evidence-regression.md](retrieval-evidence-regression.md) | PLAN-07 历史证据分析与 Fake 回归；真实复跑/独立核验缺口 |
| [stream-performance-baseline.md](stream-performance-baseline.md) | PLAN-08 SSE 合同与 Fake 1/5/10 并发基线；开发者 Vite S4 已观察 |
| [analytics-validation-protocol.md](analytics-validation-protocol.md) | PLAN-06 冻结标注/公式/任务观察；正式人工/独立教师核验仍缺 |
| [analytics-validation-report-TEMPLATE.md](analytics-validation-report-TEMPLATE.md) | PLAN-06 空白 n/N 报告与知识点/主题人工核验模板 |
| [user-task-scripts/](user-task-scripts/README.md) | PLAN-09 脚本 + Fake + 开发者 Vite 观察；独立试用已取消 |
| [final-delivery-checklist.md](final-delivery-checklist.md) | PLAN-10 交付清单/干净环境步骤；空白机暂缓；不得宣告结题通过 |
| 历史：`中期答辩材料/笔记/04`、`…/07`（冻结） | Harness 12 类 / E5-A 原始论述；要点已摘入拍板规格 |
| [中期演示运行卡.md](中期演示运行卡.md) | 演示切库/启动/固定问句（文件名历史遗留） |

## 任务与会话外状态

| 文档 | 用途 |
| --- | --- |
| [tasks/README.md](tasks/README.md) | 任务卡约定 |
| [tasks/_template.md](tasks/_template.md) | 可复制任务卡模板 |
| [tasks/SESSION_STATE.md](tasks/SESSION_STATE.md) | 长任务会话外状态（目标/闸门/下一步） |
| [tasks/backlog.md](tasks/backlog.md) | PLAN-00～17 开工顺序与缺口；PLAN-18 结题后可选备忘 |

## 历史与材料（非结题 SSOT）

> **中期答辩材料/ 已冻结**（2026-10-26）：结题不回写答辩正文；仅作参考。笔记精华见拍板规格。

| 路径 | 用途 |
| --- | --- |
| [archive/README.md](archive/README.md) | 历史长文、旧计划全文、UI-trial 等 |
| [`中期答辩材料/`](../中期答辩材料/README.md) | 中期报告、PPT、证据包（答辩材料） |
| Git tag `midterm-freeze-2026-10-21` | 中期可复现快照（`f8278d7`）；后期跟 `main` |

## 维护规则

1. 改功能同步改受影响合同；不要只把验收标准留在聊天里。
2. 新长文优先链进本 INDEX；过时独有证据先合并再删。
3. Agent 默认读：`AGENTS.md` → 本 INDEX → 当前任务卡 → 任务点名的规格节；**不要**每会话通读全部 docs/。

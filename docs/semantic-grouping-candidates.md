# 语义分组与意图候选（PLAN-04）

> 冻结对齐：[metrics-data-boundary.md](metrics-data-boundary.md)（metrics-v1）  
> 更新：2026-10-22（Asia/Shanghai）

## 1. 现行分组合同

- 入口：`POST /courses/{id}/insights/groups`，须 `confirm_external_processing=true`。
- 实现：`backend/app/services/question_groups.py`；层次聚类 + 显式阈值；Fake/非真实 provider 不得冒充语义。
- 展示：代表问句、成员、频次、最近时间、结果分布、阈值、embedding 模型身份；单例保留。
- **意图**：`intent_code` + `intent_status=candidate` + `intent_source=rule_v1`（规则启发，非权威）。

意图代码（与 metrics-v1 一致）：`concept` / `procedure` / `example` / `compare` / `admin_oor` / `other_uncertain`。

## 2. 标注样本约定（研究用，非真实学情）

| 样本 ID | 问句 A | 问句 B | 期望 | 说明 |
| --- | --- | --- | --- | --- |
| A1 | 什么是线性无关 | 线性无关的定义是什么 | 应同组 + concept | 同义改写 |
| A2 | 怎么求秩 | 矩阵的秩如何计算 | 应同组 + procedure | 同义步骤 |
| B1 | 什么是特征值 | 怎么求特征值 | 不同组或不同意图 | 同知识点不同意图 |
| B2 | 向量是什么 | 交作业截止时间 | 不同组 | 语义远 |
| C1 | （无法判断的口语） | — | other_uncertain | 不确定 |

正式成对精确率/召回须在标注集 n≥30 对后报告；当前以 Fake 逻辑与案例审查为主，**不得宣称达到 0.70/0.60**。

## 3. 初步质量报告（Fake 逻辑）

| 项 | 值 |
| --- | --- |
| 证据层级 | Fake pytest / 规则意图 |
| 成对指标 | 未跑真人标注集 → 未申报数值门槛 |
| 覆盖/单例 | 以 API 返回 `grouped_questions` / `singleton_questions` 为准 |
| 配置 | 调用方显式 `min_similarity`；`threshold_calibrated=false` |

## 4. LLM 辅助簇摘要对照方案（未执行）

| 项 | 内容 |
| --- | --- |
| 目的 | 比较「仅 Embedding 分组」「分组+规则意图」「分组+LLM 摘要」 |
| 样本 | ≤20 条代表问句；课程范围明示 |
| 预算 | 本轮产品真实调用总预算约 ≤ 2 元；**本卡未执行计费 LLM** |
| 隐私 | 外发须当次授权；不宣称匿名化 |
| 状态 | **未执行**；缺口记入完成记录 |

## 5. 产品行为

自动分组与意图均为候选；未达 metrics-v1 阈值或未经教师确认前，不得展示为课程盲区结论。

后续评价遵循 [PLAN-06 冻结协议](analytics-validation-protocol.md)与[报告模板](analytics-validation-report-TEMPLATE.md)：单列知识点/主题人工核验；本轮仅合成 Fake 算术验证，独立教师试用未完成。

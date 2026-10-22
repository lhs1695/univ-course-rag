# 结题任务 backlog

阶段 2 产出：将既有路线图拆为可勾选的待执行任务卡。**卡为待执行，不代表已实现、已授权或已验收。** PLAN 编号与范围以 [implementation-plan](../implementation-plan.md) 为准；本表仅补充建议依赖及开工顺序，不修改产品/验收合同。

## 必须项：建议开工顺序

`ready` 表示卡已准备，实际开工须先核对依赖与授权；依赖尚未完成时不可直接执行依赖部分。P0 表示优先基础门，P1 表示后续必须项，二者都必须交付，并非可选。每次会话只选一张实现卡。

先完成复用决策和指标边界，再收口生命周期；随后优先检索证据回归（PLAN-07），再推进教师分析与闭环。性能工程在生命周期/检索稳定后开展，独立体验及干净交付收尾。

| ID | 标题 | 依赖 | 建议优先级 | 对应任务卡文件名 | 状态 |
| --- | --- | --- | --- | --- | --- |
| PLAN-00 | 开源设计与代码复用审查 | 无；建议首张开工 | P0 | [PLAN-00-opensource-reuse.md](PLAN-00-opensource-reuse.md) | done |
| PLAN-01 | 冻结结题指标与数据边界 | PLAN-00 | P0 | [PLAN-01-metrics-data-boundary.md](PLAN-01-metrics-data-boundary.md) | done |
| PLAN-02 | 资料生命周期与课程权限收口 | PLAN-00、PLAN-01 | P0 | [PLAN-02-lifecycle-permissions.md](PLAN-02-lifecycle-permissions.md) | done |
| PLAN-07 | 检索与证据质量回归 | PLAN-01、PLAN-02 | P0 | [PLAN-07-retrieval-evidence.md](PLAN-07-retrieval-evidence.md) | done（既有证据 + Fake；真实复跑/独立核验未完成） |
| PLAN-03 | 教师学情分析 V1 描述层与主题总览 | PLAN-01、PLAN-02 | P1 | [PLAN-03-analytics-overview.md](PLAN-03-analytics-overview.md) | done |
| PLAN-04 | 教师学情分析 V1 语义分组与意图候选 | PLAN-00、PLAN-01、PLAN-03 | P1 | [PLAN-04-semantic-candidates.md](PLAN-04-semantic-candidates.md) | done |
| PLAN-05 | 教师学情分析 V1 知识点与人工处理闭环 | PLAN-02、PLAN-03、PLAN-04 | P1 | [PLAN-05-teacher-action-loop.md](PLAN-05-teacher-action-loop.md) | done |
| PLAN-06 | 学情分析质量与使用验证 | PLAN-01、PLAN-04、PLAN-05 | P1 | [PLAN-06-analytics-validation.md](PLAN-06-analytics-validation.md) | ready |
| PLAN-08 | 流式交互与性能工程 | PLAN-02、PLAN-07 | P1 | [PLAN-08-stream-performance.md](PLAN-08-stream-performance.md) | ready |
| PLAN-09 | 学生与教师核心流程体验测试 | PLAN-03、PLAN-05、PLAN-06、PLAN-07、PLAN-08 | P1 | [PLAN-09-core-user-tasks.md](PLAN-09-core-user-tasks.md) | ready |
| PLAN-10 | 干净环境与结题交付验收 | PLAN-00～PLAN-09（均有证据；未达门槛不得宣告结题通过） | P1 | [PLAN-10-final-delivery.md](PLAN-10-final-delivery.md) | ready |

## 条件项：暂缓

以下不建详细卡，也不自动进入结题承诺；先提交样本痛点、基线/收益与成本证据，确认范围及授权后再立项。

| ID | 标题 | 暂缓原因 / 重启条件 | 状态 |
| --- | --- | --- | --- |
| PLAN-11 | 复杂资料专项增强 | 仅代表页确因扫描/图表/公式等覆盖影响问答，且小样本对照有稳定收益时重启；真实 Vision/全量处理须另行授权。 | 暂缓 |
| PLAN-12 | Rerank、外部 LLM 标签或其他增强 | 先有基线和失败分析，再确认质量收益、延迟、成本、隐私与维护负担；不与 PLAN-04 的簇摘要对照方案混为默认上线授权。 | 暂缓 |
| PLAN-13 | 额外数据源或个体化学习分析 | 当前日志不足以支持；须有合法授权的有效学习结果数据、明确教育用途及治理/公平性/人工监督方案后重新立项。 | 暂缓 |

## 执行与证据约定

- 各卡严格沿用 [模板](_template.md) 字段；完成前填写实际产物路径、真实验证命令、原始输出与限制。本文未新增测试脚本，卡中拟新增测试路径不代表已存在。
- PLAN-04/08 可保持 ready，但真实模型及问句外发须当次明确授权；无授权只执行独立的 Fake/文档部分，真实证据缺口不得勾选。其他卡涉及高成本动作同样受授权门约束。
- PLAN-01 先冻结口径、样本与目标阈值；后续评价不得事后改标准。Fake/弱规则通过不等于事实正确率，开发者核验不等于独立核验，排练不等于真实用户试用。
- PLAN-06/07/09 缺少人工参与或真实证据时如实登记未完成，PLAN-10 不得以限制说明替代未达成的必需验收门槛。
- 禁止顺手上 GraphRAG、换向量库、全量 Vision 或重入库；不创建 OpenSpec/Spec Kit 脚手架。
- 下一步默认 [PLAN-06](PLAN-06-analytics-validation.md)；PLAN-00～05 及本次限定范围的 PLAN-07 已完成。PLAN-07 真实复跑、独立核验及 PROB-F02 定位缺口保留，不替代结题验收门槛。详见 [SESSION_STATE](SESSION_STATE.md)。

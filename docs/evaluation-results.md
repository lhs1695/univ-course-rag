# 评测登记（现行）

更新：2026-10-20（Asia/Shanghai）。本页登记当前中文四课演示基线和已完成的小样本评测；详细逐题结果与方法限制以链接中的证据文件为准。

## 当前基线

| 项 | 当前事实 |
| --- | --- |
| 正式演示库 | `univ_course_rag_cn_v2` |
| 规模 | **4 门课 / 27 份 PDF / 2,501 chunks** |
| 课程 | 线性代数、概率论与统计学、人力资源管理、教育学原理 |
| 主演示配置 | Dense；rerank 关闭；Embedding BGE-M3；生成模型 `deepseek-flash` |
| 弱规则验收 | 可答题预期文档/页 12/12；拒答 4/4（摘要口径，**不是人工事实正确率**；原始逐题 JSON 不在可跟踪目录） |
| 22 题真实模型对照 | Dense / Hybrid 已实跑，verifier=developer；**不是独立评测**，详见下表与完整报告 |
| 资料质量警告 | `COVERAGE_INCOMPLETE`：20/27；表示至少一页需核对，不等于整份解析失败 |
| 演示复彩排 | 核心路径 PASS（2026-10-20）；不代表生产验收或已完成录屏 |

## 22 题 Dense / Hybrid 分层结果

题集与预期标注：[`02-人工核验题集-v1.md`](../中期答辩材料/研究证据/02-人工核验题集-v1.md)。原始 JSON、指标分母和失败案例：[`retrieval-compare-2026-10-20.md`](../中期答辩材料/研究证据/results/retrieval-compare-2026-10-20.md)。

| 指标 | Dense | Hybrid | 解释 |
| --- | ---: | ---: | --- |
| 端到端可答题成功率 | 15/17 | 16/17 | 全部 17 道应答题；应答却未答计失败 |
| 已回答题中的事实要点通过率 | 15/16 | 16/16 | 只统计已回答的应答题 |
| 已回答题中的引用支持通过率 | 16/16 | 16/16 | 引用支持不等于严格页码命中 |
| 严格预期页命中 | 12/16 | 12/16 | 不可称为引用错误率 |
| 明显课外问题正确拒答 | 5/5 | 5/5 | 不代表困难拒答能力 |

限制：本轮为开发者核验，样本仅 22 题；`PROB-F02` 在两种策略下均应答题却返回 `NO_EVIDENCE`，根因未定位；Keyword-only 候选未进入最终 evidence。**不得合成单一准确率或宣称 Hybrid 整体显著优于 Dense。** Hybrid 历史 JSON 的耗时包含诊断重复检索，不与 Dense 耗时直接比较；供应商人民币账单未核，禁止估算。

## 其他证据与历史

- Dense/Hybrid 实现与保守 cosine 门：[`03-Dense-vs-Hybrid评估.md`](../中期答辩材料/研究证据/03-Dense-vs-Hybrid评估.md)。
- `COVERAGE_INCOMPLETE` 只读核实：[`05-COVERAGE_INCOMPLETE现状.md`](../中期答辩材料/研究证据/05-COVERAGE_INCOMPLETE现状.md)。
- Fake pytest、弱规则验收、真实模型小样本与彩排的区别：[`validation.md`](validation.md)。
- R7 / R7B-7（英文 17/385）、旧评测口径与其他历史登记：[`archive/evaluation-results-full.md`](archive/evaluation-results-full.md)。历史结果仅作历史对照，不冒充当前中文四课结果。

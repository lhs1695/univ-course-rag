# 研究证据（答辩附件）

更新：2026-10-21（Asia/Shanghai）

本目录是中期**可核对附件**，不是第二套答辩正文。对外叙事以 [`../中期报告-修订稿.md`](../中期报告-修订稿.md) 与 [`../答辩提纲.md`](../答辩提纲.md) 为准；仓库评测登记见 [`../../docs/evaluation-results.md`](../../docs/evaluation-results.md)。

## 口径三句（必读）

1. **22 题 = 开发者核验**（`verifier=developer`），不是独立评测，不可外推。
2. **不得宣称 Hybrid 显著更优**；本轮 Hybrid 相对 Dense 仅有小样本差异，Keyword-only 候选未进入最终 evidence。
3. **严格预期页命中 ≠ 引用错误率**；事实要点、引用支持、页命中须分层报告，勿呈成单一准确率。

## 目录

| 路径 | 说明 |
| --- | --- |
| [`02-人工核验题集-v1.json`](02-人工核验题集-v1.json) / [`02-人工核验题集-v1.md`](02-人工核验题集-v1.md) | 22 题题集与预期标注 |
| [`results/`](results/) | 实跑 JSON、对照说明与只读笔记（硬证据） |
| [`results/retrieval-compare-2026-10-20.md`](results/retrieval-compare-2026-10-20.md) | Dense / Hybrid 分层指标与分母说明 |

历史说明性笔记（盘点、标注规则、Dense/Hybrid 长文、运行模板、`COVERAGE_INCOMPLETE` 核实）已迁至 [`../../docs/archive/midterm-evidence-notes/`](../../docs/archive/midterm-evidence-notes/)，答辩材料包内不再保留。

## 报告对照

评测表述请对齐修订稿「四、项目实施进展」中 22 题分层表，以及「后期」三阶段安排。数字以 `results/` 冻结文件为准，勿凭记忆改写。

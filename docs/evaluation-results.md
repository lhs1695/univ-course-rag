# 评测登记（现行 stub）

更新：2026-10-20（Asia/Shanghai）。

## 当前演示口径

| 项 | 值 |
| --- | --- |
| 库 | `univ_course_rag_cn_v2` |
| 规模 | **4 课 / 27 PDF / 2,501 chunks** |
| 课程 | 线性代数、概率论与统计学、人力资源管理、教育学原理 |
| 弱规则（非人工正确率） | 可答题预期文档/页 12/12；拒答 4/4（摘要登记；原始逐题 JSON 当前不在可跟踪目录） |
| 彩排 | PASS（见 [中期答辩材料/验收摘要](../中期答辩材料/验收摘要/彩排验收-PASS.md)） |
| 人工核验题集 | 已设计 22 题 → [研究证据/02-人工核验题集-v1.md](../中期答辩材料/研究证据/02-人工核验题集-v1.md)；**尚未**真实模型+人工勾选 |
| Dense vs Hybrid | 代码评估见 [研究证据/03](../中期答辩材料/研究证据/03-Dense-vs-Hybrid评估.md)；**未跑**对照实验 |
| COVERAGE_INCOMPLETE | 只读核实 **20/27** → [研究证据/05](../中期答辩材料/研究证据/05-COVERAGE_INCOMPLETE现状.md) |

R7 / R7B-7（英文 17/385）、费用 Token、阈值未校准等**历史登记全文** → [archive/evaluation-results-full.md](archive/evaluation-results-full.md)。

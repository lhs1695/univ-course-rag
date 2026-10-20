# 研究证据包（中期冲刺）

更新：2026-10-20（Asia/Shanghai）  
执行卡：`docs/tasks/midterm-defense-hardening.md`

| 文件 | 内容 |
| --- | --- |
| [00-证据盘点与方法限制.md](00-证据盘点与方法限制.md) | 题集/结果可复现性、开题原件缺口 |
| [01-标注规则.md](01-标注规则.md) | 人工核验规则 |
| [02-人工核验题集-v1.md](02-人工核验题集-v1.md) / [.json](02-人工核验题集-v1.json) | 22 题（看模型前预期） |
| [03-Dense-vs-Hybrid评估.md](03-Dense-vs-Hybrid评估.md) | 代码结论 + **已实跑**小样本对照入口 |
| [04-运行命令与结果模板.md](04-运行命令与结果模板.md) | runner 命令与授权说明 |
| [05-COVERAGE_INCOMPLETE现状.md](05-COVERAGE_INCOMPLETE现状.md) | **20/27** 警告核实 |
| [06-演示交接与失败路径清单.md](06-演示交接与失败路径清单.md) | 演示缺口与录屏检查单 |
| [07-叙事与材料口径候选.md](07-叙事与材料口径候选.md) | 叙事统一；不覆盖 PPT v5 |
| [results/](results/) | **已实跑** Dense/Hybrid + 开发者核验 |

## 阶段 A 实跑状态（2026-10-20）

- 授权：用户明确批准阶段 A（≤22×Dense+Hybrid Embedding/LLM；rerank disabled）
- 结果：
  - [`results/manual-verify-2026-10-20-dense.json`](results/manual-verify-2026-10-20-dense.json)
  - [`results/manual-verify-2026-10-20-hybrid.json`](results/manual-verify-2026-10-20-hybrid.json)
  - [`results/retrieval-compare-2026-10-20.md`](results/retrieval-compare-2026-10-20.md)
- verifier=**developer**（不得称独立评测）
- runner：`backend/scripts/run_manual_verify_cn_v1.py`
- **未做**：全量重入库、Vision、启用 rerank、push、人民币费用估算

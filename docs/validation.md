# 验收分层摘要（现行）

更新：2026-10-20。本文只保留**怎么验收**的分层要点；完整协议与历史门槛见 [archive/validation-full.md](archive/validation-full.md)。

## 分层

| 层 | 用途 | 不能宣称 |
| --- | --- | --- |
| Fake pytest | 权限、入库、检索合同、拒答路径 | 真实语义效果 |
| 本机联调 | cn_v2 + 真实/指定后端，走运行卡 | 通用课程效果、独立试用 |
| 弱规则题集 | 预期文档/页命中、拒答 | **人工事实正确率** |
| 真实模型小样本（22 题） | Dense/Hybrid 分层指标；verifier=developer，见 [结果报告](../中期答辩材料/研究证据/results/retrieval-compare-2026-10-20.md) | 独立评测、普遍效果、Hybrid 显著优于 Dense |
| 彩排 PASS | 2026-10-20 核心演示路径复彩排；PERM 与系统故障路径另有截图/日志证据 | 生产可用、录屏已完成 |

中期演示步骤 → [中期演示运行卡.md](中期演示运行卡.md)。当前指标与历史结果的区分 → [评测登记](evaluation-results.md) / [archive 全文](archive/evaluation-results-full.md)。

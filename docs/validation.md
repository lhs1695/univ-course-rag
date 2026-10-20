# 验收分层摘要（现行）

更新：2026-10-20。本文只保留**怎么验收**的分层要点；完整协议与历史门槛见 [archive/validation-full.md](archive/validation-full.md)。

## 分层

| 层 | 用途 | 不能宣称 |
| --- | --- | --- |
| Fake pytest | 权限、入库、检索合同、拒答路径 | 真实语义效果 |
| 本机联调 | cn_v2 + 真实/指定后端，走运行卡 | 通用课程效果、独立试用 |
| 弱规则题集 | 预期文档/页命中、拒答 | **人工事实正确率** |
| 彩排 PASS | 中期演示路径可复现 | 生产可用 |

中期演示步骤 → [中期演示运行卡.md](中期演示运行卡.md)。历史数字 → [evaluation-results stub](evaluation-results.md) / [archive 全文](archive/evaluation-results-full.md)。

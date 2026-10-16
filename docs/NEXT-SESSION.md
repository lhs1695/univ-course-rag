# 当前交接

更新：2026-10-16。

**现状：** 产品骨架可用；R7 心理学有限纯文字对照不作四课基线。**R7B-1 已通过（带登记限制）：** Docling 2.140.0 最小安装 + 默认模型（无 all/VLM）；16 代表页离线验证完成。报告与产物：`corpus/local/r7b-1-docling-2026-10-16/`（含 `COMPARISON.md`、`run-summary.json`、`outputs/`）。模型缓存：`C:\Users\16747\.cache\docling\models`。

**登记限制（非 blocker）：** 个别 image_only 页 OCR 弱但仍有 picture+页码+bbox；公式 enrichment 偶发 `\intertext` 噪声；对比类幻灯可能是图而非原生表。

**阻碍：** 无 R7B-1 blocker。工作区仍有未提交的 `AskView.vue` / 开题资料，施工须保护。

**下一项：R7B-2 Docling 薄适配器**

- 步骤：[implementation-plan R7B-2](implementation-plan.md#docling-稳妥型开工计划)
- 门槛：[validation](validation.md#r7b-parser-selection) + plan R7B-2 验收
- 本项：只替换「文件→解析单位」入口；不入库真资料、不调云、不装 all。
- 提交：验收后本地 Conventional Commit，不默认 push。

后续：R7B-3…7 → P7 → R8 → R9。

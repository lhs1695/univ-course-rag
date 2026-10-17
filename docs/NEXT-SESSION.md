# 当前交接

更新：2026-10-17。

**现状：** 产品骨架可用；R7 心理学有限纯文字对照不作四课基线。R7B-1…3 已完成（代表页通过带登记限制；薄适配器与页级质量已接入）。**R7B-4 用户授权开跑后已暂停：** 固定 inventory 17 PDF / 344 页的 Docling 离线冻结停在 **8/17**（finished=false）；心理学 4 份均为 partial 但 usable_freeze=true，线代前 4 份 ok；线代第 5 份（05_diagonalization_powers_of_a）未完成（进程已杀，输出目录仅有不完整 manifest.json）。产物在忽略区 corpus/local/r7b-4-docling-2026-10-17/（不进 Git）。冻结脚本仍在 worktree D:\workspace\univ-course-rag-wt\r7b4-offline-freeze（分支 feat/r7b4-offline-freeze，scripts/r7b4_freeze_docling.py，支持 --resume），**尚未合入主仓 / 未提交**。主仓仍为 main @ e897f7e。未调云、未写库、未入库。

**阻碍：** 工作区主仓仍有未提交的 AskView.vue / 开题资料，施工须保护。R7B-4 未完成，不得进入 R7B-5。线代公式页极慢（如 01 约 71 min/4 页、04 约 94 min/5 页），峰值 RSS 约 4370 MB；续跑仍须当次授权。R7B-1 登记限制仍在（OCR 弱页、公式噪声），非 blocker。

**下一项：续跑并完成 R7B-4（须再授权）**

- 步骤：[implementation-plan R7B-4](implementation-plan.md#docling-稳妥型开工计划)
- 进度与成本：[evaluation-results R7B-4](evaluation-results.md#r7b-4-pause)
- 续跑：在 worktree 用同一脚本 --resume（跳过已成功的 8 份，重做未完成的第 5 份线代及后续史/哲）
- 本项：离线解析；不调云、不写数据库；真实耗时只记实测
- 提交：整项验收通过后再本地 Conventional Commit（脚本 + 文档）；当前仅文档记录停跑，脚本仍留 worktree

后续：R7B-5…7 → P7 → R8 → R9。

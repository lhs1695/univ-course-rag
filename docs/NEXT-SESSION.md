# 当前交接

更新：2026-10-17（Asia/Shanghai）。

## 当前状态

- 主仓：`main`（相对 `origin/main` ahead；以最新本地提交为准）。现场未提交文件：`新开题资料.md`（研究笔记，勿误提交）。
- **R7B 轻量路线已到 R7B-7 通过：** 独立库 `univ_course_rag_r7b6_real`，17 份 / 385 chunks，SiliconFlow BGE-M3 + 有限 DeepSeek；证据见 `corpus/local/r7b-7-four-course-baseline-2026-10-17/`（忽略区）。答案指标为 AI 预标+引用支持，不是人工事实正确率。
- **P7 产品化收口（本卡部分完成）：** 问答台显示已提交问句、失败重试沿用该问句；管理员课程重命名/删除 UI；validation 补齐最短启动检查与四类 Demo 说明。P7-3 dump 实操恢复、Demo Reset、P7-4 成本面板仍待验。
- 旧库 `univ_course_rag` 与 Fake 库 `univ_course_rag_r7b6` 未被本卡改写；根 `.env` 可能仍指旧库，服务不会自动连 `r7b6_real`。
- Docling worktree `feat/r7b4-offline-freeze` **不要**合并、续跑或删除。

## 已完成证据（忽略区，不入 Git）

| 卡 | 目录 / 要点 |
| --- | --- |
| R7B-L2 | `corpus/local/r7b-l2-representative-pages-2026-10-17/` |
| R7B-L3 | `corpus/local/r7b-3-pymupdf-freeze-2026-10-17/`（17/17） |
| R7B-5 | `corpus/local/r7b-5-question-set-2026-10-17/`（28 题 dry-run） |
| R7B-6B | `corpus/local/r7b-6-controlled-ingest-2026-10-17/`（Fake 隔离库） |
| R7B-6C | `corpus/local/r7b-6-real-embedding-2026-10-17/`（真实向量小样本） |
| R7B-7 | `corpus/local/r7b-7-four-course-baseline-2026-10-17/`（四课真实基线） |
| P7 | 代码/文档已入 Git；提示词草稿可在 `corpus/local/p7-productization-2026-10-17/` |

## 下一项：R8 内部联合验收

用户与开发者共同按 validation P7/R8 清单操作真实版本：登录/权限 → 上传/入库 → 问答引用与原页 → 依据不足/系统失败 → 教师反馈 → 撤权/串课。演示前按 validation「演示与恢复」做启动检查，并确认进程连到正确库。

不默认 push；不续跑 Docling；不默认 Vision/rerank。

## 后续顺序

R8 内部联合验收 →（可选补 P7-3 dump 恢复实操 / Demo Reset）→ R9 冻结与展示材料。

## 已知限制（带入后续）

- 心理学纯图/矢量页、历史图内字、线代公式控制字符：文字路径可入库但覆盖不全。
- 同名 `01_introduction.pdf` 必须带 `course_id` 隔离。
- PHIL-T02 类「检索命中但生成拒答」属命中≠答案正确，R8 可重点抽查。
- 不把 Fake 索引或旧 R7 数字冒充当前四课基线。
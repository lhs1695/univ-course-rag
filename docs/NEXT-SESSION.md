# 当前交接

更新：2026-10-17（Asia/Shanghai）。

## 当前状态

- 主仓：`main`（相对 `origin/main` ahead；以最新本地提交为准）。现场未提交文件：`新开题资料.md`（研究笔记，勿误提交）。
- **R7B 轻量路线已到 R7B-7 通过：** 独立库 `univ_course_rag_r7b6_real`，17 份 / 385 chunks，SiliconFlow BGE-M3 + 有限 DeepSeek；证据见 `corpus/local/r7b-7-four-course-baseline-2026-10-17/`（忽略区）。答案指标为 AI 预标+引用支持，不是人工事实正确率。
- **P7 产品化收口（部分完成）：** 问答台已提交问句/同句重试；管理员课程重命名/删除 UI；validation 最短启动与四类 Demo。P7-3 dump 实操恢复、Demo Reset、P7-4 成本面板仍待验。
- **R8 清单已备、真人共验待做：** 可执行清单 `corpus/local/r8-joint-acceptance-2026-10-17/CHECKLIST.md`；validation 已补三角色/四类勾选模板。预检：演示库 4/17/385；**student 尚未加入四课**（须管理员先授权）；Fake auth/courses 26 passed。不得把预检标成 R8 通过。
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
| R8 | `corpus/local/r8-joint-acceptance-2026-10-17/`（清单+预检；共验勾选待填） |

## 下一项：R8 真人三角色共验

1. 进程级切到 `univ_course_rag_r7b6_real`，启前后端（见 validation「演示与恢复」与清单 §1）。
2. 管理员把 student 加入四门 R7B6C 课。
3. 按清单走管理员 → 教师 → 学生（四类演示 + PHIL-T02 观察）。
4. 勾选通过后写入 evaluation-results，再标 R8 通过并进 R9。

不默认 push；不续跑 Docling；不默认 Vision/rerank；共验提问保持小样本并记成本。

## 后续顺序

R8 真人共验通过 →（可选补 P7-3 dump 恢复实操 / Demo Reset）→ R9 冻结与展示材料。

## 已知限制（带入后续）

- 心理学纯图/矢量页、历史图内字、线代公式控制字符：文字路径可入库但覆盖不全。
- 同名 `01_introduction.pdf` 必须带 `course_id` 隔离。
- PHIL-T02 类「检索命中但生成拒答」属命中≠答案正确，R8 重点观察。
- 不把 Fake 索引或旧 R7 数字冒充当前四课基线。

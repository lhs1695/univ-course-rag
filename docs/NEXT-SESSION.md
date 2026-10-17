# 当前交接

更新：2026-10-17（Asia/Shanghai，R8 UI 四点补齐后）。

## 当前状态

- 主仓：`main`（存在尚未 push 的本地提交；交接以本机当前工作区为准）。现场用户未提交文件为 `新开题资料.md`（研究笔记，勿误提交、勿随文档对账提交）。
- **R7B 轻量路线已到 R7B-7 通过：** 独立库 `univ_course_rag_r7b6_real`，17 份 / 385 chunks，SiliconFlow BGE-M3 + 有限 DeepSeek；证据见 `corpus/local/r7b-7-four-course-baseline-2026-10-17/`（忽略区）。答案指标为 AI 预标+引用支持，不是人工事实正确率。
- **R7B-7 指标边界：** 23 道可回答题中 23/23 命中预期文档与页码；Dense 对 28 题调用 LLM 26 次，弱引用支持检查为 27/28（其中含 5 道预期拒答），拒答判定 5/5。Hybrid 完成 28 题检索对照，未运行生成。阈值 0.45 未校准，未开 Vision/reranker；实际人民币费用未查账单。
- **P7 产品化收口（部分完成）：** 问答台已提交问句/同句重试；管理员课程重命名/删除 UI；validation 最短启动与四类 Demo。任务记录为后端 pytest 32 passed、前端测试 15 passed、构建通过（主 JS 包约 1.34 MB，有 Vite 500 KB 警告）。这些不是全量回归或真实端到端验收。数据库 dump/资料恢复实操、Demo Reset、成本/资源限制专项验收仍待处理；不先扩展功能。
- **R8 正式通过（2026-10-17）：** 证据 `corpus/local/r8-joint-acceptance-2026-10-17/RESULTS.md` + `UI_FOUR_POINTS.json` + `ui-screenshots/`。API 关键路径与 UI 四点（三角色登录、原页 `#page=`、教师覆盖警告文案、C4 断后端后重试已提交问句）均通过。用户授权由执行器本机浏览器代点 UI。
- 旧库 `univ_course_rag` 与 Fake 库 `univ_course_rag_r7b6` 未被本卡改写；根 `.env` 可能仍指旧库，服务不会自动连 `r7b6_real`。
- **Docling 清理已完成：** 主仓适配代码、专属测试、`scripts/r7b1_run_docling_pages.py` 与 optional extra 已删除；Docling 不是生产路径，PyMuPDF 与页级质量门禁保留，历史结论仍见 [evaluation-results](evaluation-results.md#r7b-4-pause)。依赖声明已删，venv 未卸载 Docling 包；corpus/local 全部证据保留（含 R7B-1/R7B-4）。
- **清理卡已本地提交：** 生产残留导入检查、Ruff、diff 检查通过，parse/ingest 59 passed（临时目录权限处理见施工计划）。提交不含 `新开题资料.md`；未 push。
- 两个 worktree 均保留，不合并、不续跑：`D:\workspace\univ-course-rag-wt\r7b4-offline-freeze`（`feat/r7b4-offline-freeze`）相对 main 无独有提交，但有未跟踪冻结脚本与 `.codex-*.txt`，工作区不干净；`D:\workspace\univ-course-rag-wt\r7b-l1-pymupdf-gate`（`feat/r7b-l1-pymupdf-gate`）相对 main 无独有提交，已有脏区及未跟踪文件，属于 PyMuPDF 路线，并非 Docling 旧路线。本卡均未删除或改写。

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
| R8 | `corpus/local/r8-joint-acceptance-2026-10-17/`（清单+API+UI 四点；**正式通过**） |

## 下一项：R9 冻结与展示材料（可选先补 P7-3 恢复）

1. 演示仍须进程级切到 `univ_course_rag_r7b6_real`（根 `.env` 可能仍指旧库）。
2. 优先：受控 dump/资料恢复验证（P7-3）；Demo Reset / 成本面板按时间。
3. 再进 R9：冻结题集与基线口径、整理展示材料。
4. PHIL-T02 继续按「命中≠答案正确」展示，不粉饰。

不默认 push；不续跑 Docling；不默认 Vision/rerank。

## 后续顺序

R8 已通过 → 受控 dump/资料恢复（Demo Reset 可选）→ R9 冻结与展示材料。不为追求“全功能”扩写未完 P7 可选项并伪装成通过。

## 已知限制（带入后续）

- 心理学纯图/矢量页、历史图内字、线代公式控制字符：文字路径可入库但覆盖不全。
- 同名 `01_introduction.pdf` 必须带 `course_id` 隔离。
- PHIL-T02 类「检索命中但生成拒答」属命中≠答案正确，R8 重点观察。
- 不把 Fake 索引或旧 R7 数字冒充当前四课基线。

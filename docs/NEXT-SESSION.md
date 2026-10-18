# 当前交接

更新：2026-10-18（Asia/Shanghai，R9 冻结身份清单生成后）。

## 当前状态

- **P7 UI 三角色收口已落地（本机提交）：** 系统状态迁至管理员 `/admin/system`；学生/教师业务页去掉运维条；Ask 失败人话且「依据不足≠系统故障」。`npm run build` 与前端测试 15/15 通过。下一项仍为 PPT 视觉复核与固定 Demo 彩排，或你指定的 UI 复验。

- 主仓：`main`（存在尚未 push 的本地提交；交接以本机当前工作区为准）。现场用户未提交文件为 `新开题资料.md`（研究笔记，勿误提交、勿随文档对账提交）。
- **R7B 轻量路线已到 R7B-7 通过：** 独立库 `univ_course_rag_r7b6_real`，17 份 / 385 chunks，SiliconFlow BGE-M3 + 有限 DeepSeek；证据见 `corpus/local/r7b-7-four-course-baseline-2026-10-17/`（忽略区）。答案指标为 AI 预标+引用支持，不是人工事实正确率。
- **R7B-7 指标边界：** 23 道可回答题中 23/23 命中预期文档与页码；Dense 对 28 题调用 LLM 26 次，弱引用支持检查为 27/28（其中含 5 道预期拒答），拒答判定 5/5。Hybrid 完成 28 题检索对照，未运行生成。阈值 0.45 未校准，未开 Vision/reranker；实际人民币费用未查账单。
- **P7 产品化收口（部分完成）：** 问答台已提交问句/同句重试；管理员课程重命名/删除 UI；validation 最短启动与四类 Demo。任务记录为后端 pytest 32 passed、前端测试 15 passed、构建通过（主 JS 包约 1.34 MB，有 Vite 500 KB 警告）。这些不是全量回归或真实端到端验收。数据库 dump + 上传资料/解析产物隔离恢复子项已于 2026-10-18 通过；Demo Reset、成本/资源限制专项验收仍待处理，不先扩展功能。
- **R8 正式通过（2026-10-17）：** 证据 `corpus/local/r8-joint-acceptance-2026-10-17/RESULTS.md` + `UI_FOUR_POINTS.json` + `ui-screenshots/`。API 关键路径与 UI 四点（三角色登录、原页 `#page=`、教师覆盖警告文案、C4 断后端后重试已提交问句）均通过。用户授权由执行器本机浏览器代点 UI。
- **P7-3 受控恢复子项通过（2026-10-18）：** `corpus/local/r9-recovery-2026-10-18/RESTORE-RESULTS.md`、`restore-result.json`、`package-manifest.json`。源库 `univ_course_rag_r7b6_real` custom dump 恢复到隔离库 `univ_course_rag_r9_restore_20261018`；migration 0011、4/17/385、全部 public 表行数、pgvector、17/17 PDF SHA-256/页数/存储边界与 17/17 解析产物来源身份均通过。源库、旧库、Fake 库规模未变；未调用云模型。P7 整体仍部分完成，Demo Reset 与成本/资源专项仍待验。
- **R9 冻结身份清单已生成（2026-10-18）：** `corpus/local/r9-recovery-2026-10-18/freeze/freeze-manifest.json`，摘要 `freeze/R9-FREEZE-RESULTS.md`。记录当前代码提交 `7426103`、最后代码变更提交、Python/前端依赖快照、0011 迁移、17 份 PDF、412 个解析产物、28 道题集、R7B-7 结果与恢复包哈希。R7B-7 历史运行 SHA 缺失、Python 依赖声明未完全锁定等限制已显式记录。
- **中期汇报 PPT v4 初稿已生成并完成结构预览（2026-10-18）：** `build/midterm-presentation/output/final-v4.pptx`；讲稿提示 `build/midterm-presentation/output/speaker-notes-v4.md`；结构校验 `build/midterm-presentation/finalizer/final-v4.validation.json` 通过（10 页、16:9、必要指标齐全、无旧阶段术语、形状均在页面边界内）。低分辨率结构预览已复核，R8 两张 UI 图改为关键区域裁切，原始截图不变；本机没有 PowerPoint/LibreOffice 渲染器，最终字体与换行仍需本机 Office 复核。固定演示步骤见 `docs/midterm-demo-runbook.md`。旧版 `final-v3.pptx` 保留。
- **本轮只读运行预检（2026-10-18）：** 后端 `/health`、`/ready` 与 Vite 根页均返回 HTTP 200；`/runtime` 只报告 `database=available`、`migration/index=not_checked`，不暴露实际库名。尚未确认当前后端进程的数据库身份，因此没有提交真实模型问句；正式彩排前必须核实其确实连接 `univ_course_rag_r7b6_real`（4/17/385），不能仅凭健康检查判断。
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

## 下一项：PPT 视觉复核与固定 Demo 彩排

1. 在本机 PowerPoint 打开 `build/midterm-presentation/output/final-v4.pptx`，检查真实字体、换行、截图可读性与页面留白；旧版 v3 保留，不覆盖。
2. 按 `docs/midterm-demo-runbook.md` 与 `build/midterm-presentation/output/speaker-notes-v4.md` 彩排固定流程：正常回答与原页、资料外问题拒答、教师覆盖警告、服务失败重试、撤权/串课边界。
3. 以冻结清单 `freeze-manifest.json` 中 `code.commit` 为代码基准；未提交的 `新开题资料.md` 继续排除在冻结提交外，不清理两个脏 worktree。
4. 只展示已验证范围与边界：答案指标是 AI 预标/弱引用支持规则，不是人工事实正确率；Hybrid 未跑生成；费用未查账单；R7B-7 历史运行 SHA 缺失、Python 依赖声明未完全锁定。PHIL-T02 继续按「命中≠答案正确」展示，不粉饰。
5. 演示使用 `univ_course_rag_r7b6_real`，不要把隔离恢复库 `univ_course_rag_r9_restore_20261018` 当演示库；不重新入库、不临场换模型、不默认调用云模型。

不默认 push；不续跑 Docling；不默认 Vision/rerank。

## 后续顺序

R8 已通过 → **P7-3 数据库与文件恢复子项已通过** → R9 冻结身份清单已生成 → PPT v4 视觉复核与固定 Demo 彩排。Demo Reset、成本/资源限制专项展示仍可待验；P7 整体不标为全部完成。

## 已知限制（带入后续）

- 心理学纯图/矢量页、历史图内字、线代公式控制字符：文字路径可入库但覆盖不全。
- 同名 `01_introduction.pdf` 必须带 `course_id` 隔离。
- PHIL-T02 类「检索命中但生成拒答」属命中≠答案正确，R8 重点观察。
- 不把 Fake 索引或旧 R7 数字冒充当前四课基线。

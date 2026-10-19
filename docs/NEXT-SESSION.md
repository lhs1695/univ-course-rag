# 当前交接

## 2026-10-19 staff/admin F1–F20（本 worktree）

已按会话角色统一 staff 壳，补教师原文入口及 F1–F20 可做项。F10 无改密/停用 API、F12 真实模型连通未验证、F14 浏览器原生 Network 日志均诚实降级，见 [逐项交付](../NOTES-F1-F20.md)。本次未读 .env、未改后端或学生四页核心交互、未 push；原有执行日志/提示词排除提交。按用户要求外层补 build 与 Playwright 三角色/390px 点击验收，静态检查不能替代浏览器验收。本地提交尝试被 Git 元数据目录 index.lock 写权限阻断，未暂存、HEAD 仍为 9246139；外层按逐项交付的文件范围补本地提交。


更新：2026-10-18（Asia/Shanghai，R9 冻结身份清单生成后）。

## 当前状态

### 教师 / Admin A 品牌对齐（2026-10-19，feat/staff-admin-align-a）

- 管理壳、主操作、导航、表格与反馈/维护面板改为 A 紫色书签品牌，保留稳重表格与操作栏；学生门控、学生模板与 student.css 未改，业务脚本、API、权限与上传入库逻辑未改。
- 交付说明见 [DESIGN-NOTES-STAFF](../frontend/DESIGN-NOTES-STAFF.md)。按用户要求未跑 build，外层需补构建与 Admin / 教师登录后的视觉点验；本次不宣称浏览器操作验收通过。未 push，原有执行提示词与日志未纳入提交。
- 静态验收通过：6 个 Vue 模板与相关 CSS 解析、业务脚本/绑定不变、学生门控/模板/四页/路由不变、A primary 色阶一致、diff 无空白错误。提交尝试因主仓 worktree 索引目录在沙箱写入范围外而被拒（index.lock Permission denied），未暂存、未提交，HEAD 仍为 `f567d42`；外层补本地提交，具体文件范围见设计说明。

### 演示走查 20 条全修（2026-10-19，分支 fix/demo-20-fixes，未合并 main）

- 批次提交（均本地、未 push）：A 后端 QA `2b246ba`、B 公式/摘录 `ff12b4e`、C1 问答历史 `18527be`、C2 页面体验 `410b83b`、A 补修计算召回 `6921eab`、计算生成提示 `c0b75af`、教师清单排除拦截题 `f424ffe`。批 B 的构建阻塞已由 bot 在本机补跑通过，本节覆盖上方批 B 小节中「构建待验」的旧结论。
- 全量回归只跑了一次（证据 `corpus/local/demo-fix-2026-10-19/`，忽略区）：旧 16 题按原合并范围口径检索命中 12/12、拒答 4/4、系统失败 0（引用精确页命中 6/12、must_include 11/12，HR-02 仍为措辞波动）；新四课高频 40 题中可答 36 题答 35（`什么是教学？` 经诊断资料无定义、拒答合理；红白球计算题经补修后已答且引 02-prob 第 55 页）、拒答边界 4/4、系统失败 0。追问专项：无上下文返回 NEEDS_CONTEXT、带上一轮能围绕正态分布作答、纯标点 64ms 返回 INVALID_QUESTION、同题 3 次均引第 60 页且无自贬话术。
- 页面点验（Playwright，证据同目录 ui-acceptance.json 与截图）：学生提问公式 KaTeX 渲染、追问带上下文、切课回来历史仍在、引用链接带 #page=；教师反馈显示本地日期与待核对清单；管理员系统状态显示「已填写配置」且无「未验证连通」。
- 待用户决定：(1) 本分支尚未合并 main——main 工作区有宽召回+rerank 未提交残留（与 ask.py/test_ask.py/engineering.md 重叠），处置（回退/保留/提交）定了再合并；(2) M5 清理：教师待核对中的测试题清单已列在 `m5-cleanup-candidates.json`（23 条不同问句，含走查与本轮回归），未删除任何数据，等确认范围；(3) 演示进程（8000/5173）仍跑 main 旧代码，合并后需按 cn_v2 进程级环境重启才生效。

<a id="batch-b-closeout"></a>

### 批 B 收尾（2026-10-19，代码及定向测试、构建均已验收）

- 已核对原有 diff，保留 `generate.py` 摘录清洗、`answerMarkdown.js` KaTeX 规则、`AnswerBody.vue` 样式，未重做或修改批 A；原有未跟踪 `.codex-prompt-b.txt`、`.codex-prompt-b2.txt` 保留且不纳入提交。
- `frontend/package.json` 与 lock 均固定 `katex 0.19.0`，本机安装版本一致；唯一新增直接依赖 katex，commander 15.0.0 为其传递依赖。用户指定临时 cache 安装首次 `spawn EPERM`，以同一命令追加 `--ignore-scripts` 成功；前端渲染测试确认发行 JS 可用。
- `answerMarkdown.test.mjs` 新增美元行内/行间、反斜杠圆括号、普通圆括号内分式、中文括号/普通文本与 script 同段防注入；`test_source_excerpt.py` 新增页脚/页码/CONTENTS、公式密集、中文、替换字符及生成证据/存储原文不变测试。
- 前端原命令 `node --test frontend/tests/answerMarkdown.test.mjs` 被子进程 `spawn EPERM` 阻断；同文件用 `node --test --test-isolation=none frontend/tests/answerMarkdown.test.mjs` 得 `tests 10 / pass 10 / fail 0`。
- 本工作树没有 `backend/.venv`，使用主仓 `D:/workspace/univ-course-rag/backend/.venv/Scripts/python.exe` 并设 `PYTHONPATH` 为本工作树 backend。定向 `-m pytest backend/tests/test_source_excerpt.py backend/tests/test_ask.py -q -p no:cacheprovider -k "excerpt or generation_context or context_budget or context_skips or context_clips or generate_filters or generate_without or deleted_hybrid_evidence" --tb=short` 得 `25 passed, 46 deselected in 2.24s`；相关三文件 Ruff 得 `All checks passed!`。
- 曾尝试上述两测试整文件：不依赖临时目录的测试通过，44 项在临时目录 fixture 遇环境错误；补临时父目录后仍因 pytest 创建的受限目录报 `PermissionError: [WinError 5]`。未修改测试基础设施，改用上述用户允许的摘录/上下文定向范围；不宣称整文件通过。`.tmp/b-excerpt-pytest-2` 受限目录保留，不清理现有依赖或受控资料。
- 构建验收（bot 补跑）：Codex 沙箱内子进程受 EPERM 限制，bot 在本机工作区 `npm ci` 后 `npm run build` 成功（1669 模块，主 JS 约 1,607.81 kB / gzip 534.77 kB，含 KaTeX 字体资源；仍有 Vite 500 kB 警告）。bot 复跑定向测试：answerMarkdown 10/10、test_source_excerpt.py+test_ask.py 71 passed、ruff 通过。不读 `.env`，不调用云，不重入库，未跑全量回归。

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

## 中文四课换课重跑（2026-10-18 已完成，旧四课已删）

- 新四课已入库隔离库 `univ_course_rag_cn_v1`（0011）：线性代数 1 份/695 chunks、概率论与统计学 12 份/1,620、人力资源管理 8 份/508、教育学原理 6 份/154，合计 27 份 / 2,977 chunks，SiliconFlow BGE-M3（457,231 tokens / 104 批 / 失败 0；幂等复跑 0 新增）。`COVERAGE_INCOMPLETE` 共 20 份（人力 8/8、概率 11/12、线代 1/1、教育 0/6），已如实登记。
- 新题集 16 道（每课 3 答 + 1 拒答，冻结在忽略区证据目录）：命中预期文档+页 12/12、引用支持 12/12（弱规则，非人工正确率）、拒答 4/4、系统失败 0；DeepSeek `deepseek-v4-flash` 16 次共 32,161 tokens。
- 演示已进程级切换到 `univ_course_rag_cn_v1` + 新 uploads（未改 `.env`），API 验收三角色登录、student 新四课与资料、PDF 200、问答引用 page 1 均通过。
- 旧演示库 `univ_course_rag_r7b6_real` 旧四课已删（现 0/0/0，账号保留），旧 uploads 17 份文件已删；备份在 `corpus/local/cn-replace-2026-10-18/backup/`（dump + 17 PDF + SHA-256 清单，恢复方法见证据 `REPORT.md`），保留不删。`univ_course_rag` 与 Fake 库未动。
- 注意：PPT v4 与旧 Demo 彩排口径仍是旧四课数字/截图，正式汇报前需按新四课更新；勿再把旧库当演示库。

## 检索层宽泛问法修复（2026-10-18 已完成，演示已切 cn_v2）

- 三批改动取舍：重切（rechunk，短页 <120 字并入后续正文、CHUNKING_VERSION 已升版）与检索层查询扩展已提交；宽召回+rerank 批次实测无效、最终演示未启用（进程级 `RERANKER_BACKEND=disabled`、dense），其代码仍留在工作区未提交，是否回退待用户定，不要擅自回退。
- 新机制：`QUERY_EXPANSION_BACKEND` 默认 disabled，演示进程级设为 `llm` 复用 DeepSeek。宽泛程序性问法（<=40 字且含如何/怎么/步骤/方法等）先由 LLM 改写为 2 个指向具体方法/步骤的子问题，子分支优先轮询配额合并（各 top-20），准入仍为原问余弦 >=0.45 与 NO_EVIDENCE 门；首次无引用时再扩展重试一次；扩展失败回退原检索。引用格式/页码、权限、阈值未变。定向改写提示词离线 15/15 次把目标正文页带入证据。
- 数据：演示已进程级切到 `univ_course_rag_cn_v2`（27 份 / 2,501 chunks，未改 .env，UPLOAD_DIR 指向 rechunk/uploads_v2），cn_v1 保留不删作回退。API 实测三角色、student 四课资料、PDF 200、原问「如何解线性方程组」经演示页多次作答并引用第 60 页。
- 验收（真实 API，证据在 `corpus/local/cn-replace-2026-10-18/retrieval-layer/`）：16 题按合并范围命中 12/12、拒答 4/4、系统失败 0；答案弱校验按原口径（仅答案文本）为 10-11/12，波动项 HR-02/PB-03 均为措辞口径（答案+被引来源计 12/12，非答错）；宽泛题原问 2/2、同义与新增共 5 道最终轮全部作答并引用步骤/正文页（X2 曾 1 次偶发拒答、复跑 2/2 通过，属 LLM 改写/生成波动）。答案指标仍是弱引用支持规则，不是人工事实正确率。
- 还差：PPT 与彩排脚本按新四课更新；rerank 未提交批次的处置待用户定。

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


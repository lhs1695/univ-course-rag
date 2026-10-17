# 验证与中期重跑指南

更新：2026-10-17。R7 有限对照与运行日志见 [evaluation-results](evaluation-results.md)；R7B **当前施工步骤**见 [轻量解析路线计划](implementation-plan.md#r7b-lightweight-plan)。Docling 代表页和全量试验均为历史记录，不能作为当前主解析路线。本文只保留验收方法与通过/失败门槛。操作规则见 [workflow](workflow.md)。

<a id="r7b-parser-selection"></a>

## R7B 轻量解析路线验收门槛

**路线决定：** 停止 Docling 全量主解析路线，当前目标是恢复现有 PyMuPDF 原生文字提取。生产 PDF 默认已为 PyMuPDF 轻量路径（R7B-L1 已通过）。

### R7B-L1：默认入口与页级质量门禁

| 维度 | 通过证据 |
|---|---|
| 依赖与入口 | 使用现有 PyMuPDF；PDF 默认不再调用 Docling；PPTX/DOCX/Markdown/TXT 路径不受无关影响 |
| 页码完整性 | 报告总页数与 1-based 连续页号一致；空页仍有记录，不静默丢弃；每页文字长度可追溯 |
| 质量标记 | 空页、稀疏页、明显异常字符分别记录；稀疏只作风险提示，不能单凭字符数宣称内容错误或正确 |
| 覆盖与任务状态 | 区分解析执行失败和文字覆盖不完整；已知图像页可在明确显示覆盖警告时索引其余可读文字，但不得显示为内容完整；不可读、页数不一致、意外全空或不可恢复异常必须失败 |
| 索引安全 | 致命解析失败不调用 embedder、不替换旧完整索引；质量警告不会被 UI 显示为普通完整成功 |
| 测试 | Fake/单元测试覆盖空页、稀疏页、页码缺失、全空、部分覆盖警告、失败恢复；运行当前项测试与 Ruff |

本项不安装新依赖、不运行真实课程资料全量解析、不入库、不调用真实模型。代码切换完成前，不得把目标方案描述为现行代码。

### R7B-L2：固定代表页人工核对

从已有 17 份资料 inventory 固定少量页面，覆盖普通文字、线代公式、历史图文/表格、心理学图像页和哲学稀疏页。逐页对照原 PDF 检查缺字、错序、控制字符、公式/表格损坏、页码和引用。样本固定后不得按结果替换；复用既有预检，不先重跑 344 页。只对实际发现的缺口另开定向任务。

**通过证据：** 每类关键风险都有可复核页号和明确结论；尚未覆盖的图片/公式内容清楚标记，不以文字提取成功冒充视觉理解或公式正确。

### R7B-L3：17 份轻量离线冻结

全量前核对原文件 SHA-256/页数，只运行 PyMuPDF 原生文字提取，不运行 OCR、公式增强、表格模型或视觉模型。逐文件/逐页产物记录输入哈希、解析器版本、总耗时、页数、空页/稀疏页/异常页及终态。

- 单文件硬上限 3 分钟，全量硬上限 15 分钟（不含人工核对）。
- 超时立即停止并汇报，不自动重试、不无限续跑、不进入后续阶段。
- 17 份文件均有终态记录、页码/来源可对账，且失败不污染旧索引，才允许进入 R7B-5。
- **状态（2026-10-17）：** R7B-L1…L3 与 R7B-5 已通过；证据见 [evaluation-results 轻量进度](evaluation-results.md#r7b-lightweight-pass)。满足上述门槛后才允许进入 R7B-6 受控入库；当前 R7B-6B/6C 与 R7B-7 状态见 [结果登记](evaluation-results.md)。

四课预检画像见 [evaluation-results](evaluation-results.md#r7b-preflight)；施工步骤见 [轻量解析计划](implementation-plan.md#r7b-lightweight-plan)。

<a id="product-acceptance"></a>

## 当前验收范围

已有 Fake/合成合同测试可用于回归。中期前按实际 diff 和冻结范围重新验证，不能将局部通过数当整个产品或真实效果证明。带日期的实现/联调运行日志见 [evaluation-results](evaluation-results.md#run-logs)。

| 范围 | 直接检查入口/要点 |
| --- | --- |
| 解析/切分/来源 | test_parse.py、test_chunk.py、test_source_metadata_migration.py、test_ingest.py；字符范围、单位隔离、失败保留/成功替换 |
| 检索/重排 | test_keyword.py、test_fusion.py、test_rerank.py、test_retrieve.py；完整候选、课程/索引/排除、评分隔离、失败不回落 |
| 回答/评测 | test_ask.py、test_eval.py；实际上下文、合法引用、拒答/失败、checkpoint配置隔离 |
| 反馈事件/统计 | test_ask.py、test_insights.py、test_query_outcome_migration.py；结果/角色快照、UTC窗口、分母/重试/未知、UTC日趋势与学生合计、历史成员变化、隔离迁移 |
| 候选问题组 | test_question_groups.py；合成向量/完全链接、单例/medoid/计数解释、权限/窗口/上限/错误/依赖关闭。页面不自动 POST；分组 413 与上传 413 的文案分开。真实题对另做人工误合并/误拆分评价 |
| 权限/原文件/留存 | test_auth.py、test_courses.py、test_storage.py、test_insights.py、test_query_log_retention.py；按实际改动选取 |
| 配置/就绪 | test_configuration.py、test_health.py；缺配置不转Fake、状态不冒充连通、错误脱敏 |
| UI | frontend npm run build；相关前端测试与新增控件实际点击。教师反馈包括时间筛选、趋势、待核对问句和需确认的候选组；不重复pytest已覆盖的行为 |

所有pytest在仓库根使用backend/.venv；排除可选云/Postgres标记的离线示例：

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_ask.py backend/tests/test_retrieve.py backend/tests/test_eval.py -m "not integration and not postgres"
backend/.venv/Scripts/python.exe -m ruff check
```

这些是运行入口而非本轮执行记录；按diff补充必要模块，不默认全量。Windows沙箱遇到已确认的TestClient/临时目录权限限制时使用获准的执行方式，将临时目录限定仓库忽略区随机路径，不改测试掩盖环境失败。UI不变时不为文档改动启动浏览器。

<a id="eval-protocol"></a>

## 中期前重新建立数据与基线

1. 先按 [R7B 门槛](#r7b-parser-selection) 验收 PyMuPDF 轻量默认入口和页级质量门禁；不安装新解析器，不恢复 Docling 全量任务。施工顺序见 [轻量解析计划](implementation-plan.md#r7b-lightweight-plan)。
2. 固定可恢复的实际工作区、依赖、迁移、配置与索引身份。包含未提交改动时HEAD不足以标识版本；数据、结构化解析产物与配置恢复副本留受控位置。
3. 离线解析四课资料并核对页级质量。预检分类见 evaluation-results；轻量阶段记录总页、每页文字长度、空页/稀疏页/异常字符、页码连续性、输入哈希、解析器版本与实测耗时。后续若对固定页面使用 OCR/公式/视觉专项，必须分开记录处理方法与模型身份，不将机器派生内容伪装成原生正文。
4. 在明确目标库应用当前迁移、受控重新入库。记录 Document.chunking_version 和当前索引，确认未混 Fake 与真实向量；关键页解析失败不得显示普通成功，不覆盖旧完整索引或自动删除资料。
5. 新建可核对的题集，先标注必需要点、支持文档/页或区域与应否拒答。同知识点改写不跨开发/测试；先开发集校准，再冻结测试集，不按结果删失败题。
6. 取得当次联网/计费授权与预算，分别验证服务可用性，再执行有限规模对照；配置非空不证明云服务可用，浏览器超时不证明计费停止。
7. 运行后审查失败与代表样例，匿名汇总写入evaluation-results；原题/答案、逐题分数/输出、引用UUID和数据库留受控忽略区。

视觉题单独处理：四课新基线的主检索对照不默认把图片发送给模型。若中期做有限视觉问答，先固定少量题目和对应 page/bbox/asset，在另一次明确的 Vision 授权下仅对这些题发送图片；结果记录 visual input、模型身份、调用次数和费用，并与纯文字 RAG 指标分开。

四课新基线预计每课 6–8 题，总量依解析后可用内容确定；至少区分普通正文、公式、表格/图表或图片信息、相近但无答案及资料外问题。R7 实收 24 题仅涵盖旧纯文字 PDF 路径，不代表复杂资料或四课效果。

### 同条件比较

候选顺序为dense → hybrid → hybrid+rerank。保持资料、切分、最终证据数、prompt、生成设置与模型一致；结构切分、模型与回答机制分别比较。当前hybrid仍经保守余弦准入，keyword-only能参与候选/重排但不能自动生成；未补充分性选择时必须按这一实际能力命名实验，不能称完整互补混合问答。

分别统计候选覆盖与最终证据覆盖。RRF、BM25、rerank分不当概率；高相关性不等于包含答案。各向量空间阈值独立开发集重验；当前0.15/0.45是代码配置，不是新版已校准结果。失败、空输出、超时、重试与降级全部计数。

### 工具与人工评价的边界

| 指标 | 判读要求 |
| --- | --- |
| 正确文档Recall@k | 当前CLI衡量最终SearchHit预期文档覆盖；不自动证明正确片段/必需要点找到 |
| 有效引用 | 当前CLI主要检查合法引用ID；人工另核对裁剪后正文是否支持主张，不能称事实正确率 |
| 事实与要点 | 优先依据预先标注的要点与来源人工评价；R7 使用 AI 预标和 AI 评判，单列并披露无人工复核，不能称人工事实正确率 |
| 拒答 | 将应答题的误拒答、应拒答题的误答与系统失败分别报告，标明各自分母 |
| 代价/性能 | 同版本环境报告p50/p95、调用次数/费用与失败；Fake/SQLite耗时不代表真实容量 |
| 权限/生命周期 | 串课、撤权、删除/排除、过期记录不得泄露；不以回答质量测试替代权限检查 |

### 现有CLI

案例文件在受控忽略区，含id、category、query、expected_documents、should_refuse；拒答题expected_documents为空，可回答题非空。删除对照使用excluded_documents，在索引检查和排序前排除，不需要真的删除资料。不要修改测试fixtures/golden.json来迎合结果。

只验证案例的dry-run示例：

```powershell
backend/.venv/Scripts/python.exe -m app.eval --case-file corpus/local/eval-cases.json
```

在获当次授权、配置和资料核验后才执行真实评测：

```powershell
backend/.venv/Scripts/python.exe -m app.eval --case-file corpus/local/eval-cases.json --run --allow-cloud --course-id <课程UUID> --output corpus/local/eval-result-summary.json
```

运行逐题原子保存checkpoint；使用相同参数加--resume恢复，配置/题集元数据不匹配拒绝恢复，异常题重试。当前 CLI 记录检索/重排/生成合同与端点哈希，不自动核验所有资料正文或切分变化；恢复前仍须确认资料/索引/版本冻结，变化后重新开始实验。CLI 输出包含summary/failures/metadata，不保存问题/答案/摘录/key。

<a id="synthetic-benchmark"></a>

## 合成性能检查

现有app.benchmark生成规则Markdown资料，复用正式解析/切分/Fake嵌入/检索，不代表真实语义质量。默认只校验参数；本机SQLite运行示例（输出放忽略区，不新增docs JSON）：

```powershell
backend/.venv/Scripts/python.exe -m app.benchmark --run --database sqlite --scales 100,500,1000 --retrieval-runs 6 --output corpus/local/synthetic-benchmark-sqlite.json
```

Postgres需明确--database postgres --allow-postgres；会临时写入受控库，先核对目标/授权与恢复点。异常中止可能留合成对象，按明确清单核对，不批量清库。规模/批次按CLI上限，资源计数不等于RSS或生产容量。旧性能数值已移除，本轮未重跑。

<a id="demo"></a>

## 演示与恢复

### 最短启动检查（本机）

按顺序核对，任一步失败先停再继续：

1. **数据库**：目标 Postgres 已启动；演示四课真实基线时进程级指向 `univ_course_rag_r7b6_real`（根 `.env` 可能仍指旧库，勿把旧库当 R7B-7 结果）。
2. **migration**：目标库已到最新 Alembic head（当前合同为 `0011`）。
3. **backend**：仓库根用 `backend/.venv` 启动 uvicorn（见 [workflow](workflow.md)）。
4. **frontend**：`npm run dev`；浏览器走 Vite 地址，不直连后端端口登录。
5. **health / ready / runtime**：`/health` 仅进程；`/ready` 仅 `SELECT 1`；`/runtime` 仅本地配置状态。`configured` ≠ 供应商连通或模型可用。
6. **登录**：用固定演示账号进入「我的课程」。

### 四类固定演示（勿临场换模型/重入库）

| 类型 | 预期 |
| --- | --- |
| 正常回答 + 引用核对 | 学生提问 → 有回答 → 右侧引用 → 点「查看原资料」回 PDF 页 |
| 资料外问题 → 依据不足 | 显示 `NO_EVIDENCE`/依据不足，不冒充成功回答 |
| 服务异常 → 系统失败 | 错误态可重试「本次问题」，不显示成依据不足或成功 |
| 撤权 / 串课 → 拒绝访问 | 移出成员或访问未授权课后，下一次请求拒绝 |

持续标明 Fake/真实模式；未实现的逐主张支持、同义组或主题反馈不伪造展示。录屏不拍入凭据、Cookie、学生身份或私密原文。P7 只提供上述可操作说明与 UI 闭环；**真人共同走通记入 R8**，不把开发者自测冒充联合验收或独立试用。

现场演示和答辩材料仍可在 R9 冻结后再制作。恢复包/dump 实操与 Demo Reset 脚本属 P7-3/重点争取，未在本卡强制完成者标待验。

<a id="usability-test-template"></a>
<a id="r8-internal-acceptance"></a>

## P7 中期产品化验收前置

P7 只验证产品闭环与运行边界，不把 UI 美化、数据库恢复或 Demo 准备当成 RAG 质量指标。实施后至少检查：

| 范围 | 最低验收 |
| --- | --- |
| 学生端 | 我的课程 → 进入问答 → 提交问题 → 查看回答/依据不足/系统失败 → 聚焦引用 → 打开原 PDF 页 |
| 教师端 | 查看本课 → 加入已有学生 → 上传资料 → 查看解析/入库状态 → 失败重试 → 查看基础反馈 |
| 管理员 | 创建课程/账号 → 管理成员 → 编辑/删除课程（管理员页已提供重命名/删除；真人操作记 R8） |
| 权限 | 学生串课、撤权后访问、教师越权、原文件越权均拒绝 |
| 生命周期 | 课程/资料删除后不可检索/读取；失败任务不覆盖旧完整索引 |
| 数据库 | 最新 migration 可从干净库建立；dump + 资料/解析产物恢复可按说明完成 |
| 资源限制 | 超限文件/问题/候选得到明确错误；不会无限重试或无限并发 |
| 成本 | 本轮真实调用的模型、次数、usage/账单依据、失败和总费用可追溯；无可靠 usage 不填精确费用 |
| Demo | 固定账号/课程/资料/题目能从启动检查一路跑到引用核对；异常演示与正常回答不混淆 |
| UI | 核心页面视觉一致、空/加载/错误状态明确、小屏基本可操作；不以截图代替功能验收 |

进入 R8 前，必须具备可启动的真实演示环境、核心问答/引用路径与课程权限操作条件；只存在代码而未实际操作的项目仍登记为待验。R8 不要求把所有非核心收尾预先标成通过：数据库 dump + 资料/解析产物恢复仍须在 R9 冻结前实操验证；Demo Reset 与成本/资源限制专项展示可继续明确标为待验，不得影响或伪造 R8 真人验收结果。

## R8 内部联合验收

用户与开发者按实际版本共同操作，逐项记录课程/模式、任务、操作人、结果、卡点、修复与重验。先检查登录与课内权限、资料与入库恢复、问答及引用、依据不足与服务失败、教师反馈，再检查撤权/串课边界。合成浏览器响应和离线合同只作为前置检查，不能记为真实端到端完成。若日后报告非开发者独立试用，仍须另有非开发者独立操作及匿名过程记录；本项不冒称独立试用。前置检查与前端改动运行日志见 [evaluation-results](evaluation-results.md#run-logs)。

可执行勾选清单（含切库、固定验题、成员缺口提示）见受控忽略区 `corpus/local/r8-joint-acceptance-2026-10-17/CHECKLIST.md`；下列为入库勾选模板，现场结果另记 evaluation-results，不把开发者自测标为 R8 通过。

### R8 启动核对

| 检查 | 预期 | 结果 |
| --- | --- | --- |
| 目标库 | 四课真实基线用 `univ_course_rag_r7b6_real`（进程级切库；根 `.env` 可能仍指旧库） | |
| 规模 | 约 4 课 / 17 文档 / 385 chunks；alembic 当前合同 head | |
| 前后端 | uvicorn :8000 + Vite :5173；浏览器只走 Vite | |
| health/ready/runtime | 进程 / `SELECT 1` / 本地配置；`configured` ≠ 供应商连通 | |
| 成员 | 共验前确认 student 已加入演示课（仅有 teacher 成员时先授权） | |

### R8 三角色勾选

| 角色 | 最低操作 | 通过 | 卡点 |
| --- | --- | --- | --- |
| 管理员 | 登录；确认账号；将学生加入演示课；可选重命名（勿删演示四课） | | |
| 教师 | 打开本课资料；核对份数/文件名；确认覆盖警告可见；反馈页空态诚实；未授权课拒绝 | | |
| 学生 | 我的课程 → 提问 → 引用 → 回 PDF 原页；依据不足题；失败重试沿用已提交问句；撤权/串课拒绝 | | |

### R8 四类演示与观察点

| 类型 | 建议题 / 操作 | 预期 | 通过 |
| --- | --- | --- | --- |
| 正常回答 + 原页 | PSY-D01 / LA-D02 / HIST-D01 / PHIL-D01（小样本即可） | 有回答与引用，点回 PDF 对应页；哲学同名 `01_introduction.pdf` 不串心理课 | |
| 依据不足 | PSY-D03（碳-14） | `NO_EVIDENCE`/依据不足，不冒充成功 | |
| 系统失败 | 断后端或 503 后「重试本次问题」 | 重试原问句；错误态 ≠ 依据不足 | |
| 撤权 / 串课 | 移出成员后再问；打开未授权课 | 下一次请求拒绝 | |
| PHIL-T02 观察 | Frege / Hesperus 题 | 允许「检索命中但生成拒答」；记命中≠答案正确，不标系统失败 | |

**R8 通过条件：** 三角色均有真人共同记录；四类演示关键路径通过；连库身份正确；覆盖警告未粉饰；未用 Fake/合成点击冒充。通过后更新 NEXT-SESSION 与 evaluation-results，再进 R9。

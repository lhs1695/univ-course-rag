# 验证与中期重跑指南

更新：2026-10-16。R7 有限对照与运行日志见 [evaluation-results](evaluation-results.md)；R7B **施工步骤**见 [plan 稳妥型开工计划](implementation-plan.md#docling-稳妥型开工计划)。本文只保留验收方法与通过/失败门槛。操作规则见 [workflow](workflow.md)。

<a id="r7b-parser-selection"></a>

## R7B Docling 代表页离线验证（门槛）

下一实现项只验证已确定的 Docling 主解析器：不入库、不生成向量、不冻结题集、不调用云模型。样本约 12–16 页的选取与安装步骤以 plan R7B-1 为准。**只有在用户明确允许较大依赖/模型下载后才安装；最小可行配置，不装全量 extras。** MinerU 不在本项并行运行。

| 维度 | 通过证据 |
| --- | --- |
| 正文与顺序 | 对照原页检查缺字、错序、重复、页眉页脚污染；不只比较字符数 |
| OCR | 纯图像页产生可读文字，原页号不丢；普通文字页不因强制 OCR 明显退化 |
| 公式 | 关键变量、上下标、运算符、矩阵结构与原页一致；LaTeX 可读≠数学正确 |
| 表格/图表/图片 | 表头与单元关系可恢复；图片/图表至少被发现并保留 asset + page，能回原页；派生理解单独记录 |
| 来源定位 | 至少保留原文件哈希、页码、元素类型和解析器/模型版本；优先验证页内 bbox |
| 工程成本 | Windows 与现有硬件可重复运行；记录安装、模型下载、CPU/GPU、峰值资源、逐页耗时和失败 |
| 许可与维护 | 固定包/模型版本和许可；只接公开 API/CLI，不复制解析算法，不引入整套 RAG 框架 |

### 最小资源门槛

- 不执行 `all` extras，不下载与代表页无关的 VLM/音视频等模型。
- 优先本机 Python API/CLI；Docling Serve 非中期必需。
- 先代表页，通过后再全量 17 份；安装/模型明显超本机可接受范围则停在 R7B-1。
- 解析耗时可较长，但必须可重复；中期目标是离线冻结，不是实时上传解析。

**硬失败：** 页码/来源丢失、代表公式系统性错误、关键视觉页无法核对、环境无法稳定复现 → 当前配置不得进入适配。通过后直接采用 Docling；出现明确 blocker 再另开 MinerU 后备项。

### 结构化结果检查要点

至少记录：页级成功/异常/空页与耗时；Text/Formula/Table/Image/Chart 代表元素；page、bbox（可得时）、哈希、parser/model version；native/OCR/formula/image/chart 来源性质分开；asset 能否回原页。检测到图片 ≠ 已理解图片。PARTIAL/FAILED 不得映射成 ingest succeeded。结构化结果与 Markdown 冲突时以结构化结果和原页为准。

### 主解析器决策

1. 先按硬门槛验证 Docling；通过后直接作为唯一主解析器。
2. 不做无收益的平行选型平均分比较。
3. 仅当 Docling 出现明确 blocker 且 MinerU 能稳定解决同一问题时，才另开后备验证。
4. 单项小误差记入页级质量限制，不因此重新选型。

四课 PyMuPDF 预检画像与代表页风险说明见 [evaluation-results](evaluation-results.md#r7b-preflight)。

<a id="product-acceptance"></a>


## R7B-2 Docling 薄适配器（门槛）

| 维度 | 通过证据 |
|---|---|
| 入口替换 | PDF 走 `docling_adapter`；MD/TXT/DOCX/PPTX 原路径 |
| 项目模型 | Fake 可验证 Text/Formula/Table/Image/Chart + method/bbox/status |
| 安全失败 | 无 Docling → 既有 `ParseError`；失败/空文不冒充成功 |
| 回归 | `test_docling_adapter` + `test_parse` + Ruff；无关合同未破坏 |

步骤见 [plan R7B-2](implementation-plan.md#docling-稳妥型开工计划)。本项不入库、不调云。

## R7B-3 页级质量、来源和失败状态（门槛）

| 维度 | 通过证据 |
|---|---|
| 页级报告 | Fake 验证总页、成功/异常/空页计数和页号、连续性/缺页、逐页元素与方法计数；空页计入异常并降为 PARTIAL |
| 解析身份与耗时 | parser_version、已知元素模型集合、方法摘要；实测整次转换耗时，未测逐页为 None，可注入 Fake 页耗时 |
| 结构化来源 | page/bbox 保留；canonical JSON 的 SHA-256 对耗时稳定，对来源结构变化敏感；成功 PDF 片段带 parser_version/structured_hash |
| 硬失败 | converter PARTIAL/FAILED、空页不能成为 ingest succeeded；Fake 重入库失败保留旧片段、来源、版本和质量计数，且不调用 embedder |
| 回归 | `test_docling_adapter`、`test_parse`、`test_ingest` 与触及文件 Ruff；无 Docling/模型安装要求 |

R7B-3 仅证明 Fake/合成合同；17 PDF 内容质量、逐页实测和离线产物冻结留 R7B-4。步骤见 [plan](implementation-plan.md#docling-稳妥型开工计划)。

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

1. 先按 [R7B 门槛](#r7b-parser-selection) 固定 Docling 包/模型版本、许可、运行方式和代表页结果；未通过不得进入四课正式解析。实际安装前另确认较大依赖/模型下载授权。施工顺序见 [plan](implementation-plan.md#docling-稳妥型开工计划)。
2. 固定可恢复的实际工作区、依赖、迁移、配置与索引身份。包含未提交改动时HEAD不足以标识版本；数据、结构化解析产物与配置恢复副本留受控位置。
3. 离线解析四课资料并核对页级质量。预检分类见 evaluation-results；Docling 阶段再记录总页、成功/异常页、原生文字/OCR/公式/表格/图片/图表、解析器和模型版本、结构化产物哈希。机器识别结果与原生正文分开。
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

现场演示和答辩展示材料暂缓。日后安排演示时，在当前迁移/新资料/新结果核验后，使用隔离演示课程：教师上传并检查任务与来源版本 → 学生提问核对引用/原文件 → 相关无答案与服务失败 → 教师查看真实反馈 → 删除/失权后旧入口拒绝 → 管理员先dry-run再按授权维护。

持续标明Fake/真实模式，未实现的逐主张支持、同义组或主题反馈不伪造展示。准备重启服务、重新登录、失败任务恢复与安全录屏；不拍入凭据、学生身份或私密原文。录屏与材料对应冻结后的版本/资料/结果，不把开发者走位称独立试用。

<a id="usability-test-template"></a>
<a id="r8-internal-acceptance"></a>

## P7 中期产品化验收前置

P7 只验证产品闭环与运行边界，不把 UI 美化、数据库恢复或 Demo 准备当成 RAG 质量指标。实施后至少检查：

| 范围 | 最低验收 |
| --- | --- |
| 学生端 | 我的课程 → 进入问答 → 提交问题 → 查看回答/依据不足/系统失败 → 聚焦引用 → 打开原 PDF 页 |
| 教师端 | 查看本课 → 加入已有学生 → 上传资料 → 查看解析/入库状态 → 失败重试 → 查看基础反馈 |
| 管理员 | 创建课程/账号 → 管理成员 → 编辑/删除课程（若 UI 已补齐） |
| 权限 | 学生串课、撤权后访问、教师越权、原文件越权均拒绝 |
| 生命周期 | 课程/资料删除后不可检索/读取；失败任务不覆盖旧完整索引 |
| 数据库 | 最新 migration 可从干净库建立；dump + 资料/解析产物恢复可按说明完成 |
| 资源限制 | 超限文件/问题/候选得到明确错误；不会无限重试或无限并发 |
| 成本 | 本轮真实调用的模型、次数、usage/账单依据、失败和总费用可追溯；无可靠 usage 不填精确费用 |
| Demo | 固定账号/课程/资料/题目能从启动检查一路跑到引用核对；异常演示与正常回答不混淆 |
| UI | 核心页面视觉一致、空/加载/错误状态明确、小屏基本可操作；不以截图代替功能验收 |

P7 通过后才进入 R8 内部联合验收。若某一项只是“代码存在”而未真实操作，登记为待验，不标为通过。

## R8 内部联合验收

用户与开发者按实际版本共同操作，逐项记录课程/模式、任务、操作人、结果、卡点、修复与重验。先检查登录与课内权限、资料与入库恢复、问答及引用、依据不足与服务失败、教师反馈，再检查撤权/串课边界。合成浏览器响应和离线合同只作为前置检查，不能记为真实端到端完成。若日后报告非开发者独立试用，仍须另有非开发者独立操作及匿名过程记录；本项不冒称独立试用。前置检查与前端改动运行日志见 [evaluation-results](evaluation-results.md#run-logs)。

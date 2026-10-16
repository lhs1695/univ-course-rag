# 验证与中期重跑指南

更新：2026-10-16。R7 已有新隔离库/单课程真实模型的有限对照，AI 预标且无人工复核；不能当作广泛课程正确率。结果见 [evaluation-results](evaluation-results.md)，操作规则见 [workflow](workflow.md)。

<a id="r7-check"></a>

## 最近一次真实对照检查：R7（2026-10-16）

- 先核对 main / 9214ac3 工作区干净；新隔离 PostgreSQL 16.15 / pgvector 0.8.7 从空库迁移到 0011，迁移前后与入库后受控恢复包分开保存。原长期目标库没有验证或迁移。
- 四份 MIT 官方 PDF 按原字节 SHA-256 匹配，资料清单/许可例外/切分版本与题集先冻结；新课四个入库任务成功、257 片段，索引均为真实 `BAAI/bge-m3` 1024 维。`backend/.venv/Scripts/python.exe -m app.eval --case-file` dry-run 验证 24 个案例有效。
- 先跑 4 个开发集试题，再完成 dense 与 hybrid 各 24 题；共 48 次查询、46 次生成、零重试。受控脚本核对源/题集/索引/代码哈希、逐次保存输出与用量，并做 AI 要点评判；原题/答案及逐题输出留 `corpus/local`。实际分母、失败、延迟和费用估算见 [结果登记](evaluation-results.md)。
- 没有改产品 Python 或 UI 代码，没有以 P6 的 95 项合成测试或页面点击充当效果。未运行全量产品回归、权限/串课、重排、故障注入、PPTX/DOCX、非开发者试用；这些状态均为待验。

<a id="p6-check"></a>

## 最近一次实现检查：P6（2026-10-15）

- backend/.venv/Scripts/python.exe -m pytest backend/tests/test_insights.py backend/tests/test_question_groups.py backend/tests/test_ask.py -m "not integration and not postgres"：95 passed。backend/.venv/Scripts/python.exe -m ruff check 通过。SQLite/Fake，未启动目标库；趋势断言覆盖学生 UTC 日、失败/未知、教师与未知角色排除、空日为 0，以及四项合计等于 student_attempts。
- node --test frontend/tests/insightTrend.test.mjs frontend/tests/recovery.test.mjs：11 passed。UTC 日标签不随本地时区改写；QUESTION_GROUPING_LIMIT 的 413 要求缩小时间范围，上传 413 仍是 15 MB 文案，两者都不回显原始响应。
- frontend npm run build 通过（Vite 7.3.6）。新增 Chart.js 后主包仍超过 500 kB 的既有警告，构建成功。
- 浏览器使用 Vite http://localhost:5173 ，接口由合成响应代替，未连接数据库或云模型。实际点击「最近 7 天」「按此时间统计」「使用留存窗口」「刷新统计」、阈值输入、外发确认、生成候选组和成员展开。筛选 GET 带 start_at/end_at 且不 POST；恢复留存窗口的 GET 不带时间参数，并清除外发勾选、不 POST。确认前按钮禁用；POST 带已应用窗口、阈值和 confirm_external_processing。页面显示失败/未知、未校准、未调用嵌入、候选与单例、排除量。413 分组上限不显示 15 MB 或原始 message。浏览器把该 413 记为资源加载错误，页面文案仍是缩小时间范围。
- 未读 .env 或真资料，无模型调用、迁移、提交或部署。此前 P5 的 84 项通过不是本项结果，也不能证明分组效果。真实阈值、语义质量和 Postgres 按日 SQL 仍待验。

<a id="product-acceptance"></a>

## 当前验收范围

已有Fake/合成合同测试可用于回归；本次 R7 检查见上文，P6 检查仅为上一实现项。中期前按实际diff和冻结范围重新验证，不能将局部通过数当整个产品或真实效果证明。

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

1. 固定可恢复的实际工作区、依赖、迁移、配置与索引身份。包含未提交改动时HEAD不足以标识版本；数据与配置恢复副本留受控位置。
2. 在明确目标库应用当前迁移、受控重新入库。记录资料来源/许可/哈希、Document.chunking_version和当前索引，确认未混Fake与真实向量；不覆盖旧库或自动删除资料。
3. 新建可核对的题集，先标注必需要点、支持片段/位置、预期文档与应否拒答。同知识点改写不跨开发/测试；先开发集校准，再冻结测试集，不按结果删失败题。R7 因无法安排人工，按用户授权使用 AI 预标/评价并明确无人工复核；后续人工核验不能回写成 R7 已完成。
4. 取得当次联网/计费授权与预算，分别验证服务可用性，再执行有限规模对照；配置非空不证明云服务可用，浏览器超时不证明计费停止。
5. 运行后审查失败与代表样例，匿名汇总写入evaluation-results；原题/答案、逐题分数/输出、引用UUID和数据库留受控忽略区。

首轮可从20–30个可核对案例起步，完整研究约80题是设计目标，均不表示已经收集。R7 实收 24 题仅涵盖 PDF 事实/跨页/相似无答案/资料外/排除文档；PPTX/DOCX/文本和串课待验。实际缩减须披露题型和分母，不能按高分选题。

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

运行逐题原子保存checkpoint；使用相同参数加--resume恢复，配置/题集元数据不匹配拒绝恢复，异常题重试。当前 CLI 记录检索/重排/生成合同与端点哈希，不自动核验所有资料正文或切分变化；恢复前仍须确认资料/索引/版本冻结，变化后重新开始实验。CLI 输出包含summary/failures/metadata，不保存问题/答案/摘录/key。R7 本次使用忽略区内另一个有调用/费用停止边界的受控运行脚本，冻结源与代码哈希并逐题私存上下文和输出；它不是生产评测入口，其脱敏汇总才进入文档。

<a id="synthetic-benchmark"></a>

## 合成性能检查

现有app.benchmark生成规则Markdown资料，复用正式解析/切分/Fake嵌入/检索，不代表真实语义质量。默认只校验参数；本机SQLite运行示例（输出放忽略区，不新增docs JSON）：

```powershell
backend/.venv/Scripts/python.exe -m app.benchmark --run --database sqlite --scales 100,500,1000 --retrieval-runs 6 --output corpus/local/synthetic-benchmark-sqlite.json
```

Postgres需明确--database postgres --allow-postgres；会临时写入受控库，先核对目标/授权与恢复点。异常中止可能留合成对象，按明确清单核对，不批量清库。规模/批次按CLI上限，资源计数不等于RSS或生产容量。

重复同环境/设置测趋势，报告实际chunk数、批次与检索延迟及失败；不得沿用旧版本JSON作新版基准。旧性能数值已移除，本轮未重跑。

<a id="demo"></a>

## 演示与恢复

在当前迁移/新资料/新结果核验后，使用隔离演示课程：教师上传并检查任务与来源版本 → 学生提问核对引用/原文件 → 相关无答案与服务失败 → 教师查看真实反馈 → 删除/失权后旧入口拒绝 → 管理员先dry-run再按授权维护。

持续标明Fake/真实模式，未实现的部分依据/同义组/主题反馈不伪造展示。准备重启服务、重新登录、失败任务恢复与安全录屏；不拍入凭据、学生身份或私密原文。录屏与材料对应冻结后的版本/资料/结果，不把开发者走位称独立试用。

<a id="usability-test-template"></a>

## 独立试用登记

至少一名非开发者独立完成任务，实际参与后才填写匿名记录：版本/模式、任务、是否独立完成、耗时/卡点、原话反馈的匿名摘要、恢复情况与下一步修改。研究者介入必须记录；开发者代点、合成演示或历史走位均不能替代。当前仍待完成，不保留空模板中的示例数字作结果。

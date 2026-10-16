# 现行工程合同

更新：2026-10-16。本文记录当前代码行为、复用与许可；任务见 [施工计划](implementation-plan.md)，验收方法见 [validation](validation.md)。R7 有限真实运行见 [结果登记](evaluation-results.md)，不改变本合同默认设置。

## 目录

- [权限与产品](#product-contracts)
- [复用与许可](#open-source-selection)
- [检索与证据](#retrieval-contract)
- [切分与来源](#chunk-source)
- [入库恢复](#ingest-recovery)
- [上传文件](#storage-lifecycle)
- [日志留存](#query-log-retention)
- [异常与恢复](#异常与恢复)

<a id="product-contracts"></a>

## 权限与产品

登录使用 HTTP-only Cookie session_id 与服务端 Session，不使用 JWT/localStorage token。全局角色来自 /auth/me；课程内容按当前 CourseMember.role 鉴权，全局教师或管理员身份不自动获得课程内容权限。仅 admin 可 POST /admin/users、GET /admin/users。

课程响应给出 membership_role 与 can_manage_documents/can_manage_members/can_view_insights。成员可读取本课资料、原文件、检索和问答；课内教师管理资料/学生并查看反馈。普通学生不能读课程成员名单；管理员可管理授权，查看正文仍须显式入课。普通账号绑定受全局 teacher/student 约束，admin 可显式指定其课内角色。改课内角色可移出后重新加入，不存在独立角色更新接口。

后端逐请求查会话、用户与成员，撤权无需重新登录。前端导航、focus/重新可见时刷新身份/能力，401 或课程权限失效时卸载受保护视图，迟到响应不覆盖新状态。无服务端推送，静止且无请求页面不会即时获知远端撤权。

界面为学生问答/证据双列工作台（900px及以下堆叠）与简洁后台；按能力显示入口。回答直接复用 markdown-it 15.0.2 显示 Markdown，禁用原始 HTML、普通链接/图片/自动链接；这些内容按文字显示，不发起生成文本指定的导航或图片请求。仅服务端返回引用列表内的 UUID 标记转换为编号，重复引用共用编号，未知编号显示“未登记引用”，代码中的标记保留文字。点击内联编号滚动并聚焦相应证据卡；资料名/正文仍以 Vue 插值显示，原资料入口保持鉴权。渲染器不启用额外插件或高亮器，只有受控 renderAnswer 输出可传给 v-html。基本键盘焦点、长内容换行不等于完整无障碍认证。

回答保留“已返回回答·请核对证据”、依据不足、服务/索引失败三类显示，不新增“部分依据”或“完全支持”标签；当前没有经验证的逐主张支持判断。索引不兼容单独显示为异常，不提示成资料没有答案。引用合法只表示来源登记，不证明答案正确。

问答工作台提交时保存本次问句快照并在回答区显示；编辑后续草稿不会改变已提交问句，失败时“重试本次问题”仍发送该快照。直接复用现有 Vue 3 状态和 Element Plus 按钮，不引入新组件或依赖；本地只保留请求与草稿的对应关系。现成表单控件不持有本项目的已提交请求身份，引入状态管理包会增加依赖和迁移成本，故用短小页面状态适配。验收为编辑草稿后点击重试，两个请求体仍为原问句且草稿保留。

教学反馈按最终事件结果和提问时课内角色计数。页面用已安装的 Element Plus 时间选择器提交可选窗口，并展示服务端返回的实际窗口、样本量、分母、失败/未知/非学生/角色未知与刷新失败。趋势是同一次统计里的学生 UTC 日计数，直接用 Chart.js 堆叠柱，空日为 0。基础问句列表仍折叠空白并截断 200 字符，可能合并相同前缀，不是同义组。候选分组仍是默认关闭的独立 POST：加载、刷新或改时间都不调用；教师须自行填写未校准阈值并勾选本次外发确认。候选、单例、排除量以及未启用/超限/失败分开显示，分组超限不能显示成上传文件过大。聚合受课内教师权限、时间窗/留存与隐私约束，不建学生掌握度画像，不凭高频、依据不足或候选相似度断言教学缺失或已验证同义。

<a id="open-source-selection"></a>

## 复用与许可

路线为开源组件复用与课程适配，不声称原创 BM25、RRF、模型或切分算法。实际使用方式如下；完整复用决策规则见 [workflow](workflow.md#reuse-gate)。

### R7B 开源选型（已定结论）

**已定：Docling 为唯一主解析器；接入并通过验收后更新本文「切分与来源」现行合同。** 施工步骤见 [plan 稳妥型开工计划](implementation-plan.md#docling-稳妥型开工计划)；验收门槛见 [validation](validation.md#r7b-parser-selection)。当前尚未安装接入，不以计划合同冒充现行行为。

| 对象 | 角色 |
| --- | --- |
| Docling | 唯一主解析器（MIT 代码；模型许可另核） |
| MinerU | 仅 Docling 明确 blocker 时的后备，不并行维护生产管线 |
| PyMuPDF4LLM / PaddleOCR | 低成本逃生或专项 OCR 后备，非主方案 |
| RAGFlow / Kotaemon / Dify / RAG-Anything / FlagEmbedding 等 | 只借鉴局部设计（parser 可替换、citation UX、元素分型、hybrid/rerank）；不整体迁移 |

**不选完整平台接管的原因（短）：** 本项目已有 FastAPI + Postgres/pgvector + Vue 骨架，整体换 RAGFlow/Dify/Kotaemon 重验成本高于收益；当前阻塞在解析与来源质量，不在图谱/Agent；PyMuPDF4LLM/PaddleOCR 不能单独覆盖中期公式+扫描+图表目标。更长选型讨论见 git 历史。

**Docling 运行原则（R7B-1 已验证）：** 最小必要依赖（`docling==2.140.0`，含 RapidOCR/公式所需，**禁止** `docling[all]` 与默认 VLM/SmolDocling）；只在 ingestion/离线脚本加载；单机低并发；记录包版本、下载体积、峰值 RAM、耗时与失败。本机模型缓存优先 C:：`DOCLING_ARTIFACTS_PATH` / `DOCLING_CACHE_DIR` / `HF_HOME`（用户级环境变量，无密钥入仓）。可选依赖见 `backend/pyproject.toml` 的 `docling` extra。许可拆成代码包 / 模型权重 / 素材 / 托管服务四层分别核对。

### 已接入与已评估组件

| 对象与版本 | 实际采用方式/来源 | 许可与本地工作 |
| --- | --- | --- |
| SciPy 1.18.1 / 现有 NumPy 2.5.4 | P5 直接调用 scipy.spatial.distance.pdist/squareform 与 scipy.cluster.hierarchy.linkage(method=complete)/fcluster(criterion=distance)；[官方API](https://docs.scipy.org/doc/scipy/reference/generated/scipy.cluster.hierarchy.linkage.html)、[发行版](https://pypi.org/project/scipy/1.18.1/) | SciPy主体BSD-3-Clause，二进制捆绑许可随wheel保留，不推断全部依赖同许可。只安装二进制包，不下载权重；相较 scikit-learn 1.9.1（BSD-3-Clause，AgglomerativeClustering），直接SciPy只新增一个包，避免额外joblib/threadpoolctl。未复制算法；本地仅做课程/窗口/角色筛选、计数、向量校验/上限、代表问句与解释字段。嵌入直接复用现有SiliconFlow API适配（默认关闭的新POST入口），Fake仅注入合成语义向量，不使用词项哈希冒充同义。阈值请求必填、未校准，不称已验证同义；验收语义对/负例、链式误合并、单例/代表问句、权限/留存及失败不回退 |
| SQLAlchemy 2.0.52 / Alembic 1.19.1 | P4 直接复用已有 select/func.count/group_by、UTC范围过滤与 op.add_column；本机元数据均为MIT，[聚合API](https://docs.sqlalchemy.org/en/20/tutorial/data_select.html#aggregate-functions-with-group-by-having) | 无新依赖；本地只定义最终结果、课内角色快照、分母与旧数据未知规则。两个可空列迁移不回填，兼容现有响应字段。独立 PostHog 事件/分析服务仍需上述课程口径与鉴权/留存适配并增加部署或外发数据边界，[官方自托管说明](https://posthog.com/docs/self-host)不推荐生产自托管；本项未安装/调用/复制平台源码，直接调用现有数据库组件总成本更低。验收角色变化、拒答/失败、重试、时间边界、旧记录与迁移 |
| Chart.js 4.5.1 | P6 直接调用 tree-shake 入口 BarController、BarElement、CategoryScale、LinearScale、Legend、Tooltip 和 `new Chart`；[npm 发行版](https://www.npmjs.com/package/chart.js) 核对 4.5.1/MIT，固定 package 与 lock。随包安装 @kurkle/color 0.3.4/MIT，未复制源码 | 对比 Apache ECharts 6.1.0（Apache-2.0，发行包解压约 60MB，含地图和多图表平台）及 vue-echarts 8.3.2/MIT（还需 peer echarts ^6）；对比 uPlot 1.6.32/MIT（解压约 0.5MB，但堆叠分类图例要补更多本地坐标代码）；对比 vue-chartjs 5.3.4/MIT（额外包装层）。Element Plus 2.14.5 没有图表组件。本地只把同一次 GET 的 UTC 日计数交给堆叠柱，不在前端补零或改口径 |
| Element Plus 2.14.5 DatePicker | 直接调用已安装的 el-date-picker `datetimerange` 与 shortcuts；lock 为 2.14.5/MIT，未升到核对时的 2.14.7。组件自带 dayjs 锁定 1.11.23/MIT，不另加日期库 | 时间筛选无新依赖。页面把选择转成带时区的 ISO，只在点击后 GET；服务端仍裁剪留存窗口。快捷项不是已校准的统计周期 |
| markdown-it 15.0.2 | R6 直接调用 MarkdownIt/render 与 inline ruler；npm registry 核对版本/MIT，固定 package 与 lock。[上游安全规则](https://github.com/markdown-it/markdown-it/blob/master/docs/safety.md) | 关闭 HTML、自动链接及图片/普通链接导航，仅受控来源引用可定位；本地只做 Source UUID→卡片编号/焦点。新增7个npm包，无Python依赖/模型或算法复制。对比 Marked 18.1.1（registry/MIT，[官方说明](https://github.com/markedjs/marked#warning--markdown-sanitizing)要求另行清洗 HTML），当前无需任意 HTML，采用 markdown-it 上游禁用 HTML 方案，减少清洗配置与DOM测试依赖，未安装Marked/DOMPurify。现有平台引用引擎仍不能代替课程鉴权与实际正文预算，保留短小白名单适配。验收为恶意 Markdown/伪引用/代码引用及实际卡片点击，不宣称自动事实核验 |
| jieba 0.42.1 | 直接调用搜索分词，HMM=False；[版本来源](https://pypi.org/project/jieba/0.42.1/) | MIT；本地做统一预处理、术语与资源适配，不改算法 |
| rank-bm25 0.2.2 | 直接调用 BM25Okapi/get_scores；[版本来源](https://pypi.org/project/rank-bm25/0.2.2/) | Apache-2.0；预分词输入、范围与候选合同适配 |
| NumPy 2.5.4 | BM25 的实际依赖，pyproject 固定版本 | 元数据许可表达式 BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0；保留发行包捆绑声明 |
| 本地 RRF / Haystack v2.18.1 | 本地 fuse_rrf；对比 [DocumentJoiner 固定源码](https://github.com/deepset-ai/haystack/blob/v2.18.1/haystack/components/joiners/document_joiner.py)，未安装/复制 Haystack | 上游 Apache-2.0，仅参考；现有同分名次、可配偏移、原分隔离与ID校验仍需本地适配，替换少量累加循环不足抵消迁移/重验 |
| SiliconFlow v1 rerank / BAAI/bge-reranker-v2-m3 | 已写现成 API 薄适配，默认关闭；[固定规范](https://github.com/siliconflow/siliconcloud/blob/ab00eefcf075f0374165d47b8aad3d284f3a1a9a/openapi.yaml) | 规范1.0.0为MIT，模型卡为Apache-2.0；真实服务未调用，托管权重revision不可锁定 |
| HTTPX 0.28.1 | 直接调用公开HTTP API，已有包补为固定运行时依赖 | BSD-3-Clause；请求/ID/上限/错误映射；未自写推理。对比 FlagEmbedding 1.4.2（MIT）本机方案需额外依赖/权重/硬件，当前未采用 |
| semantic-text-splitter 0.33.0 | 直接调用 MarkdownSplitter/TextSplitter/chunk_indices；[版本来源](https://pypi.org/project/semantic-text-splitter/0.33.0/) | MIT；本地只做来源/页/范围/版本适配。对比 langchain-text-splitters 1.0.0（MIT）需额外core依赖与来源映射，未采用；没有复制算法 |
| python-docx 1.2.0 | 直接调用 iter_inner_content 保持顶层段落/表格顺序；版本固定 | MIT；抽取与来源适配 |
| PyMuPDF / python-pptx | 沿用当前解析依赖；本机核对版本为1.28.2/1.0.2 | 具体发行包声明随依赖保留，正式交付重新核对实际版本与发行方式；不由本表推断所有依赖同许可 |
| LlamaIndex citation query engine | 仅作来源组织设计参考，未接入其数据库/鉴权/运行时 | 保留必要课程Source/实际上下文合同，不称已集成框架 |

R7B-1 已在本机装入最小 Docling 并完成 16 代表页离线验证（通过，带登记限制）；**生产解析路径仍是纯文字 PyMuPDF，未切换。** 组件、模型、托管服务的许可/费用分别核对；代码包许可不能代替模型或服务条款。MinerU 只保留为 blocker 后备。

SciPy安装为CPython3.12 Windows二进制wheel（36.7MB），仅新增SciPy包，元数据要求NumPy>=2.0,<2.8，与现有2.5.4兼容，pip check通过；原始许可位于scipy-1.18.1.dist-info/LICENSE.txt，包含实际捆绑声明，随依赖保留。没有复制其源码、安装scikit-learn/模型平台或下载权重。

### 制品归属

以下为仍使用的组件制品追溯，不是课程实验数据或全项目锁文件；其他平台wheel哈希不同。正式交付须随制品保留实际完整许可及捆绑依赖声明。

| 制品 | SHA-256 |
| --- | --- |
| jieba 0.42.1源码包（本机构建wheel） | 055ca12f62674fafed09427f176506079bc135638a14e23e25be909131928db2 |
| rank-bm25 0.2.2 | 7bd4a95571adadfc271746fa146a4bcfd89c0cf731e49c3d1ad863290adbe8ae |
| NumPy 2.5.4 Windows CPython3.12 wheel | a7b1b6353e36a7e50de2973a38d705c88ee93adcf120673cee7f45a4a3fa223a |
| semantic_text_splitter-0.33.0-cp310-abi3-win_amd64.whl | b74eb60519c0b012087184b4997f6ab599c055cca98b194f5bb44b4c5ba2bc7e |

splitter默认无额外Python运行时依赖，不启用tokenizer/docs/test extras或模型。其0.33.0源码包哈希为6d5db802af52ce6a2a2035f4e72f22b46d346bd0850fd9ca97011f8841aa7826，只在内存核对制品，未执行源码。jieba本机构建wheel与splitter wheel未附完整LICENSE文本，故在本文保留归属与许可；splitter类型以版本元数据MIT为据，完整文本来自上游公开LICENSE.txt，不把main称作固定版本源码核验。已有依赖的dist-info/SBOM与许可不删除。

jieba [上游许可](https://github.com/fxsjy/jieba/blob/v0.42.1/LICENSE)：

```text
The MIT License (MIT)

Copyright (c) 2013 Sun Junyi

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
```

semantic-text-splitter [上游许可](https://github.com/benbrandt/text-splitter/blob/main/LICENSE.txt)：

```text
MIT License

Copyright (c) 2023 Benjamin Brandt

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

<a id="retrieval-contract"></a>

## 检索与证据

### 候选与排序

retrieval_strategy 仅接受 dense/hybrid，默认dense；默认最终top_k=8。Fake最低余弦0.15、SiliconFlow最低余弦0.45是当前配置，均须在新版实验中独立重验，不当作新版本已校准结果；清理文档不修改代码参数。两种向量空间不得混用。

两路召回先限制当前授权课程、相容embedding索引身份、排除文档。dense保持原向量排序/阈值；hybrid通过 retrieve_hybrid_candidates 返回完整有界并集：dense召回阶段不使用最终min_score，lexical依词项交集产生候选。每路candidate_k默认32、上限100；HTTP使用max(32, top_k)，最终0不查库。Postgres范围过滤、距离排序和LIMIT在SQL执行；SQLite/Fake沿用点积测试约定。

词项预处理统一NFKC/casefold；中文jieba搜索分词，ASCII标识符/数字/连字符/C++/C#保留。查询去重、正文保留词频，不额外停用词/词干化。BM25Okapi参数k1=1.5、b=0.75、epsilon=0.25；有交集可保留零/负BM25分，无交集不固定填数。语料只在请求内构建，不缓存课程正文/token/排名；SQL读取正文前先过滤、只投影有限正文及元数据，不取向量，超限整次失败。

| lexical资源上限 | 值 |
| --- | --- |
| 切片数/每片字符/总字符 | 2000 / 8000 / 2,000,000 |
| 每片token/总token | 2048 / 200,000 |
| 查询字符/token | 2000 / 256 |
| Top-K/排除文档数 | 0–100 / 1000 |

KeywordLimits只可收紧。RRF按chunk ID去重，分支内同分共享竞争名次，默认k=60、可配1–10000；同融合分按UUID稳定排序。融合上限为两路预算之和，最大200；cosine_score、bm25_score、rrf_score与两路名次分别保留。身份冲突、分支内重复ID、非有限分拒绝合并，失败不返回部分分支。

### 可选重排

RERANKER_BACKEND默认disabled，不创建HTTP客户端；只接受siliconflow与hybrid组合，使用SILICONFLOW_API_KEY，model/base_url控制模型与发送目的地。未知后端、fake、dense+启用、缺配置明确失败；FakeReranker只供测试注入，不按词项交集伪装模型。

重排在完整并集上重新核验当前课、索引、排除、存在性与文档/页身份，只读取正文前1200字符。空前缀跳过；最多64候选、查询2000字符，超过候选上限整次失败，不只取前64。请求top_n等于全部发送候选数，return_documents=false；按严格整数index和有限relevance_score验证完整覆盖、无重复/越界/遗漏，按输入位置映回ID。上游回显正文不用作来源。

每次单POST，以with关闭客户端；无自动重试、重定向或环境代理。复用UPSTREAM_TIMEOUT_SECONDS作为HTTPX各IO阶段超时，不承诺总时长。rerank_score独立保存，按分数降序，同分保留RRF顺序；它不是答案支持概率。

### 最终准入与引用

retrieve_chunks仅返回最终SearchHit。hybrid在完整候选（可选重排之后）先检查已有dense余弦分与该空间min_score，再按当前顺序取最终Top-K。无余弦/低余弦的keyword-only支持片段也仍会被拒绝，等待经验证的充分性选择；不能仅凭词项交集、RRF或重排高分放行。SearchHit.score只承载余弦，不覆盖为其他分数。默认dense不调用关键词或重排。

assemble_ask_context同次生成prompt、允许Source ID和对应正文快照。只有仍存在、正文非空且实际装入预算的块才登记ID；不以摘要兜底。每片正文strip后最多1200字符，来源块累计6000字符（含Source标头和块内换行，不含说明/问题/块间分隔），首个超预算块停止装配。全部不可用不调用LLM；生成后仅登记同一白名单中的引用。问答 CitationOut.snippet 改为该次生成中对应正文的完整快照（最多1200字符），不再使用检索摘要；搜索 API 摘要合同不变。只返回被引用来源；卡片不表示全部上下文，也不回读或补足裁剪尾部。

系统提示和上下文要求只回答正文支持内容，不足时仅输出 NO_EVIDENCE；精确匹配该信号（忽略首尾空白）、空回答或无合法引用均保持现有 NO_EVIDENCE/answer=null/空引用。响应结构不变，generate_answer 保留 tuple 接口，问答路径使用同次生成结果中的正文快照。现有正则引用白名单是结构检查，不解析每个事实、引号/代码的语义，也不自动识别“相关但没答案”；Fake 负例是 scripted 拒答合同测试，不冒充语义模型。即使模型引用合法 ID，仍可能误答；未做额外计费判定调用。服务超时/失败维持原503/504与错误码，不归为知识不足；QueryLog.hit 仍为检索是否有证据，不再用来判断教学反馈的最终结果。

评测recall_at_k仍统计最终证据文档覆盖，不冒充候选覆盖；元数据区分检索合同、重排开关/模型/端点哈希，并增加 generation_contract=r6-context-citations-refusal-v1，拒绝续跑旧生成合同 checkpoint。合法引用指标不等于人工支持评价；R7 仅有 AI 预标的单课有限真实对照，完整混合问答、人工事实复核与拒答校准仍未验收。

<a id="chunk-source"></a>

## 切分与来源

逐页/幻灯片调用现成切分器，800字符容量、120最大重叠；MarkdownSplitter处理Markdown，其余TextSplitter处理抽取文本。实际重叠由结构决定；可容纳块优先保留，小章节可合并，超长代码/表格/段落仍会拆分，不保证围栏闭合或完整标题树。

当前解析是纯文字基线：PDF 通过 PyMuPDF `page.get_text("text")`，PPTX 读取文本框和表格，DOCX 通过 `iter_inner_content` 保持顶层段落/表格顺序，Markdown/TXT 按 UTF-8 读取。DOCX 不还原物理分页、合并/嵌套表、图片/公式或布局；PDF/PPTX 不做 OCR、版面恢复、图片/图表理解或可靠公式恢复，空单位可跳过但真实编号不重排。当前 `LOW_EXTRACTED_TEXT` 只比较整份资料字符总量，不能识别局部空页、图片页或公式乱码。R7B 预检已增加页级风险画像，但这些分类仍只描述 PyMuPDF 现状，不是解析质量评分。即使生成模型本身支持图片，现有 `DeepSeekLLM.generate` 仍只发送字符串，没有视觉内容块。

R7B **已定** Docling 为主解析器；R7B-1 代表页验证已通过。**接入（R7B-2）后**更新本节现行解析描述；当前生产路径仍是上文纯文字抽取。步骤见 plan，门槛见 validation；代表页报告见 `corpus/local/r7b-1-docling-2026-10-16/COMPARISON.md`（忽略区）。

### R7B 课程资料来源合同

中期基线只认 `corpus/local/r7b-four-course-source-inventory-2026-10-16.json` 的 17 份 PDF；`corpus/local/SOURCES.md` 是人工可读索引。不得通过扫描 `corpus/local` 自动把历史实验、重复上传、旧 Calculus 或其他课程资料加入当前基线。资料文件名可以作为本地 provenance，但课程标题、讲次和官方来源以 inventory 的 metadata 为准。

当前固定资料均来自 MIT OpenCourseWare，并记录课程代码、课程标题、学期、教师、官方课程页、官方资源页/PDF URL、SHA-256 和项目使用状态。哲学明确是有限覆盖，仅第 1–4 讲；线性代数第 4、5 个文件已按官方实际讲次直接修正本地文件名，内容字节未改。页级预检只用于发现解析风险，不能把 `pages_with_text` 当作内容正确率，也不能把 OCR/公式/图片派生结果伪装成原生资料。

### 解析证据中间层（接入后更新）

**已定方向（尚未成为现行代码合同）：** Docling 输出经薄适配进入 Document → Page → Element（Text/Formula/Table/Image/Chart），保留 page、bbox（可得时）、extraction_method、parser/model、status、asset_ref；结构化产物为事实源，Markdown/Chunk 为派生视图；PARTIAL/FAILED ≠ ingest succeeded。细节与验收子项见 [plan R7B-2/R7B-3](implementation-plan.md#docling-稳妥型开工计划)。接入并验收通过前，仍以本节下方现行 PyMuPDF/切分字段表为准。

| 字段 | 当前含义 |
| --- | --- |
| Document.chunking_version | 成功入库后sts-0.33.0-char800-overlap120-r5-v1；资料列表/详情提供同名可空字段 |
| Chunk.source_metadata | 可空JSON，含kind/unit_index/char_start/char_end/chunk_index/splitter，无路径/账号或正文副本 |
| kind/unit_index | pdf_page或pptx_slide使用实际1-based页/幻灯片；markdown/plain_text/docx_text为抽取单位（当前1），不表示物理页 |
| char_start/char_end | 清洗后当前单位内0-based半开Python Unicode字符范围，必须unit[start:end]==chunk.text；不是文件字节/屏幕坐标 |
| chunk_index/splitter | 文档内0-based连续序号；markdown或text；重复正文直接使用上游偏移，不用find猜位置 |
| Chunk.page | 新PDF/PPTX保留真实号；新DOCX/Markdown/纯文本为null；旧行不回写 |

切片前移除Postgres不接受的NUL；抽取计数、嵌入输入、落库正文与范围针对同一清洗文本。0010只增加可空版本/JSON列，无回填、不触发重嵌入。旧行null不能冒充新算法；迁移和原子重入库要求见 [workflow](workflow.md)。

<a id="ingest-recovery"></a>

## 入库恢复

任务pending→running→succeeded/failed；通过条件更新认领、分配唯一run_token。心跳/最终成功/失败必须匹配当前token，旧worker失去租约后不能覆盖状态或提交片段。EMBEDDING_BATCH_SIZE默认32、允许1–256；每批校验数量与1024维并刷新心跳，全部成功后才在同一事务替换片段/向量/来源/版本/质量计数并成功落库。失败回滚，保留旧完整索引。

课内教师POST /courses/{course_id}/documents/{document_id}/retry，接受返回202；failed可立即重试，pending/running默认900秒后可恢复，活跃或succeeded返回409，学生403、跨课/不存在404。恢复撤销旧token；当前为进程内后台任务，不是持久队列，不自动恢复所有崩溃任务。抽取为空失败，偏短可成功并给质量提示，计数不等于抽取质量/事实评分。

<a id="storage-lifecycle"></a>

## 上传文件

存储路径固定为 upload_dir/course_uuid/document_uuid/safe_filename，根/课程/资料/文件先resolve；文件名须等于basename，拒绝穿越、串课、越界或非文件读取。单资料删除限本课本资料目录，课程删除限该课程树，其他课程不受影响。

GET /courses/{course_id}/documents/{document_id}/content先做Session/成员鉴权，再验证存储范围与文件存在；不公开挂载上传目录。PDF/Markdown/纯文本inline，PPTX/DOCX attachment；MIME白名单与nosniff，不承诺Office页内预览。PDF可使用可信页码附加#page=。

上传先落盘后提交数据库，失败回滚并补偿刚写入文件；删除先提交数据库后清理文件。清理失败保留删除成功语义，记录storage_cleanup_failed的scope/对象ID/error_type，不记录正文或完整路径；当前需人工补偿，不在请求内无限重试。

<a id="midterm-product-contract"></a>

## 中期产品化与运行合同

中期目标是本机小规模演示，不是生产服务。已有业务与 RAG 架构足够，产品化只做收口，不新增基础设施。

### 课程与成员

- 管理员创建课程与账号；管理员可维护课程成员；教师只能维护自己有权限的课程并加入已有学生；学生只访问当前已加入课程。
- 中期不做学生自主选课、邀请码、公开课程目录、申请审批和成绩/能力画像。
- 成员撤权必须影响下一次课程、资料、问答和原文件请求；删除课程/资料后不得继续检索或读取旧内容。

### 数据库与文件

- PostgreSQL + pgvector 继续作为唯一业务/向量数据库；不为中期引入 Redis、Elasticsearch、MongoDB、对象存储或独立分析平台。
- 解析事实源/图片等大制品放受控本机文件；数据库保存必要 metadata、来源、Chunk、向量和状态，不把完整解析 JSON 与所有二进制塞进业务表。
- Alembic 迁移、课程/资料删除、失败任务恢复和数据库 dump 恢复分别验证；恢复不得依赖删除卷重建。
- 解析、切分、embedding、索引身份变化必须能被识别；新解析失败不得覆盖旧完整索引。

### 中期资源上限

| 类别 | 合同 |
| --- | --- |
| 文件/问题 | 沿用当前单文件大小、PDF 页数、问题长度等 API 限制；用户可理解的主要限制由 UI 提示 |
| 解析 | Docling 低并发、固定版本、最小必要 extras/模型；按代表页/文件范围测试，避免无谓全量重跑 |
| Embedding | 固定模型与 batch；资料冻结后不因 UI/prompt 小改反复全量向量化 |
| Retrieval | 固定候选上限与最终 Top-K；课程过滤先于召回 |
| Rerank | 默认关闭；只有 baseline 证明“候选已召回但排序不足”才开启 |
| LLM/Vision | 真实调用必须有当次范围、次数/预算、超时、重试和停止条件；Vision 默认关闭，只用于少量固定视觉题 |
| 日志 | QueryLog 只按既定留存窗口保存；不把完整原始模型输出或密钥写日志 |

供应商价格、RPM/TPM、模型别名和服务能力会变化。项目记录本次实验实际模型、版本、usage/账单依据与总费用，不把网页上的历史单价当永久合同；没有可靠 usage 就不估算成精确费用。SiliconFlow 当前文档明确区分 RPM/TPM/TPD 等限流指标，具体模型限制以模型广场为准。

### 运行与 Demo

- 保持现有本机启动方式；至少有数据库、migration、backend、frontend、health/ready、登录六步检查。
- health/ready/runtime 只说明进程、数据库和本地配置状态；configured 不等于供应商连通或模型可用。
- Demo 使用固定课程、账号、资料和题目，不在现场临时解析、入库或换模型。
- 准备最小恢复/重置路径，只作用于明确的 Demo 数据；真实资料、旧结果和数据库恢复副本不得被“重置”顺手删除。

### AI 编程环境

- 权威工作区仍是本机 D:\workspace\univ-course-rag；Git 状态和最终验收以本机工作区为准。
- 一个工作区同一时刻只允许一个写入型 coding agent 负责代码修改；其他 Agent 只做只读检查、研究或 review，避免两个 agent 同时改同一工作树。
- 如果使用远程云电脑，只同步代码和合成/公开测试资料；17 份受控课程资料、数据库恢复包、.env 和其他本机数据默认不上传。远程结果必须回到本机 Git 工作区核对后才算项目事实。
- Windows 原生与 WSL2 均可作为本机执行环境；优先保持与最终演示一致的环境。若为 Docling/本地工具选择 WSL2，只把它当执行层，不改变项目权威路径和数据合同。

<a id="query-log-retention"></a>

## 日志留存

QueryLog含问题原文，仅用于课内描述性反馈；统计只读当前留存窗口，即使尚未物理清理也排除到期记录。QUERY_LOG_RETENTION_DAYS默认90（1–3650），QUERY_LOG_CLEANUP_BATCH_SIZE默认100（1–1000）。

### 问答事件与统计口径（P4）

0011增加可空 QueryLog.outcome/member_role_at_ask，无默认值/回填；旧 hit/error_code 不能证明曾有合法引用或历史课内角色。新问答在处理函数入口快照UTC时间和课内角色，以入口时间写 created_at，按最终结果写 outcome：

| outcome | 含义 |
| --- | --- |
| cited_answer | 返回有合法上下文引用的回答，不等于事实正确或完全支持 |
| no_evidence | 无证据、明确拒答或无合法引用；即使hit=true也可能发生 |
| failure | 已捕获的检索/上游错误、超时或索引不兼容；不进入依据不足列表 |
| null/未知值 | 历史或未知结果，不从旧字段推断为成功 |

每个进入处理函数并成功提交日志的HTTP提问记一次，显式重试/相同问句各记一次，不去重、不表示人数；SDK内部重试不另记事件。401/403/422、依赖构造阶段的配置失败、未捕获异常/进程中断与数据库无法提交可能没有事件，因此记录数不是所有请求数或完整可用率分母。鉴权仍逐请求执行，失败不伪造事件，暂不新增通用事件中间件。统计不能证明客户端已收到回答。

GET /courses/{course_id}/insights 保留 retention_days/frequent/no_evidence，并返回 window_start/window_end/summary/trend；可选 start_at/end_at 必须含时区，转UTC，实际范围为请求与[当前时间-留存天数,当前时间)交集。默认完整留存窗，左闭右开；无交集/倒置/无时区返回422。不会读到期或未来记录。页面可提交开始（含）与结束（不含），并显示服务端裁剪后的窗口；筛选和刷新只调用本 GET。

按 member_role_at_ask=student 统计，无当前成员表或用户身份join，改角色/移出课程不重写历史；teacher单列排除，其余角色/null为未知角色，不进入学生结果或问句列表。只查询本课，访问者仍须当前课内教师。单条SQL直接复用case/count/max/group_by，同时得总量与列表，避免两次查询观察到不同提交；不读取非学生/未知事件的问句，也不返回用户标识。

summary中 recorded_attempts = student_attempts + non_student_attempts + unknown_role_attempts；student_attempts = cited_answer + no_evidence + failure + unknown_outcome。knowledge_attempts = cited_answer + no_evidence；no_evidence_rate仅为 no_evidence/knowledge_attempts，分母0返回null，失败/未知不进入分母，不能称正确率或教学缺口率。frequent仅列有引用回答，no_evidence仅列依据不足，空规范化问句只计总量不入列表；失败不混入二者。旧记录可全部为未知，绝不使用当前角色补造新基线。新增列后目标库须先迁移0011；R7 新隔离库已实际应用，原长期目标库未核验。

仅admin可POST /admin/query-logs/retention，先dry_run查看一批，再显式delete；按created_at,id处理最旧一批，has_more表示仍可继续。维护日志只写模式/数量/是否更多，不写提问/用户/Cookie/Session。当前库删除不能立即抹除外部备份；聚合、未来向量与缓存也须继承权限和留存。

### 候选同义问题组（P5）

POST /courses/{course_id}/insights/groups仅当前课内教师可用，与普通统计GET分离。QUESTION_GROUPING_BACKEND默认disabled，POST返回QUESTION_GROUPING_DISABLED/503；显式embedding仅复用已配置SiliconFlow嵌入，fake/未知后端不得冒充语义。请求必填min_similarity（0<值<=1，有限），可选含时区start_at/end_at与P4共用留存裁剪/左闭右开合同，并须confirm_external_processing=true确认本次外发问句。未确认/无效窗口为422；普通统计无嵌入调用。真实调用仍需当次数据/费用授权，本轮未调用。

单SQL只筛本课/本窗口/member_role_at_ask=student，只有cited_answer/no_evidence的非空问句可入组；学生失败/未知/空问句计excluded_attempts，其余角色与课外/窗外不在该样本域。折叠空白但不做200字符截断、词项强合并或问题改写，重复问句合并计数，保留两种最终结果和最近时间。按全文排序保证输入稳定，不连接身份表、不返回用户ID，不写回原日志、向量、缓存或持久组表；无历史回填或新迁移。

最多200个不同规范化问句、每句2000字符、总计200000字符；SQL原始聚合读取最多405行，触顶或其他超限整次QUESTION_GROUPING_LIMIT/413，缩窗重试，不静默抽样或返回部分组。0/1种问句不嵌入；大于1种一次调用现有embed适配（SDK超时/重试沿用现行配置），请求依赖finally关闭新增客户端，重复POST可能重复计费。服务错误/超时保持503/504，无词项回退。

向量数量/矩形维度/有限实数/非零校验，维度最多4096，归一化避免巨大幅值溢出；无效输出QUESTION_GROUPING_FAILED/503。直接调用SciPy余弦距离与complete-linkage/fcluster，按请求阈值裁剪；complete约束组内最差成对相似度，不使用单链接传递链合并。高嵌入相似度依然可能混淆同主题不同任务，真实误合并/误拆分尚未验收，不把它当回答依据、掌握度或确定知识点。

响应包含grouping_contract=p5-complete-cosine-v1、模型/索引身份、实际窗口、阈值、threshold_calibrated=false和embedding_called。eligible_attempts为入组事件数，distinct_questions为不同全文问句数，grouped_questions/singleton_questions及singleton_attempts明确未成组数量；所有组count之和等于eligible_attempts。kind=candidate表示至少两种表达，singleton保留单例（即使该问句重复多次）；成员提供计数、cited_answer/no_evidence、与代表的余弦相似度及最近时间，组提供min_pair_similarity（单例null）。代表从真实成员选组内无频次权重的距离和最小者，同分按全文排序，不由LLM生成名称。相似度不是同义概率；阈值没有已验证默认值，真实开发集题对校准与人工复核后才能评价效果。分组算法与 POST 合同由 P5 保持；页面接入见下文，统计请求不会自动调用该接口。

<a id="p6-dashboard"></a>

### 教师反馈看板（P6）

trend 与 summary、问句列表来自同一条 SQL：按课内角色、最终结果、可列出的问句和 UTC 日分组。PostgreSQL 使用 `date_trunc('day', timezone('UTC', created_at))`；当前测试库是 SQLite，按已存 UTC 文本取日期。序列覆盖实际窗口中的每个 UTC 日，无事件记 0，不抽样、不丢事件。只累计 `member_role_at_ask=student` 的 cited_answer、no_evidence、failure、unknown_outcome，四项之和等于 student_attempts。教师和未知角色不进入趋势或问句列表。旧结果与旧角色保持未知，不回填，也不按当前成员改写。

页面时间控件只填本地范围。点击「按此时间统计」后发送带时区的 start_at/end_at；「使用留存窗口」和首次打开不带这两个参数。返回的窗口、分母和列表仍遵守 P4。候选组 POST 复用最近一次已应用的同一对时间。刷新或更换统计窗口会清掉上一次分组和外发勾选，避免沿用另一个窗口的确认。

分组按钮在阈值合法（有限、大于 0 且不超过 1）且勾选外发确认前保持禁用。QUESTION_GROUPING_DISABLED、QUESTION_GROUPING_FAILED、QUESTION_GROUPING_LIMIT 使用前端固定文案，不回显服务端 message。LIMIT 的 HTTP 413 文案要求缩小时间范围，与资料上传的 15 MB 413 分开。结果写明 threshold_calibrated 为 false、本次是否调用嵌入、可分组/排除次数，以及候选问句数和单例问句/次数。candidate 与 singleton 分表；代表问句和成员相似度沿用 P5 字段，不改写成知识点名称、教学缺口或掌握度。

没有新迁移、分组缓存或自动外发。真实 Postgres 的按日表达式、真实阈值和语义效果尚未在目标库验收。

## 异常与恢复

当前真实向量为BAAI/bge-m3/1024，生成模板deepseek-flash，显式关闭thinking；现行调用是纯文字 Chat Completions，不因同名模型具备视觉能力而自动处理图片。这些配置不代表供应商已连通或效果已验收。未知/缺key/空模型/非法URL等真实配置不静默转Fake。/health仅进程，/ready仅SELECT 1，/runtime仅安全本地状态；含reranking disabled/configured/unavailable，connectivity/migration/index仍not_checked，不发计费探测。

| 场景 | 当前处理 |
| --- | --- |
| 配置/上游/数据库不可用 | MODEL_NOT_CONFIGURED、UPSTREAM_UNAVAILABLE、DATABASE_UNAVAILABLE为503；UPSTREAM_TIMEOUT为504 |
| 关键词/融合/策略失败 | KEYWORD_LIMIT、RETRIEVAL_FAILED、RETRIEVAL_STRATEGY为503，不改跑其他策略 |
| 重排失败/超时 | RERANK_FAILED 503 / RERANK_TIMEOUT 504；不返回部分排序或调用生成，问答记系统失败 |
| 不兼容索引 | EMBEDDING_MISMATCH，要求受控重新入库，不混空间 |
| 无证据或无合法引用 | NO_EVIDENCE，不记作上游故障 |
| 未知入库异常 | INGEST_FAILED，保留安全解析原因；不回显原始错误或凭据 |

前端按安全白名单/HTTP类别显示文案；未列入白名单的新错误可能仍显示通用503提示。问题草稿仅模块内存、按账号/课程隔离；同账号重新登录可恢复，换账号/退出/整页刷新关闭丢弃，不落localStorage。某资料404不撤整课能力，课程自身拒绝才清理课程视图。

上传结果不确定时先刷新列表核对，再显式重传；同名阻止该重传入口，已接收入库但列表失败不冒充上传失败。按method/path与表单状态阻止在途重复写，不提供跨页面/重试的服务端幂等保证。通用等待90秒、问答300秒；等待取消不保证后端/计费停止，轮询不重叠，迟到响应不重启已离开的视图。

## 当前待验证边界

R7 新隔离库已核验0011/pgvector和真实供应商可用性，单课程纯文字效果见 [结果登记](evaluation-results.md)。原长期目标库迁移、性能/并发、实际账单、人工事实复核和拒答/阈值校准、关键词独有证据的充分性、Docling 代表页验证、复杂资料解析、页级质量、视觉输入及内部联合验收仍待验证。教师看板只展示已保存计数和当次候选分组，不证明同义质量或教学效果。Fake/组件导入/本地configured状态只证明相应合同，不能代替这些结果。

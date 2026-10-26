# PLAN-07 检索与证据质量回归

更新：2026-10-22（Asia/Shanghai）。本卡交付为**既有证据分析 + Fake 合同回归**。默认 Dense、rerank 关闭；本次新增产品 Embedding/LLM 调用 **0 次、¥0**。未重跑 22 题，也未复跑 PROB-F02。**PROB-F02 尚未修复、根因未完全定位；独立人工核验未完成。**

## 1. 冻结输入与复用边界

依据：[中期对照报告](../中期答辩材料/研究证据/results/retrieval-compare-2026-10-20.md)、[评测登记](evaluation-results.md)、[metrics-v1](metrics-data-boundary.md) §3.1。2026-10-22 对下列文件只读计算 SHA-256，均与中期报告一致；未改写原 JSON、题集或预期答案。

| 输入 | 冻结值 |
| --- | --- |
| 语料 | `univ_course_rag_cn_v2`，4 课 / 27 PDF / 2,501 chunks；本次没有查询正式库或重新解析 |
| 题集 | [02-人工核验题集-v1.json](../中期答辩材料/研究证据/02-人工核验题集-v1.json)，22 题：17 应答 / 5 明显课外拒答；保留其预期要点、来源及页标注 |
| 真实运行版本 | 两份 JSON 的 `meta.git_sha=5292d54`，日期 2026-10-20；中期归档锚点 `midterm-freeze-2026-10-21` → `f8278d7` |
| 检索与模型 | Dense / Hybrid 历史对照；rerank=`disabled`；`siliconflow\|BAAI/bge-m3`；`deepseek\|deepseek-flash`；cosine 门 0.45 |
| 核验者 | 历史 `verifier=developer`；本次复算字段计数，不新增人工评分 |
| 当前代码证据预算 | `SEARCH_TOP_K=8`，上下文 6,000 字符、每来源 1,200 字符；旧 JSON 未完整记录预算，不把当前常量冒充历史逐题配置证明 |

| 文件 | SHA-256（原报告指纹；本次复核相同） |
| --- | --- |
| [Dense JSON](../中期答辩材料/研究证据/results/manual-verify-2026-10-20-dense.json) | `C8FA1AE6D542FDD2939C07CFFEB5A60BA130F167BE7AF45E3CE7F017BDB8FBDF` |
| [Hybrid JSON](../中期答辩材料/研究证据/results/manual-verify-2026-10-20-hybrid.json) | `391464B4810AD26ACE9E1B677E1D184891797DDA86CFB7381E6C13014374EA7B` |
| 22 题题集（两侧 `meta.case_set_sha256`） | `33437a164e41f1f35ac39399994a2c6bfde927f28daa261890127cd8dede12a0` |

复用现有 runner 的 `serialize_retrieval_hits`、`classify_generation`、`candidate_stats`，以及现有 `retrieve_hybrid_candidates` / `_select_conservative_evidence`、FakeEmbedder 与测试造数 helper。新增独立计数纯函数 `summarize_citation_metrics`，供 runner 新结果的 `answered_citation_metrics` 使用；旧 totals 和历史文件不变。没有引入新依赖、检索管线或评分模型。

## 2. PROB-F02 分层假说表

以下事实来自[只读诊断笔记](../中期答辩材料/研究证据/results/prob-f02-readonly-notes-2026-10-20.md)及两份旧 JSON；本次未重新查询 PDF/数据库，也不重复原题答案。

| 层 | 已有证据 | 尚待验证的假说 / 不能推出的结论 | 所缺诊断 |
| --- | --- | --- | --- |
| 覆盖 coverage | 笔记确认目标 PDF 有 48 chunks；完整目录文本在 `page=3`、`unit_index_start=2` / `unit_index_end=3` 合并块及后续重复块内；阅读器 #2 是预期目录页 | 目标内容并非全库缺失；但覆盖存在不保证目录块被召回，也不能据合并末页认定目录被丢弃 | 当前索引内容的逐块版本及页 span 对照；本次沿用笔记 |
| 候选召回 candidate recall/rank | 两侧 `retrieval_hit_documents/pages` 非空；Hybrid 有候选统计 | 目录块可能未入候选或排名不足；聚合页集合含 2，不能证明目标文档的目录页被命中 | 每个候选的 chunk_id、文档、页、分数/排名配对；旧结果没有 |
| 证据过滤 evidence filter | 旧聚合字段对应最终 evidence，说明最终证据非空；keyword-only 未准入，门为 0.45 | 目录块可能被门或 Top-k 排除；不能断定阈值过严，也不能据此降门 | 同次候选 → 最终 evidence 的逐条配对及排除原因；旧结果没有 |
| 上下文 context | 当前装配器会限制总预算及每来源长度；空/缺失 chunk 不入 Source | 即使目录块入 evidence，也可能被排序、预算或截断影响；历史没有 prompt/Source 配对，不能认定发生过截断 | 已装配 source_ids、来源片段/截断状态；仅有 retrieval_hits 仍不足以完全定位 |
| 生成 generate | 两侧 `status=no_evidence`、空回答、无引用、`error=null`；系统失败 0 | 可能是字面 NO_EVIDENCE、空输出或无合法引用，旧记录无法区分；不能断定模型拒答或 prompt 为单一根因 | 当前 runner 的 `generation_status`；本次只用 Fake 覆盖，未取得该题新真实结果 |
| 引用展示 cite UI | 两侧没有可展示引用；笔记确认 `Chunk.page` 常取合并末页 | 该题无法完成点引用闭环；不能用 HR 的末页现象解释这次无回答。页 span 不等于答案所在的唯一页 | 后续获授权后记录真实引用及 Vite 点回 PDF；本次未测 UI |

因此只保留“应答题误拒答 / 原因未完全定位”的结论。当前 runner 可留逐条 `retrieval_hits` 与生成细分状态；新增 Fake 覆盖保证这些字段在拒答、空输出、非法引用和上游失败时仍能辨别，不构成真实修复证据。

## 3. Hybrid keyword-only 准入事实

中期对照文档和旧 Hybrid JSON 复算一致，22 题累计（各题候选数求和，**不是全库去重 chunk 数**）：

| 候选来源 / 准入 | 计数 |
| --- | ---: |
| dense_only | 431 |
| keyword_only | 431 |
| both | 273 |
| keyword_only 进入最终 evidence | 0 / 431（22 题中有准入的题数 0/22） |

融合仅给候选排序；BM25/RRF 不可冒充 cosine。当前 keyword-only 的 `cosine_score=None`，保守选择器要求分数存在且 `>=0.45`，故排除；有 cosine 但低于门的候选同样排除。这是现行行为及已观测事实，不能简化成“所有关键词命中都测得 cosine<0.45”，也不视为必须降门的 bug。

Fake 场景用实际 Fake 检索/融合构造：已知向量点积为 0.44 的块落在 Dense 候选预算外，被 keyword 分支召回、保留为 keyword-only（融合分数中 cosine 仍缺失），最终被门排除；both=0.8 和 dense_only=0.9 可准入且保留 cosine 分数。这只验证分层合同。

历史可见变化主要涉及排序/Top-k 组成。HR-T01 的两侧事实字段不同只是一道题的开发者核验差异；**不宣称 Hybrid 整体显著优于 Dense**，默认仍 Dense、rerank 关。

## 4. 分层指标与分母

以下 n/N 沿用中期对照表，并只读复算已回答应答题的标签；没有新增评分。

| 层 / 指标 | Dense | Hybrid | 分母或限制 |
| --- | ---: | ---: | --- |
| 候选召回 / 排名质量 | 未留足配对，不能重算 | 同左 | 候选计数不等于 recall@k / MRR；不补造 n/N |
| 最终证据支持答案 | 无单独评分，不能重算 | 同左 | evidence 非空不等于可答；PROB-F02 两侧有非空聚合命中仍未回答 |
| 全部应答题事实要点 | 15/17 | 16/17 | 含 PROB-F02 应答未答 |
| 已回答应答题事实要点 | 15/16 | 16/16 | 仅机器 answered 的应答题 |
| 已回答应答题 citation_supports | 16/16 | 16/16 | 人工支持性标签，不从“有合法引用”自动推断 |
| 已回答应答题 page_ok | 12/16 | 12/16 | 严格比题集预期 PDF 阅读器页序 |
| 明显课外正确拒答 | 5/5 | 5/5 | 未覆盖课内相关但资料不足的困难拒答 |
| 应答题误拒答 | 1/17 | 1/17 | PROB-F02；两侧 no_evidence=6/22 = 5 正确拒答 + 1 误拒答 |
| 系统失败 | 0/22 | 0/22 | 错误/异常，与无依据分开 |
| 机器已回答（非准确率） | 16/22 | 16/22 | 回答状态不代表事实或引用质量 |

旧 JSON totals 里引用支持及页命中使用全部 17 应答题分母，分别为 16/17、12/17；上表按对照报告明确限定“已回答应答题”，故为 16/16、12/16。两种分母不能混用，也不回写历史 totals。

新 `summarize_citation_metrics` 仅统计 `should_refuse=false` 且 `status=answered`；对 `citation_supports`、`page_ok` 分别返回 `n`、`N`、`reviewed`。pending/unclear/缺字段不算通过，只有 pass/fail 计入 reviewed；`reviewed<N` 时指标未核验完整，不能当作已完成通过率。Fake 验证“支持但页不符”“页符但不支持”以及待核验、拒答、故障的边界。

### 页合并的评分限制

[HR 页码笔记](../中期答辩材料/研究证据/results/hr-page-mapping-notes-2026-10-20.md)已确认：一个概论 chunk 的 `page=9`、span=1–9，含阅读器 #5 的相关内容；严格期望页 5 与引用页 9 不同，不自动推翻内容支持。HR-F01/F02/T01/X01 是两侧严格页失败样本；Dense 的 HR-T01 另有事实要点失败，不能把所有失败都归为页合并。

`citation_supports` 衡量回答是否受引文支持；`page_ok` 衡量是否严格命中预标页。**12/16 不能称为引用错误率。** 阅读器页序、印刷页码、合并块末页不保证处处一致。保留原页码及引用 UX；本次没有改检索/引用 span metadata，也没有用 span 覆盖替代严格评分。后续暴露 span 可帮助诊断，但不能自动证明该块每一页都支持答案。

### 延迟、调用与成本

历史 Dense embedding 22 次 / LLM 22 次；Hybrid embedding 44 次 / LLM 22 次（含候选诊断重复检索）。因此历史 latency / embedding 次数不能直接作策略效率对照。当前 runner 已同次候选复用并分开 `retrieval_ms` / `diagnosis_ms`，已有 Fake 回归守护；没有回改历史耗时。

历史 `cny_cost=null`，未核供应商账单，禁止估算；本次没有产品云调用，新增花费 ¥0，PLAN-07..10 约 ¥2 总预算按此前约 ¥0 保留给后续卡。

## 5. 回归范围与未完成项

- Fake：逐条 hit 配对、截断/换行/缺文档名；五类生成状态；真实装配器与引用过滤的 runner 路径；保守门和候选统计；引用支持/严格页命中独立计数。见 [新增测试](../backend/tests/test_plan07_retrieval_evidence.py)及[现有 runner 测试](../backend/tests/test_manual_verify_runner.py)。
- 本卡只改 runner 报告 helper 与 Fake 测试；应用入口另修已有导入排序以通过指定 ruff 检查。检索、生成、引用 API、UI 均无行为改动；没有新增依赖或完整管线。
- **未完成：独立人工核验**（本会话无独立核验者）；历史 developer 不能替代。
- **未完成：新真实同题回归 / 退化检查**（本次按用户决定不复跑 PROB-F02 或 22 题）；Fake 通过不能说明真实质量提升。
- **未完成：PROB-F02 修复及完整根因定位**；缺同次逐条 retrieval_hits、上下文装配与生成状态的真实配对证据。
- **未完成：新引用点击回 PDF 页验证**；未改 UI，因此 build / 点击检查本卡不适用。历史页映射限制仍在。
- 跨页样本仅 5 题且部分要点在同页/相邻合并块内，不能称真正跨页专项验证已完成。

本地命令、原始输出摘要及环境处理见 [PLAN-07 完成记录](tasks/PLAN-07-retrieval-evidence.md)。任务卡 done 表示本次用户限定交付完成；上述真实质量和独立核验缺口仍须后续补证，不能据此宣告结题整体通过。

## 6. 2026-10-26 有限 Evidence 收口（本批）

更新：2026-10-26（Asia/Shanghai）。本批**不修复 PROB-F02**；**不跑 22 题真实全量复跑**；**不宣称 Hybrid 显著优于 Dense**。

### 6.1 Fake 复跑

仓库根：

```text
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan07_retrieval_evidence.py backend/tests/test_manual_verify_runner.py backend/tests/test_retrieve.py backend/tests/test_fusion.py -q -p no:cacheprovider --basetemp=output/plan07-reverify-2026-10-26
```

结果：**79 passed, 2 skipped, 1 warning in 13.46s**（exit 0）。两 skip 为既有可选 PostgreSQL / 真实 embedding。夹具已与 M4 默认 `retrieval_enabled=false` 对齐（`enable_retrieval` / retrieve 上传 helper），产品检索合同未削弱。

### 6.2 链到同日 developer 真模型短问（≠ 独立评测）

指针：

- [observation-2026-10-26-developer-m3-m4.md](user-task-scripts/observation-2026-10-26-developer-m3-m4.md)
- [`evidence-2026-10-26/`](user-task-scripts/evidence-2026-10-26/)（含 `real-ask-response.json`）

口径（必须保留）：

| 项 | 事实 |
| --- | --- |
| 核验者 | **developer** 代观察；**不是**独立人工核验 / 独立评测 |
| 路径 | 学生短问；LLM=`deepseek-flash`；Embedding=硅基流动 `BAAI/bge-m3` |
| 结果 | 链路 PASS：有答 + 引用；前端可拼 `#page=` |
| 花费 | API `usage=null`，精确 CNY 未知；单次短问粗估远低于 ¥2；本批未再烧大额真实模型 |
| 质量 | **不宣称**事实正确率 / 引用支持率达标；不得据此勾选结题 Evidence 通过 |
| PROB-F02 | **仍未修复**；22 题全量真实复跑本批未做 |

### 6.3 仍未勾选的缺口

- 真实 22 题同题复跑与退化检查
- 独立人工核验
- PROB-F02 根因闭环与修复
- 新引用点击回 PDF 页的独立核验记录（本批未新增）

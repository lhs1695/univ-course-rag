# Dense vs Hybrid：代码评估与小样本对照设计

更新：2026-10-20（Asia/Shanghai）  
**阶段 A（2026-10-20）已实跑**：同一 22 题集 Dense + Hybrid（rerank=disabled），结果见 `results/manual-verify-2026-10-20-*.json` 与 `results/retrieval-compare-2026-10-20.md`。以下保留代码事实；对照数字以 results 为准。

## 1. 实现要点（代码事实）

| 项 | 位置 | 事实 |
| --- | --- | --- |
| 策略集合 | `backend/app/services/retrieve.py` `RETRIEVAL_STRATEGIES` | `dense` / `hybrid` |
| Dense | `_retrieve_dense` | 课内 + embedding 身份过滤；默认 `min_score`：SiliconFlow **0.45**，Fake **0.15** |
| Hybrid 候选 | `retrieve_hybrid_candidates` | Dense top `candidate_k`(默认 32) ∪ 关键词 BM25 top 32 → RRF 融合（`fusion.py`，k=60） |
| Hybrid **最终证据** | `_select_conservative_evidence` | **仅保留 `cosine_score is not None` 且 `cosine_score >= min_score` 的候选** |
| 关键词独有行 | 同上 docstring | Lexical-only（无 cosine）**不能**授权生成；注释写明「Temporary dense-score gate」 |
| Rerank | `_rerank_hybrid_candidates` | 可选；**演示默认关闭**；hybrid+rerank 亦先过同一 cosine 门 |

结论一句话：**当前 Hybrid 路径会召回关键词独有候选，但在进入生成前会被 cosine 门槛过滤掉。**  
因此：Hybrid 相对 Dense 的可能收益，主要来自「Dense 也命中、但 RRF/排序改变 Top-k 组成」或「rerank 重排后仍过 cosine 门」；**不是**「BM25 独有证据直接回答」。

## 2. 中期对照结论（阶段 A 已完成）

| 判断 | 说明 |
| --- | --- |
| **已完成** | 2026-10-20 对同一 22 题集分别运行 Dense 与 Hybrid（rerank 关闭），并由开发者核验；结果见 `results/retrieval-compare-2026-10-20.md` |
| **可得结论** | 当前小样本中 Hybrid 在个别题的排序/答案要点上有变化，但严格预期页命中相同；不足以证明 Hybrid 整体显著更优 |
| **仍有限制** | 保守门使 Keyword-only 候选不能进入最终 evidence；阈值未校准；开发者核验不是独立评测，样本不能外推 |
| **答辩话术** | 「Hybrid/RRF 已实现并完成 22 题小样本对照；最终 evidence 仍受 cosine 门限制，因此主演示仍用 Dense。当前证据不支持宣称 Hybrid 整体显著更优。」 |

## 3. 不污染正式库的做法

1. **只读复用** `univ_course_rag_cn_v2` 已有向量与关键词索引；**禁止**为对照全量重入库。
2. 同一题集（建议本包 22 题或先抽 8–12 题）分别跑：
   - `RETRIEVAL_STRATEGY=dense`
   - `RETRIEVAL_STRATEGY=hybrid`（rerank 仍 `disabled`）
3. 记录分层指标（缺一不可）：
   - 候选层：Dense-only / Keyword-only / Both 计数；Keyword-only 是否进入最终 evidence
   - 最终 evidence：文档/页命中（相对 `expected_*`）
   - 生成层（若授权 LLM）：拒答是否正确；**人工** citation_supports（勿只用弱规则）
   - 延迟与失败类型；usage（若 API 返回）
4. 结果写入 `results/`，文件名含策略与日期；失败案例全文保留。

## 4. 阶段 A 执行范围记录

- 已完成范围：同一 22 题集 × Dense/Hybrid；复用 `univ_course_rag_cn_v2` 现有向量与关键词索引；rerank 关闭；保存两份原始 JSON、对照报告和失败笔记。
- 未做：全量重入库、全量 Vision、启用 rerank、人民币费用估算。公开前请复核密钥；课件按公开分享资料收录（见根目录 NOTICE）。
- 费用：API usage 有记录；供应商人民币账单未核，**不估算金额**。如需新增真实模型运行，应另行明确授权与成本边界。


## 5. 实跑摘要（2026-10-20，verifier=developer）

- Keyword-only 进入最终 evidence：**0**（验证 cosine 门）
- 分层指标见 `results/retrieval-compare-2026-10-20.md`；**禁止**合成单一准确率或宣称 Hybrid 整体显著优于 Dense
- Hybrid 对个别题排序有可见影响（例 HR-T01 must_include 由 Dense fail → Hybrid pass），主因仍是 Dense 也命中后的 Top-k 组成，而非 Keyword-only 直接答

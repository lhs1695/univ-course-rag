# Dense vs Hybrid 检索/核验对照（2026-10-20 Asia/Shanghai）

verifier=**developer**（不得称独立评测）。题集：`02-人工核验题集-v1.json`（22 题）。rerank=disabled。库=`univ_course_rag_cn_v2`。

**原始结果未改写**：`manual-verify-2026-10-20-dense.json` / `manual-verify-2026-10-20-hybrid.json` 内容保持 v1 落盘原样；本文件仅修正**指标口径解释**与方法限制说明。

## 原始结果指纹（SHA-256）

| 文件 | SHA-256 |
| --- | --- |
| `manual-verify-2026-10-20-dense.json` | `C8FA1AE6D542FDD2939C07CFFEB5A60BA130F167BE7AF45E3CE7F017BDB8FBDF` |
| `manual-verify-2026-10-20-hybrid.json` | `391464B4810AD26ACE9E1B677E1D184891797DDA86CFB7381E6C13014374EA7B` |
| `02-人工核验题集-v1.json`（meta.case_set_sha256） | `33437a164e41f1f35ac39399994a2c6bfde927f28daa261890127cd8dede12a0` |

## 机器状态（原 totals，未改）

| 策略 | answered | no_evidence | system_error |
| --- | ---: | ---: | ---: |
| Dense | 16 | 6 | 0 |
| Hybrid | 16 | 6 | 0 |

说明：`no_evidence=6` = 5 道应拒答 + 1 道应答题 PROB-F02（模型未作答，见只读笔记）。

## 口径区分（基于现有人工字段；禁止合成单一准确率）

应答题 n=17（`should_refuse=false`）；其中机器 `status=answered` 的为 **16**（Dense/Hybrid 均为 16；PROB-F02 为 `no_evidence`）。拒答题 n=5。

| 指标 | Dense | Hybrid | 分母含义 |
| --- | --- | --- | --- |
| **全部应答题中的事实要点通过率**（即端到端可答题成功率；`fact_ok=pass`） | **15/17** | **16/17** | 全部应答题；含「应答却未答」为失败 |
| **已回答应答题中的事实要点通过率** | **15/16** | **16/16** | 仅 `status=answered` 的应答题 |
| **已回答应答题中的引用支持通过率** | **16/16** | **16/16** | 同上；引用支持 ≠ 页码严格命中 |
| **严格预期页命中**（`page_ok=pass`） | **12/16** | **12/16** | 同上；**暂不得称为「引用错误率」** |
| **明显课外问题的正确拒答** | **5/5** | **5/5** | 仅明显课外问句；**不**代表「课内相关但资料不足」 |

补充：

- `no_hallucination` 在应答题上 Dense/Hybrid 均为 17/17（开发者核验；含 PROB-F02 未编造）。
- 严格预期页命中失败，常见原因包括：**合并 chunk 的 `Chunk.page` 取 span 末页**、题集 `expected_pages` 按 PDF 阅读器页序标注——二者口径不同时会出现「内容在合并块内但页码数字不一致」。详见 `hr-page-mapping-notes-2026-10-20.md`。**不得**把页码未命中直接说成引用错误率。

## 题集能力边界（保留 v1 结果，不重新解释）

1. **cross_span（5 题）**：LA-X01/X02、PROB-X01、HR-X01、EDU-X01。样本量小，且部分题的要点实际落在同页或相邻合并块内。**不足以证明真正的跨页问答能力**；不得把本轮通过率表述为跨页专项验证完成。
2. **拒答（5 题）**：均为明显课外（SQL / PyTorch / PostgreSQL 复制 / 个股建议 / Kubernetes YAML）。**5/5 只代表明显课外问题的正确拒答**，**未覆盖**「课内相关但资料不足」的困难拒答场景。

## Hybrid 候选层（cosine 门前；来自原 JSON）

- 22 题合计：dense_only=431，keyword_only=431，both=273
- **Keyword-only 进入最终 evidence：0**（any=False）
- min_score_gate=0.45

一句话：当前实现下 Hybrid 会召回 Keyword-only 候选，但保守 cosine 门使其**无法**进入最终 evidence；本轮相对 Dense 的可见变化主要是排序/Top-k 组成（例：HR-T01 Hybrid 答对 must_include，Dense 偏到概论功能映射）。**不得**据此宣称 Hybrid 整体显著优于 Dense。

## 耗时与 Usage 说明（不得直接对比）

本轮 Hybrid runner **为候选统计额外执行了一次** `retrieve_hybrid_candidates`，再调用 `retrieve_chunks(hybrid)`（内部会再取候选）。因此：

- Hybrid `embedding_calls≈44` 含**诊断重复检索**开销，**不宜**与 Dense 的 latency / embedding_calls 直接对比。
- 后续 runner 已改为「同一次候选既出 stats 又出 evidence」，并把 `retrieval_ms` / `diagnosis_ms` 分开；**历史 JSON 的 latency_ms 仍按旧口径，勿回写**。

### Dense usage（原样）

```json
{
  "embedding_calls": 22,
  "embedding_texts": 22,
  "embedding_prompt_tokens": 529,
  "embedding_total_tokens": 529,
  "embedding_usage_returned_by_api": true,
  "llm_calls": 22,
  "llm_prompt_tokens": 57849,
  "llm_completion_tokens": 1504,
  "llm_total_tokens": 59353,
  "llm_usage_returned_by_api": true,
  "cny_cost": null,
  "cny_cost_note": "未查账单；禁止估算"
}
```

### Hybrid usage（原样；含诊断重复检索）

```json
{
  "embedding_calls": 44,
  "embedding_texts": 44,
  "embedding_prompt_tokens": 1058,
  "embedding_total_tokens": 1058,
  "embedding_usage_returned_by_api": true,
  "llm_calls": 22,
  "llm_prompt_tokens": 57149,
  "llm_completion_tokens": 1797,
  "llm_total_tokens": 58946,
  "llm_usage_returned_by_api": true,
  "cny_cost": null,
  "cny_cost_note": "未查账单；禁止估算"
}
```

## 主要失败（原 notes，未改写回答）

### Dense

- PROB-F02：应答题却 `no_evidence`（未编造）— 见 `prob-f02-readonly-notes-2026-10-20.md`
- HR-F01/F02/T01/X01：`page_ok` 未过（及 Dense 下 HR-T01 `fact_ok` 未过）— 页码口径见 HR 笔记

### Hybrid

- PROB-F02：同 Dense
- HR-F01/F02/T01/X01：主要为 `page_ok`；HR-T01 在 Hybrid 下 `fact_ok` 通过

## 相关笔记

- `hr-page-mapping-notes-2026-10-20.md` — PDF 页序 / 印刷页码 / `Chunk.page` 合并末页
- `prob-f02-readonly-notes-2026-10-20.md` — 只读证据边界（能证明 / 不能证明）

# Dense vs Hybrid 检索/核验对照（2026-10-20 Asia/Shanghai）

verifier=**developer**（不得称独立评测）。题集：`02-人工核验题集-v1.json`（22 题）。rerank=disabled。库=`univ_course_rag_cn_v2`。

## 机器状态

| 策略 | answered | no_evidence | system_error |
| --- | ---: | ---: | ---: |
| Dense | 16 | 6 | 0 |
| Hybrid | 16 | 6 | 0 |

## 人工分层（应答题 n=17；拒答题 n=5）

| 维度 | Dense pass/n (rate) | Hybrid pass/n (rate) |
| --- | --- | --- |
| fact_ok | 15/17 (0.882) | 16/17 (0.941) |
| citation_supports | 16/17 (0.941) | 16/17 (0.941) |
| page_ok | 12/17 (0.706) | 12/17 (0.706) |
| no_hallucination | 17/17 (1.0) | 17/17 (1.0) |
| refuse_correct | 5/5 (1.0) | 5/5 (1.0) |

## Hybrid 候选层（cosine 门前）

- 22 题合计：dense_only=431，keyword_only=431，both=273
- **Keyword-only 进入最终 evidence：0**（any=False）
- min_score_gate=0.45

一句话：当前实现下 Hybrid 会召回 Keyword-only 候选，但保守 cosine 门使其**无法**进入最终 evidence；本轮相对 Dense 的可见变化主要是排序/Top-k 组成（例：HR-T01 Hybrid 答对 must_include，Dense 偏到概论功能映射）。**不得**据此宣称 Hybrid 整体显著优于 Dense。

## Usage（API 返回；cny_cost=null）

### Dense
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

### Hybrid
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

说明：Hybrid runner 为统计候选另调一次 `retrieve_hybrid_candidates`，再调 `retrieve_chunks(hybrid)`，故 embedding_calls≈44（非演示默认路径的双倍计量，属本对照脚本开销）。

## 主要失败

### Dense
- {"id": "PROB-F02", "kind": "answer", "failed_dims": ["fact_ok", "citation_supports", "page_ok"], "status": "no_evidence", "notes": "应答题却 no_evidence（未编造）"}
- {"id": "HR-F01", "kind": "answer", "failed_dims": ["page_ok"], "status": "answered", "notes": "expected p5 cited p9；超出 ±1，不回改题集"}
- {"id": "HR-F02", "kind": "answer", "failed_dims": ["page_ok"], "status": "answered", "notes": "目录四块正确；cited p6/16 非 expected p2"}
- {"id": "HR-T01", "kind": "answer", "failed_dims": ["fact_ok", "page_ok"], "status": "answered", "notes": "答成吸纳/激励/维持/开发，未覆盖 must_include 规划/招聘等；且文档偏到概论 p34"}
- {"id": "HR-X01", "kind": "answer", "failed_dims": ["page_ok"], "status": "answered", "notes": "并列关系正确；cited p9 非 expected 2/3"}

### Hybrid
- {"id": "PROB-F02", "kind": "answer", "failed_dims": ["fact_ok", "citation_supports", "page_ok"], "status": "no_evidence", "notes": "与 Dense 同：应答题 no_evidence"}
- {"id": "HR-F01", "kind": "answer", "failed_dims": ["page_ok"], "status": "answered", "notes": "expected p5 cited p9"}
- {"id": "HR-F02", "kind": "answer", "failed_dims": ["page_ok"], "status": "answered", "notes": "多引了薪酬管理 PDF 片段；目录四块仍由绩效管理页支持；页码非 expected p2"}
- {"id": "HR-T01", "kind": "answer", "failed_dims": ["page_ok"], "status": "answered", "notes": "Hybrid 命中绩效管理回顾页，must_include 覆盖；cited p6 非 expected p3"}
- {"id": "HR-X01", "kind": "answer", "failed_dims": ["page_ok"], "status": "answered", "notes": "cited p9 非 expected 2/3"}

# Item 4 closeout — rerank residual & m5 pending cleanup

Date: 2026-10-19 (Asia/Shanghai)

## Rerank residual

- Working tree: **clean** for midterm closeout (rerank residual archived; `新开题资料.md` and docs already committed on `main`).
- Archive present: `corpus/local/rerank-archive-2026-10-19/` (patch + README).
- Live demo process: `RERANKER_BACKEND=disabled`, `RETRIEVAL_STRATEGY=dense`, `QUERY_EXPANSION_BACKEND=llm`, DB `univ_course_rag_cn_v2`.
- Conclusion: **已归档、不启用**；不恢复 patch，不装 rerank 依赖。

## M5 / 待核对测试脏数据

- Prior cleanup: `corpus/local/m5-cleanup-2026-10-19/result.json` deleted 35 `no_evidence` records.
- Re-explore cleanup: `corpus/local/m5-cleanup-reexplore-2026-10-19/result.json` deleted 17 more; verify-summary showed per-course `summary_no_evidence=0` / empty lists.
- Extra scan 2026-10-19: listable teacher pending (`error_code=NO_EVIDENCE`) count **0** after scan; remaining `outcome=no_evidence` rows are `NEEDS_CONTEXT` follow-ups (excluded from insights pending list by design).
- Attempted delete of leftover junk id `5d38d2cc-...` (`今天股市怎么样？`) → already gone (`m5-extra-cleanup.json` action=skip).
- Conclusion: **无需再处理** for demo pending list; backups remain in m5 evidence dirs.


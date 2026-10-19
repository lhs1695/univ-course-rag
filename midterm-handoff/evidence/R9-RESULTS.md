# R9 freeze refresh 2026-10-19

- Created: 2026-10-19T22:36:43.727163+08:00 (Asia/Shanghai)
- Code HEAD: `9bbb37b` (`9bbb37bc134e626b0ae5f91785958bce0386a22d`) on `main` (ahead of origin/main by 61)
- Demo DB name: `univ_course_rag_cn_v2` — scale **4/27/2501**, alembic `0011`
- Runtime: RERANKER=`disabled`, RETRIEVAL=`dense`, QUERY_EXP=`llm`
- Question set: `corpus/local/cn-replace-2026-10-18/cases.json` (16 cases)
- Eval pointer: `corpus/local/cn-replace-2026-10-18/eval-result.json`
- Rehearsal: `corpus/local/midterm-rehearsal-2026-10-19/` (see STATUS.md)
- Supersedes: `corpus/local/r9-recovery-2026-10-18/freeze/` (historical r7b6_real / 17/385)
- Excluded dirty file: `新开题资料.md` (not committed)
- Connection string passwords are **not** recorded.

Metrics cited from eval/rehearsal remain weak automated checks, **not** human factual accuracy.


## Post-commit refresh

- Final documented HEAD after NEXT-SESSION commit: `fa67bcf` (`fa67bcfb1c74d59d90c6813867453d7fb17ff3ff`), ahead 62
- PPT (gitignored `build/`): `build/midterm-presentation/output/final-v5.pptx`
- Rehearsal: PASS at `corpus/local/midterm-rehearsal-2026-10-19/`

# 阶段 23 交接

完成：阶段 22 已收敛：`QueryLog.hit` 保留为检索遥测；有检索命中但 LLM 未产生合法引用时，问答丢弃原始回答并返回 `NO_EVIDENCE`；学情的高频问句只统计 `error_code is None` 的可靠回答，`NO_EVIDENCE` 日志只进入拒答表。新增的无引用、全非法引用及命中后拒答的测试已覆盖这些合同。
验证：`pytest backend/tests/test_ask.py backend/tests/test_insights.py` 为 12 passed；仓库根 `python -m ruff check` 通过。首次受限环境无法访问 pytest 临时目录，随后用同一命令在本机临时目录完成验证。
留存：未修改黄金题、检索阈值或 API/数据库合同；未做阶段 23–25、阶段 18、19 未触发；不 push。
下一步：只做 `docs/plan-4.md` 阶段 23，建立向量索引身份与不一致保护，并按计划运行指定的 ingest/retrieve/ask 测试与 Ruff。

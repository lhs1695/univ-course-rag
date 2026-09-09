# 阶段 24 交接

完成：阶段 23 已收敛：持久化索引身份为 `backend|model|1024|v1`，Fake 与 SiliconFlow 即使模型名相同也不会混用；入库写该身份，检索只读取当前兼容切片。课程存在旧索引或混合索引时，问答返回 `EMBEDDING_MISMATCH` 和“向量模型已切换，请从原文件重新入库”，且不调用 LLM；问答页会显示该提示。
验证：`pytest backend/tests/test_ingest.py backend/tests/test_retrieve.py backend/tests/test_ask.py` 为 25 passed、1 skipped（无 key 的可选集成测试）；仓库根 `python -m ruff check` 通过；在 `frontend` 运行的 `npm run build` 通过。受限环境分别阻止 pytest 临时目录和 esbuild 子进程，随后在本机完成同命令验证。
留存：旧的裸模型名会被当作不兼容索引，须由教师删除原文件后重新上传；未通过向量长度猜来源、未改阈值或黄金题、未做阶段 24–25，阶段 18、19 未触发；不 push。
下一步：只做 `docs/plan-4.md` 阶段 24，先固定独立真模型评测协议和题集，再实现默认 dry-run、显式联网/计费开关的本地入口；pytest/CI 不得调用云。

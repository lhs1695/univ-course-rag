# 阶段 25 交接

完成：阶段 24 已收敛。新增独立真模型评测协议和 `python -m app.eval` 本地入口；默认 dry-run，真运行必须同时提供 `--run --allow-cloud`、课程 ID 和输出路径。22 条固定题覆盖 PDF/PPTX 单点事实、跨页归纳、中问英料、相似无答案、完全无关和删除对照，题集只在已忽略的 `corpus/local/`。
实证：新建独立本地评测课，两份 MIT OCW 公共课件以 `siliconflow|BAAI/bge-m3|1024|v1` 成功形成 38 个切片；DeepSeek 真评测结果为 Recall@k 1.000、有效引用率 1.000、拒答准确率 1.000、p50 2148.5 ms、p95 4553.4 ms，无失败项。匿名汇总已提交，原题、答案、引用正文、key 和逐次输出均不提交。
验证：`pytest backend/tests/test_eval.py` 与仓库根 `python -m ruff check` 通过。未修改 `golden.json`、`top_k=8` 或 `min_score=0.15`；本次没有阈值调整证据。阶段 18、19 未触发；不 push。
下一步：只做 `docs/plan-4.md` 阶段 25，组织至少一名非开发者按 `docs/demo.md` 自行试用，记录匿名反馈并据事实决定阶段 18、19 是否触发。

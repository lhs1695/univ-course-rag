# 阶段 28：pgvector Top-K 证明

日期：2026-09-09

## 实现边界

- Postgres 路径只选择 `id`、`document_id`、`page`、`text` 和计算出的距离，不再把全课程的 1024 维向量传回 Python。
- 课程、索引身份、排除文档和最低相似度均进入 SQL；数据库使用 pgvector `<=>` 计算余弦距离、升序排序并 `LIMIT top_k`。
- SQLite + Fake 路径保留 Python 排序，保证普通 pytest 不依赖 Docker 或云 key。
- 索引不一致检查改为 SQL `EXISTS`，不再加载全课程的 `embedding_model` 列。

## 索引选择

迁移 `0005_chunk_search_filter_index.py` 增加 `(course_id, embedding_model)` 复合 B-tree，先缩小需要精确计算距离的课程内兼容候选集。本阶段没有添加全局 HNSW/IVFFlat：当前查询始终带强课程与模型过滤，近似索引在过滤后可能少返回候选；在没有课程规模、召回回归和 pgvector iterative-scan 版本约束前，不用近似性能换掉现有精确 Top-K 合同。

未来只有规模基准证明精确查询不够时，才单独评估分区、部分索引或支持过滤递补的 ANN 方案，并用 Recall@k 对照验证。

## 本机证明

在项目 `backend/.venv` 与 compose Postgres 上完成：

1. `alembic upgrade head` 成功执行 `0004 -> 0005`。
2. `alembic downgrade 0004` 后再次 `alembic upgrade head` 均成功，最终数据库保持 head。
3. 显式 Postgres 集成测试在事务内插入隔离数据，验证索引存在、真实 `<=>` 查询返回两个 Top-K，首条精确匹配得分约为 `1.0`，测试结束回滚数据。
4. 同一测试对实际语句执行 `EXPLAIN`，确认计划包含 `Limit` 与 `Sort Key: ((embedding <=> ...)`；小数据集不强制规划器选择某一访问路径。
5. 编译测试确认 SQL 包含课程、索引身份、排除文档、距离阈值、向量排序和 `LIMIT`，且选择列表不包含原始 embedding 列。

Postgres 证明需要显式设置 `RUN_POSTGRES_TESTS=1`；默认 pytest 会跳过它，不访问云服务。

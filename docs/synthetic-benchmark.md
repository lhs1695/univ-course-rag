# 合成规模基准

阶段 41 的基准入口只生成固定规则的 Markdown 合成资料，不读取上传目录、真实课件、真实提问、`.env` 中的云 key，也不调用云模型。它复用正式的解析、切片、Fake embedding 批处理、数据库写入和检索代码；临时原文与 SQLite 数据库在命令结束后删除，输出只包含聚合指标。

## 运行

仓库根目录使用后端虚拟环境：

```powershell
backend\.venv\Scripts\python.exe -m app.benchmark --run `
  --database sqlite `
  --scales 100,500,1000 `
  --retrieval-runs 6 `
  --output docs/synthetic-benchmark-baseline.json
```

不带 `--run` 时只校验参数并输出 dry-run 摘要。规模必须升序且不重复，一次最多 6 档，每档 1–10000 个 chunk；embedding 批次限制为 1–256，单档检索次数限制为 1–20。

Postgres/pgvector 使用同一合成载荷和 FakeEmbedder，但必须明确选择并确认临时写入：

```powershell
backend\.venv\Scripts\python.exe -m app.benchmark --run `
  --database postgres `
  --allow-postgres `
  --scales 100,500,1000 `
  --output corpus/local/synthetic-benchmark-postgres.json
```

Postgres 路径使用本机配置的 `DATABASE_URL`，但报告不保存 URL。每档数据使用随机隔离 ID，并在该档完成或失败后删除课程、资料、切片和测试用户；中途强制终止仍可能留下标题或用户名以 `Synthetic benchmark` / `synthetic-benchmark-` 开头的合成记录，应在重跑前检查。本地 Postgres 原始输出放已忽略的 `corpus/local/`；仓库只保留经过检查的聚合基线。

## 报告口径

- `database_path` 明确区分 SQLite 的 Python 精确排序路径与 PostgreSQL 的 pgvector SQL 路径。
- 入库记录端到端耗时、实际 chunk 数、embedding 批次数和最大批次。
- 检索记录固定次数的 p50/p95、返回数范围和 Top-1 合成目标命中率。
- `resource_units` 记录合成源字节数和 1024 维向量元素数量，用于解释工作量增长；它不是进程 RSS、数据库占用或整机资源测量。
- 环境摘要只含 Python、操作系统/架构和 SQLAlchemy 版本，不含主机名、账号、路径、数据库 URL 或密钥。

## 回归判读

正确性是硬门槛：实际 chunk 数必须等于目标规模、每次检索必须返回结果、Top-1 合成目标命中率必须为 1。pytest 只验证这些确定性事实，不对耗时做断言。

性能只作同环境趋势证据。至少重复运行 3 次，保持脚本版本、数据库路径、规模、批次和检索次数一致后，再比较各档中位数。相同规模的检索 p95 或入库耗时中位数增加超过 50% 时才标为“需要调查”，不能直接判为功能回归；系统更新、后台负载和冷缓存均可能造成差异。单次小样本、Fake embedding、SQLite 数字和合成 Top-1 命中率都不能外推为真实课程准确率或生产容量承诺。

## 2026-09-10 本机基线

环境为 Windows AMD64、CPython 3.12.10、SQLAlchemy 2.0.52，FakeEmbedder 批次 32，每档检索 6 次。详细 SQLite 聚合报告见 [`synthetic-benchmark-baseline.json`](synthetic-benchmark-baseline.json)。数字是单次本机观察，只用于展示规模退化形态：

| 路径 | chunks | 入库 ms | 检索 p50 / p95 ms | 返回数 | Top-1 合成目标 |
| --- | ---: | ---: | ---: | ---: | ---: |
| SQLite 精确 Python 排序 | 100 | 431.3 | 35.7 / 37.0 | 8 | 1.000 |
| SQLite 精确 Python 排序 | 500 | 3136.3 | 599.9 / 625.9 | 8 | 1.000 |
| SQLite 精确 Python 排序 | 1000 | 13303.6 | 1371.9 / 1502.1 | 8 | 1.000 |
| PostgreSQL pgvector SQL | 100 | 555.0 | 49.3 / 53.0 | 8 | 1.000 |
| PostgreSQL pgvector SQL | 500 | 3925.4 | 56.1 / 64.2 | 8 | 1.000 |
| PostgreSQL pgvector SQL | 1000 | 15918.6 | 58.6 / 65.1 | 8 | 1.000 |

本次 Postgres 报告写入已忽略的 `corpus/local/synthetic-benchmark-postgres.json`，运行后核对合成课程和合成用户余留数均为 0。SQLite 的 Python 排序检索随 chunks 明显增长；本次 pgvector SQL 路径在相同档位下更平缓。该差异只是当前机器、当前合成载荷的一次路径证据，不是容量结论，也不触发 `top_k`、`min_score` 或索引算法调整。

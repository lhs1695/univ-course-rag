# 当前交接

更新：2026-10-17（Asia/Shanghai）。

## 当前状态

- 主仓：`main`（相对 `origin/main` ahead；以最新本地提交为准）。现场必须保留的未提交文件：`frontend/src/views/AskView.vue`、`新开题资料.md`。
- **轻量路线已推进到 R7B-6B 通过（Fake 受控入库）：** R7B-L1…L3、R7B-5 仍有效；本卡在隔离库 `univ_course_rag_r7b6`（alembic `0011`）为四课各入库 1 份代表 PDF（Fake embedder，共 74 chunks），检索串课隔离抽检通过。
- 旧库 `univ_course_rag`（R7 心理基线：1 课 / 4 资料 / 257 chunks）**未改动**；已留 custom dump：`corpus/local/r7b-6-controlled-ingest-2026-10-17/dumps/univ_course_rag_pre_r7b6.dump`。
- Docling 历史实验仍停在 8/17；独立 worktree `feat/r7b4-offline-freeze` **不要**合并、续跑或删除。
- 另有 worktree `feat/r7b-l1-pymupdf-gate`（实施 L1 时用）；合入主仓后可另议清理。

## 已完成证据（忽略区，不入 Git）

| 卡 | 目录 / 要点 |
| --- | --- |
| R7B-L2 | `corpus/local/r7b-l2-representative-pages-2026-10-17/` |
| R7B-L3 | `corpus/local/r7b-3-pymupdf-freeze-2026-10-17/`（17/17） |
| R7B-5 | `corpus/local/r7b-5-question-set-2026-10-17/`（28 题 dry-run） |
| R7B-6B | `corpus/local/r7b-6-controlled-ingest-2026-10-17/`（隔离库四课×1 PDF Fake 入库；`RESULT.json` / `SUMMARY.md`） |

## 下一项：R7B-6 收口或 R7B-7（须另授权）

可选继续：

1. **R7B-6 小样本（题集）：** 在 `univ_course_rag_r7b6` 上对 R7B-5 每课少量开发题跑 Fake 检索/（若授权）生成抽检；仍可不调真实模型。
2. **R7B-7 四课新基线：** 须另授权真实 SiliconFlow embedding（及可选 DeepSeek）；**不可**把 Fake 索引冒充正式基线。重嵌入前确认目标库、预算与是否清空/重建 r7b6 向量。

无论哪条：先 `git status` 保护未提交改动；不默认 push；不续跑 Docling。

## 后续顺序

R7B-6 小样本收口（可选）→ R7B-7 四课新基线（真实模型须另授权）→ P7 产品化收口 → R8 内部联合验收 → R9 冻结与展示。

## 已知限制（带入后续）

- 心理学纯图/矢量页、历史图内字、线代公式控制字符：文字路径可入库但覆盖不全。
- `01_introduction.pdf` 在心理学与哲学重名；必须带 `course_id`（本卡已抽检隔离通过）。
- 本机 `.env` 仍指向旧库 + siliconflow；服务进程若读 `.env` 不会自动连到 `univ_course_rag_r7b6`。
- Fake 索引身份 `fake|BAAI/bge-m3|1024|v1` 与 SiliconFlow 身份不同；正式评测前须重嵌入。

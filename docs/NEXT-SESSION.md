# 当前交接

更新：2026-10-17（Asia/Shanghai）。

## 当前状态

- 主仓：`main`（相对 `origin/main` ahead；以最新本地提交为准）。现场必须保留的未提交文件：`frontend/src/views/AskView.vue`、`新开题资料.md`。
- **轻量路线已推进到 R7B-5 通过：** R7B-L1 代码切回 PyMuPDF 默认入口 + 页级质量门禁；R7B-L2 代表页核对通过；R7B-L3 17 份/344 页轻量冻结通过；R7B-5 四课题集 + Fake/dry-run 通过。
- Docling 历史实验仍停在 8/17，产物在 `corpus/local/r7b-4-docling-2026-10-17/`；独立 worktree `feat/r7b4-offline-freeze` **不要**合并、续跑或删除。Docling 适配器代码保留作可选旁路，不是生产默认。
- 另有 worktree `feat/r7b-l1-pymupdf-gate`（实施 L1 时用）；合入主仓后可另议清理，本卡不自动删除。

## 已完成证据（忽略区，不入 Git）

| 卡 | 目录 / 要点 |
| --- | --- |
| R7B-L2 | `corpus/local/r7b-l2-representative-pages-2026-10-17/` |
| R7B-L3 | `corpus/local/r7b-3-pymupdf-freeze-2026-10-17/`（17/17，墙钟约 1.95s，峰值 RSS 约 119MB） |
| R7B-5 | `corpus/local/r7b-5-question-set-2026-10-17/`（28 题；dry-run `case_count=28`；`test_eval` 21 passed） |

## 下一项：R7B-6（须另授权）

按 [轻量解析计划](implementation-plan.md#r7b-lightweight-plan) 做**受控入库与每课小样本**：

1. 先 `git status`，保护未提交改动；明确目标库与恢复点。
2. 仅在用户当次授权下：迁移核对、按 L3 身份入库四课（或分课）、记录 chunking/index 身份；致命失败不覆盖旧完整索引。
3. 用 R7B-5 题集做每课小样本（仍可先 Fake；真实 embedding/LLM 须再授权）。
4. 不续跑 Docling，不默认全量 Vision，不 push。

## 后续顺序

R7B-6 受控入库/每课小样本（须另授权）→ R7B-7 四课新基线（真实模型须另授权）→ P7 产品化收口 → R8 内部联合验收 → R9 冻结与展示。

## 已知限制（带入后续）

- 心理学纯图/矢量页、历史图内字、线代公式控制字符：文字路径可入库但覆盖不全；题集中已用拒答/缺口题标注，不等于多模态已解决。
- `01_introduction.pdf` 在心理学与哲学重名；评测必须带 `course` / 分课 `course_id`。
- R7B-5 标注为 L3 溯源、**无独立人工复核**；事实指标不得写成人工正确率。

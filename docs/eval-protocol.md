# 真模型评测协议

本协议用于独立衡量已入库本地试用课的检索、引用、拒答和延迟；它不替代 pytest，也不修改 `backend/tests/fixtures/golden.json`。只在维护者明确允许联网和计费时运行。

## 先固定本地题集

在已忽略的 `corpus/local/eval-cases.json` 建立 20–30 条案例。题集不得进入 Git，也不得使用真实学生问题、完整私密课件或任何 key。每项固定 `id`、`category`、`query`、`expected_documents`（课程资料的文件名列表）和 `should_refuse`。拒答题的 `expected_documents` 必须为空；可回答题必须至少有一个预期文件。删除对照题可用 `excluded_documents` 列出本次评测中视为已删除的文件；评测器会在索引身份检查和 Top-K 排序前排除这些文件，无需破坏本机课程数据。

类别至少覆盖：PDF 单点事实、PPTX 单点事实、跨页归纳、中文问英文资料、相似但无答案、完全无关、删除资料后的对照。每类保留失败样本，不得为分数删除或重写题目。

示例结构（仅示意，不能作为可运行题集）：

```json
{
  "cases": [
    {
      "id": "pdf-fact-01",
      "category": "pdf_fact",
      "query": "维护者自行编写的非学生验证问题",
      "expected_documents": ["本机 PDF 文件名.pdf"],
      "should_refuse": false
    }
  ]
}
```

## 运行

先验证题集；默认 dry-run 只读取和校验案例，不连数据库、不调用 embedding 或 LLM：

```powershell
backend\.venv\Scripts\python.exe -m app.eval --case-file corpus/local/eval-cases.json
```

真运行前，维护者须在本机 `.env` 设定 SiliconFlow embedding 与 DeepSeek LLM，重启或重开 shell，并确认该课程已用当前索引身份重新入库。下列两个开关是刻意分开的：`--run` 表示执行，`--allow-cloud` 表示明确允许联网和产生费用。缺少任一开关、课程 ID 或输出路径时，入口拒绝执行。

```powershell
backend\.venv\Scripts\python.exe -m app.eval `
  --case-file corpus/local/eval-cases.json `
  --run --allow-cloud `
  --course-id <本机试用课 UUID> `
  --output corpus/local/eval-result-summary.json
```

输出只保存汇总和失败案例的 ID、类别、失败类型、Recall@k、有效引用标志、拒答判定和延迟；不会保存 query、答案、引用摘录、课件正文或 key。建议将输出也保留在已忽略的 `corpus/local/`。

## 中断与恢复

真运行每完成一题都会通过原子替换更新 `--output` 指定的 checkpoint。因此 API 或网络异常时，之前已经完成的付费题目不会丢失；异常题会记录 `evaluation_error`、异常类别及固定安全摘要，不保存供应商原始错误文本。中断后使用相同的命令并加 `--resume` 恢复：

```powershell
backend\.venv\Scripts\python.exe -m app.eval `
  --case-file corpus/local/eval-cases.json `
  --run --allow-cloud --resume `
  --course-id <同一课程 UUID> `
  --output corpus/local/eval-result-summary.json
```

恢复会严格比较题集 SHA-256、课程 ID、embedding backend/model 和 LLM backend/model；任一不同都会拒绝，不能把不同配置的指标拼在一起。已完成题会跳过，异常题会重新执行。全部题成功后 checkpoint 自动收敛回原有的 `summary`、`failures` 与 `metadata` 汇总格式。

## 判读与后续

记录四项主指标：正确文件 Recall@k、可回答题的有效引用率、拒答准确率、p50/p95 延迟；失败类型包含索引不一致、检索漏召回、意外拒答、意外回答和缺少合法引用。先按类别审查失败清单，再决定是否另立调参阶段。不能因为一次结果而直接修改 `top_k=8` 或 `min_score=0.15`；若有稳定收益证据，阈值修改必须单独提交并重跑 `test_retrieve.py`、`test_ask.py` 与 Ruff。

2026-09-09 已按本协议完成一次 22 题真评测，匿名汇总见 [`eval-result-summary.json`](eval-result-summary.json)。题集哈希随汇总保存，原题集和逐次本机输出仍只在 `corpus/local/`。本次无失败项，因此没有调整检索阈值。

# PLAN-09 开发者 Fake/API 排练日志

**证据层：开发者 Fake HTTP / 定向 pytest / Node 逻辑 smoke。≠ 独立用户试用，≠ Vite 浏览器人工观察。**

| 项 | 值 |
| --- | --- |
| 记录日期 | 2026-10-23（Asia/Shanghai）；文件名沿用脚本索引冻结名 `rehearsal-log-2026-10-22.md` |
| 脚本版本 | `p09-tasks-v1` |
| 代码基线（排练前 HEAD） | `d8e7d04`（PLAN-08） |
| 执行者 | 开发者 / 施工 agent（参与开发：是） |
| 环境 | Windows；`backend/.venv` Python 3.12；隔离 SQLite + FakeEmbedder/FakeLLM；`--basetemp output/plan09-pytest-…` |
| 模型 / 检索 | Fake / dense / rerank 关 |
| 云费用 | ¥0；未读 `.env`；未操作正式库或 `corpus/local` |
| 独立试用 | **未执行**（无未参与开发者参与者；未招募、未外发） |

## 覆盖对照（脚本 ↔ Fake 证据）

| 脚本任务 | Fake/API 证据 | 明确未覆盖 |
| --- | --- | --- |
| S1 提问→回答→依据→原 PDF 页 | `test_student_answer_evidence_and_pdf_content`（JSON 与 SSE 终态）：citation 页=2、`content_url` 返回 inline PDF 字节、PyMuPDF 读出目标页原文 | 浏览器点引用 / `#page=` 跳页 / Vite 视觉核对 |
| S2 依据不足 | `test_insufficient_evidence…`：停用检索后 `NO_EVIDENCE`、HTTP 200、无 citations；原文仍可读 | 用户是否理解恢复路径的人工观察 |
| S3 系统故障 | 同上：TimeoutLLM → 504 `UPSTREAM_TIMEOUT`、无供应商细节泄漏；恢复后 `cited_answer`；QueryLog outcome 集合含 no_evidence/failure/cited_answer | Vite 故障提示与人工重试体验 |
| S4 流式/取消/重试 | 既有 `frontend/tests/askStream.test.mjs` 4/4 PASS（逻辑 smoke） | Vite 等待态/取消/迟到覆盖人工清单仍全部待执行 |
| T1 资料质量 | 教师文档列表：`succeeded`+`COVERAGE_INCOMPLETE` vs `failed`+`INGEST_FAILED` | 打开 PDF 人工质量判断 |
| T2 候选与动作 | 同问句 2 次后 themes `cited_repeat`；POST insight-review confirmed/undecidable/clarify_in_class | 教师独立核对与 UI 表单操作 |
| T3 刷新持久化 | 清 ORM + 重登录后两次 GET 列表仍等于保存体；学生 POST 403 | 浏览器整页刷新体验 |

## 实际命令与原始输出摘要

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan09_core_user_tasks.py -q --basetemp output/plan09-pytest-20261023-fix -p no:cacheprovider
```

退出 0：

```text
....                                                                     [100%]
4 passed, 1 warning in 2.01s
```

警告：`DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated`（既有 Starlette）。首轮曾因 themes 仅在 `cited_answer` 次数 ≥2 时出现而 `StopIteration`；测试改为同问句提问两次后通过，未改业务代码。

```powershell
backend/.venv/Scripts/python.exe -m ruff check backend
```

退出 0：`All checks passed!`

```powershell
node frontend/tests/askStream.test.mjs
```

退出 0：`tests 4 / pass 4 / fail 0`（约 29ms）。**不能勾选 S4 人工清单。**

`npm run build`：**本卡未改 UI，记录不适用（N/A）**；PLAN-08 本机曾遇 Vite/esbuild `spawn EPERM`，构建门槛不在本卡以 Fake 绿测关闭。

## 独立试用缺口（诚实）

- 学生独立完成 n/N：**未观察**（计划 N=4）
- 教师独立完成 n/N：**未观察**（计划 N=3）
- 不得宣告「独立试用已完成」或 PASS
- 阻断复测：无人工阻断记录（本轮无 Vite 观察）
- 下一步：有未参与开发者且获授权后，按观察表从 Vite 执行；S4/T3 浏览器项与 PLAN-08 构建环境问题另补证

合同：[PLAN-09 任务卡](../tasks/PLAN-09-core-user-tasks.md) · [脚本索引](README.md)

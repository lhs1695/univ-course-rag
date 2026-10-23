# PLAN-10 结题交付核对表与干净环境步骤

冻结日期：2026-10-23（Asia/Shanghai）。**本文件是交付清单与可执行步骤；不以 Fake/排练冒充独立核验、用户试用或空白机全流程 PASS。**

| 项 | 值 |
| --- | --- |
| 代码冻结参考（PLAN-09 提交） | `b7f1b3a`；本卡提交见任务卡完成记录 |
| Alembic head | `0013`（`0011_query_outcomes` → `0012_document_retrieval_enabled` → `0013_insight_reviews`） |
| Python / Node / npm（本机施工环境） | 3.12.10 / v24.20.0 / 11.19.0 |
| 后端/前端包版本字段 | `0.0.0`（未做产品发版号 bump） |
| 默认演示配置口径 | dense、rerank 关；正式库名 `univ_course_rag_cn_v2` |
| 云费用（本卡） | ¥0；未读 `.env`；未全量重解析/重入库/Vision |
| 空白隔离机全流程 | **未执行（用户指示暂缓）**（见 §4 缺口） |

合同入口：[PLAN-10 任务卡](tasks/PLAN-10-final-delivery.md) · [validation §1/§6–7](validation.md) · [完工门槛 §6.A–G](结题产品定义与完工标准.md) · [workflow](workflow.md) · 根 [README](../README.md)

---

## 1. 交付物清单（路径核对）

| 类别 | 路径 / 说明 | 本轮状态 |
| --- | --- | --- |
| 可运行源码 | Git 工作区 `main`；不 push | 有 |
| 依赖锁定 | `backend/pyproject.toml`（`pip install -e ".[dev]"`）；`frontend/package-lock.json` + `npm ci` | 有 |
| 无密钥配置示例 | `.env.example`（勿提交 `.env`） | 有；本卡未打开 `.env` |
| 迁移 | `backend/alembic/`，head `0013` | 有 |
| 启动 / 工作流 | 根 README「克隆后启动」；[workflow.md](workflow.md)；[中期演示运行卡.md](中期演示运行卡.md) | 有 |
| 架构 / 权限 / 生命周期 | [架构说明.md](架构说明.md)、[lifecycle-permissions-matrix.md](lifecycle-permissions-matrix.md)、[engineering.md](engineering.md) | 有 |
| 许可证 | 根 [LICENSE](../LICENSE)（MIT，自有代码/文档）；[NOTICE](../NOTICE)（课件树不在 MIT 内） | 有 |
| 数据公开边界 | NOTICE + README 密钥纪律；日志/问句不可当系统指令（AGENTS） | 有文字；无「公开数据集发布」授权声明外扩 |
| 自动化证据 | 本卡回归摘要 §3；既有定向测试分散在 `backend/tests/` | Fake 全量见 §3 |
| 冻结题集 / 评分 | [evaluation-results.md](evaluation-results.md)；中期研究证据包 | 历史/开发者核验为主 |
| 检索证据 | [retrieval-evidence-regression.md](retrieval-evidence-regression.md) | Fake+历史；真实复跑/独立核验缺口 |
| 学情验证 | [analytics-validation-protocol.md](analytics-validation-protocol.md) 等 | 框架；正式人工/独立教师试用缺口 |
| 性能 | [stream-performance-baseline.md](stream-performance-baseline.md) | Fake 1/5/10；真实模型未测 |
| 用户任务 | [user-task-scripts/](user-task-scripts/README.md) | 脚本+Fake；独立试用取消→[开发者 Vite 观察](user-task-scripts/observation-2026-10-23-developer.md) |
| 操作指南 / 演示 | README、中期演示运行卡、中期答辩材料 | 有；结题专用「空白机录屏」未做 |
| 备份恢复说明 | 本文 §2.5（隔离演练步骤） | 有文档；**未在隔离环境实跑** |

---

## 2. 干净环境步骤（可判定命令）

目标：按文档在**不依赖本机隐含手改**的前提下装起来。以下与根 README / workflow 对齐。本轮在已有开发工作区执行回归与构建；**空白机实装演练标记为未完成**。

### 2.1 前置

- Windows + Git + Python 3.12 + Node 20+ + Docker Desktop
- 克隆仓库到新目录；**不要**复制开发机 `.env`
- `Copy-Item .env.example .env` 后本机填写；密钥永不入库

### 2.2 依赖与数据库

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
cd ..
cd frontend
npm ci
cd ..
docker compose up -d
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app
cd ..
```

### 2.3 启动与基础健康检查

```powershell
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
# 另窗
cd frontend
npm run dev
```

浏览器走 Vite（如 `http://127.0.0.1:5173`），勿直连 `:8000` 登录。检查 `/health`、`/ready`。引用开 PDF 需 `UPLOAD_DIR` 与库内路径一致；完整演示依赖 `univ_course_rag_cn_v2` 数据与课件树（见 NOTICE），**本卡不授权重建/重入库**。

### 2.4 基础任务（人工，空白机待做）

三角色登录 → 学生授权提问 → 回答/依据/引用回原 PDF 页 → 教师资料质量与 insight 处理记录（刷新仍在）。记录命令、截图位置与失败；不得用 Fake pytest 勾选本条。

### 2.5 隔离备份与恢复（文档步骤；正式库禁碰）

仅在**隔离** Postgres（非生产/非正式演示长驻库）演练：

```powershell
# 示例：逻辑备份（容器名/库名以本机 compose 为准；勿对正式长驻库试验性 drop）
docker compose exec -T db pg_dump -U postgres univ_course_rag_cn_v2 > backup-demo.sql
# 恢复到隔离空库（先创建目标库；命令需按实际容器服务名调整）
# docker compose exec -T db psql -U postgres -c "CREATE DATABASE univ_course_rag_restore_drill;"
# Get-Content backup-demo.sql | docker compose exec -T db psql -U postgres univ_course_rag_restore_drill
```

文件侧：备份 `UPLOAD_DIR` 目录树；恢复后核对 `/ready`、抽查一份 PDF content。演练记录须含时间、源/目标库名、是否成功；**本轮未执行**。

### 2.6 交付门禁命令（本机已跑）

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests -q --basetemp output/plan10-pytest-full2 -p no:cacheprovider
backend/.venv/Scripts/python.exe -m ruff check backend
cd frontend; npm run build
```

原始摘要见 §3 与 [final-delivery-gate.output.txt](final-delivery-gate.output.txt)。

---

## 3. 本机门禁原始摘要（2026-10-23）

### pytest（修复两处过时断言后）

首轮全量：`2 failed, 639 passed, 2 skipped`：

1. `test_ingest_errors_and_legacy_job_details_do_not_expose_raw_text`：裸 `Document()` 缺 `retrieval_enabled`（0012 后 pydantic 要求 bool）
2. `test_query_outcome_migration_does_not_invent_historical_facts`：误要求 alembic head==`0011`，实际 head=`0013`

最小修复：测试夹具补 `retrieval_enabled=True`；0011 行为测试改为断言 revision 存在于历史，不再钉死 head。业务代码未改。重跑：`641 passed, 2 skipped, 1 warning in 54.45s`（exit 0）。详见 `final-delivery-gate.output.txt`。

### ruff

退出 0：`All checks passed!`

### frontend build

退出 0：`vite build` ✓ built in ~8.26s；有 chunk>500kB 提示，非失败。

### 未执行 / 不适用

- 真实云调用、全量解析/重入库、Vision、rerank 开启：**未授权未执行**
- Vite 核心闭环：开发者代观察已执行（见 `user-task-scripts/observation-2026-10-23-developer.md`）；**非独立试用**
- 空白隔离机从零安装 + 备份恢复实操：**未执行（用户指示暂缓）**
- 真实模型小样本：已留证（估费 <¥1；见 evidence-2026-10-23）

---

## 4. validation / 完工门槛诚实登记（摘要）

| 门槛 | 证据层 | 判定 |
| --- | --- | --- |
| §6.A 安全与一致性 | 既有权限/生命周期测试 + PLAN-02 矩阵 | 自动化有；完整人工矩阵点检未在本卡重做 |
| §6.B 答案与证据 | PLAN-07 报告 + 中期 22 题开发者核验 | **独立核验/真实复跑缺口保留** |
| §6.C 用户任务 | PLAN-09 脚本 + Fake + 开发者 Vite 观察 | **独立试用取消**；开发者观察已留证（非独立） |
| §6.D 可复现部署 | 本文步骤 + 本机回归/构建 | **空白机实装与备份恢复暂缓** |
| §6.E 交付完整 | §1 清单 | 材料基本齐；结题录屏/空白机证据缺 |
| §6.F 学情闭环 | PLAN-03～06 | 功能+Fake；正式人工评价/独立教师试用缺口 |
| §6.G 流式性能 | PLAN-08 Fake 基线；本机 build；开发者 Vite S4 | 真实模型高并发测量仍缺 |
| validation §7 | 本清单 | **不得宣告结题验收通过 / 不得默认发布** |

---

## 5. 第三方与数据边界（短表）

| 项 | 说明 |
| --- | --- |
| 自有代码/文档 | MIT（根 LICENSE） |
| 课件 PDF | NOTICE：不在 MIT 内；演示用公开教学资料口径 |
| 运行时依赖 | 见 `backend/pyproject.toml`、`frontend/package-lock.json`；发布前应用工具生成完整归属表（本卡未另生成 SPDX 全表） |
| 密钥 / Cookie / Session / 原题答案 | 禁止入库与交付物粘贴；本卡未读取 `.env` |

---

## 6. 维护

更新本表时同步 [PLAN-10 任务卡](tasks/PLAN-10-final-delivery.md)、[SESSION_STATE](tasks/SESSION_STATE.md)、[INDEX](INDEX.md)。缺口关闭须另附原始命令输出，禁止只改勾选。

## 2026-10-23 进度补记（开发者）

- 独立试用：用户指示取消；开发者 Vite 代观察见 `docs/user-task-scripts/observation-2026-10-23-developer.md`。
- 空白机安装+备份恢复：用户指示暂缓。
- 真实小样本：`docs/user-task-scripts/evidence-2026-10-23/real-small-sample-2026-10-23-developer.json`（估费 <¥1）。

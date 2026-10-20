# 基于大模型与 RAG 的高校课程知识库智能问答系统

面向高校各类课程的**有依据、可核对**问答原型：以教师提供的课内资料为主要依据，经检索增强生成（RAG）给出回答与引用，学生可回到原 PDF 页核对。开源组件适配，本机演示；结题争取小范围多人试用。

> **研究方案详版**见 [`新开题资料.md`](新开题资料.md)（本稿为对外入口摘要，非开题全文拷贝）。

## 队友三件套（中期答辩优先看）

| 材料 | 说明 |
| --- | --- |
| [中期答辩材料/](中期答辩材料/README.md) | PPT、讲稿、彩排截图、彩排 PASS、架构图示 |
| [docs/架构说明.md](docs/架构说明.md) | 边界、模块、数据表、提问时序、配置与路由对照 |
| [docs/中期演示运行卡.md](docs/中期演示运行卡.md) | 切库、启动、固定问句、故障降级与汇报口径 |

## 背景与目标（摘要）

高校课程知识分散在讲义与课件中；通用大模型回答流畅，却未必对应当前课程口径，也难核验出处。本项目建设课程知识库智能问答系统，围绕**学生 / 教师 / 管理员**提供：资料管理、授权问答、引用追溯、依据不足提示，以及教师侧提问反馈。

研究与工程路线为**开源复用驱动**的应用开发：生产 PDF 使用 **PyMuPDF** 轻量解析 + 页级质量门禁（Docling 全量路线已停）；借鉴 RAGFlow / Kotaemon / Dify 等局部设计，不整体迁移平台。中期不宣称通用 OCR/公式/图表理解或生产多租户。

## 中期范围与四课

| 项 | 值 |
| --- | --- |
| 正式库 | `univ_course_rag_cn_v2` |
| 规模 | **4 门课 / 27 份 PDF / 2,501 chunks** |
| 课程 | 线性代数、概率论与统计学、人力资源管理、教育学原理 |
| 课件路径 | `corpus/local/cn-replace-2026-10-18/rechunk/uploads_v2/`（私人仓已纳入，约 57MB） |
| 检索 | dense；**rerank 未启用** |
| 弱规则验收 | 可答题预期文档/页 12/12，拒答 4/4（**≠ 人工事实正确率**） |

旧英文四课与 `r7b6_real` 的 17/385 仅为历史对照。

## 技术栈（仓库事实）

- **前端**：Vue 3 + Vite + Element Plus
- **后端**：FastAPI + SQLAlchemy + Alembic（Python 3.12，`backend/.venv`）
- **数据**：PostgreSQL + pgvector（向量维 1024）
- **解析 / 切分**：PyMuPDF；semantic-text-splitter
- **模型**：SiliconFlow `BAAI/bge-m3`（Embedding）；DeepSeek 文本生成；pytest 默认 FakeEmbedder / FakeLLM

数据流一句话：上传 → 解析切分向量化 → 课内 dense 检索 → 证据约束生成 + 引用 → 前端 `#page=` 回原 PDF。结构详解见 [docs/架构说明.md](docs/架构说明.md)。

## 三角色能做什么

| 角色 | 能力摘要 |
| --- | --- |
| 学生 | 登录后进入已加入课程；提问；查看引用并打开原资料；浏览课内资料列表 |
| 教师 | 课内资料上传/入库状态；成员管理；问答反馈（高频/依据不足等描述性统计） |
| 管理员 | 全局账号与课程授权；日志留存维护；系统状态（库 / 向量 / 生成配置） |

全局角色 ≠ 自动拥有课内读写权；须课程成员关系。登录为 HTTP-only Cookie Session（非 JWT）。

## 克隆后启动摘要

1. 复制 `.env.example` 为本地 `.env`（**勿提交**）；确认 `DATABASE_URL` / `POSTGRES_DB` 为 `univ_course_rag_cn_v2`，并设置 `UPLOAD_DIR` 指向上述课件目录。
2. `docker compose up -d` 启动 Postgres（默认库名已与 cn_v2 对齐）。
3. 在 `backend`：`.venv` 内 `alembic upgrade head`，再 `python -m app` seed 演示账号。
4. 仓库根启动 uvicorn `:8000`；`frontend` 下 `npm run dev`，浏览器打开 Vite 地址登录（勿直连后端端口）。

逐步命令、固定问句与故障降级见 [中期演示运行卡](docs/中期演示运行卡.md) 与 [workflow](docs/workflow.md)。演示账号口令见 seed 默认值，**勿写入 PPT 或公开群**。

## 文档索引（精简后）

| 文档 | 用途 |
| --- | --- |
| [新开题资料](新开题资料.md) | 研究方案详版 |
| [AGENTS](AGENTS.md) | 协作纪律与禁区 |
| [架构说明](docs/架构说明.md) | 系统结构（队友详解） |
| [中期演示运行卡](docs/中期演示运行卡.md) | 答辩演示操作 |
| [当前交接](docs/当前交接.md) | 最新状态与下一项 |
| [workflow](docs/workflow.md) | 启动 / 测试 / 禁区（一页） |
| [engineering](docs/engineering.md) | 现行组件边界摘要 |
| [validation](docs/validation.md) | 验收分层摘要 |
| [implementation-plan](docs/implementation-plan.md) | 施工 stub（中期已收口） |
| [evaluation-results](docs/evaluation-results.md) | 当前数字 stub |
| [docs/archive/](docs/archive/README.md) | 历史长文与 UI-trial 说明 |
| [中期答辩材料](中期答辩材料/README.md) | 队友材料包 |

## 当前现状（三行）

1. 产品骨架可用；正式演示库 cn_v2 **4 / 27 / 2,501**；中期 PPT **中期汇报-v5** 与彩排 **PASS** 已收口。
2. 生产 PDF 为 PyMuPDF；演示未启用 rerank；答案评价未经独立人工复核。
3. CI 对代码变更跑 Fake 后端 + 前端构建；纯文档变更可跳过（见 `.github/workflows/ci.yml`）。勿提交本机 `.env`。

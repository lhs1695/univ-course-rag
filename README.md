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

研究与工程路线为**开源复用驱动**的应用开发：生产 PDF 使用 **PyMuPDF** 轻量解析 + 页级质量门禁；借鉴 RAGFlow / Kotaemon / Dify 等局部设计，不整体迁移平台。中期不宣称通用 OCR/公式/图表理解或生产多租户。

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

- **前端**：Vue 3 + Vite + Element Plus（Node.js，建议 20+；本仓库常见开发环境为 Node 24）
- **后端**：FastAPI + SQLAlchemy + Alembic（**Python 3.12**，统一用 `backend/.venv`）
- **数据**：PostgreSQL 16 + pgvector（向量维 1024）；本机可用 Docker Desktop
- **解析 / 切分**：PyMuPDF；semantic-text-splitter
- **模型**：SiliconFlow `BAAI/bge-m3`（Embedding）；DeepSeek 文本生成（默认模型 id：`deepseek-flash`）；**pytest 默认 FakeEmbedder / FakeLLM**（无云 Key 也能绿测）

数据流一句话：上传 → 解析切分向量化 → 课内 dense 检索 → 证据约束生成 + 引用 → 前端 `#page=` 回原 PDF。结构详解见 [docs/架构说明.md](docs/架构说明.md)。


## 技术亮点（中期口径）

**教学闭环**：课界权限贯穿检索—生成—原文件；证据不足可拒；引用回原页；三角色与教师问答反馈。

**检索 / 生成**：页级解析与质量门禁；BGE-M3 向量检索 + DeepSeek（`deepseek-flash`）证据约束生成；dense / hybrid / rerank **已实现可开关**——中期主演示 **dense、rerank 关**，对照实验放后期。勿用弱规则数字冒充人工准确率。

详见 [中期答辩材料/答辩提纲.md](中期答辩材料/答辩提纲.md)。

## 三角色能做什么

| 角色 | 能力摘要 |
| --- | --- |
| 学生 | 登录后进入已加入课程；提问；查看引用并打开原资料；浏览课内资料列表 |
| 教师 | 课内资料上传/入库状态；成员管理；问答反馈（高频/依据不足等描述性统计） |
| 管理员 | 全局账号与课程授权；日志留存维护；系统状态（库 / 向量 / 生成配置） |

全局角色 ≠ 自动拥有课内读写权；须课程成员关系。登录为 HTTP-only Cookie Session（非 JWT）。

## 克隆后启动（队友可操作）

以下命令以 Windows PowerShell、仓库根目录为准；与 [workflow](docs/workflow.md)、[中期演示运行卡](docs/中期演示运行卡.md) 对齐。**不要**把 API Key、真实口令或 `.env` 全文写进 README / PPT / 公开群。

### 0. 演示策略与仓库公开计划

- **Key：队友自备**。Real 问答需本机 SiliconFlow + DeepSeek Key（见 `.env.example`）；无 Key 时 Fake 仅能验证 UI。
- **演示可在任意配好环境的机器上跑**：Docker Postgres、`univ_course_rag_cn_v2` 数据、`UPLOAD_DIR`、前后端。点引用打不开时优先查 `UPLOAD_DIR` 与库内路径是否一致。
- **仓库计划公开**：公开前清查未跟踪密钥；**勿提交 `.env`**；改过的演示口令勿写回仓库文件。


### 1. 需要的环境

| 项 | 说明 |
| --- | --- |
| 系统 | Windows（本仓库演示与脚本按此写） |
| Git | 克隆本**私人**仓 |
| Python | **3.12**；在 `backend` 建 `.venv` 并安装依赖 |
| Node.js | 建议 20+；在 `frontend` 执行 `npm ci` / `npm run dev` |
| Docker Desktop | 用于 `docker compose up -d` 起 Postgres + pgvector |
| 可选云 Key | **仅真实演示**需要：SiliconFlow（Embedding）与 DeepSeek（生成）。在本地 `.env` 配置，**参见 `.env.example`，勿提交、勿贴聊天**。无 Key 时保持 `EMBEDDER_BACKEND=fake` / `LLM_BACKEND=fake` 仍可跑通 UI 与 Fake 测试，但回答是假的 |

### 2. 配置 `.env`

```powershell
Copy-Item .env.example .env
# 用编辑器打开 .env，至少确认：
# DATABASE_URL / POSTGRES_DB → univ_course_rag_cn_v2
# UPLOAD_DIR → corpus/local/cn-replace-2026-10-18/rechunk/uploads_v2
# 真实演示时：EMBEDDER_BACKEND=siliconflow、LLM_BACKEND=deepseek，并填写对应 Key（见 .env.example）
# DEEPSEEK_MODEL=deepseek-flash；演示建议 RERANKER_BACKEND=disabled、RETRIEVAL_STRATEGY=dense
```

正式库名是 **`univ_course_rag_cn_v2`**。课件树已在私人仓（约 57MB / 27 PDF）。密钥只放本机 `.env`。

### 3. 安装依赖

```powershell
# 后端（在 backend 目录）
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
cd ..

# 前端
cd frontend
npm ci
cd ..
```

（若仓库已带可用的 `backend/.venv` 与 `frontend/node_modules`，可跳过对应安装。）

### 4. 启动 Postgres

```powershell
docker compose up -d
# 等待 healthy 后，端口默认 5432；默认用户/库见 compose 与 .env.example（univ / univ_course_rag_cn_v2）
```

### 5. 迁移与演示账号 seed

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app
cd ..
```

`python -m app` 会按配置 **seed 演示三角色**（只补不存在的账号）。默认用户名在代码里是 `admin` / `teacher` / `student`；默认口令见 `backend/app/config.py` 的 `seed_*_password`（形如 `change-me-*`）。**口令不要写进 PPT 或公开渠道**；若负责人改过本机口令，以私聊为准。

> 注意：seed **不会**自动重建四课 27 份 PDF 的向量库。完整「点引用开 PDF」需要库内已有 cn_v2 数据，且本机 `UPLOAD_DIR` 能对上文件。负责人本机 DB 里 `storage_path` 可能是绝对路径；队友机器若路径对不上，需协调导出/重入库或校正路径（见下方常见坑）。

### 6. 启动后端与前端

```powershell
# 仓库根：后端（监听 8000）
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# 另开一个终端：前端
cd frontend
npm run dev
```

浏览器打开 Vite 地址（一般为 `http://127.0.0.1:5173`）再登录。**不要**直连 `:8000` 做登录页。可检查：

- `http://127.0.0.1:8000/health` — 进程存活
- `http://127.0.0.1:8000/ready` — 数据库 `SELECT 1`
- `/runtime` — 可见 database / reranking 等配置态（`configured` ≠ 供应商一定连通）

### 7. 固定演示问句（线性代数课）

1. **LA-01（有引用）**：`根据线性代数讲义，线性代数主要研究哪两类对象？`  
   预期：有回答与引用卡片；**点引用**打开原 PDF，URL 含 `#page=`。截图/演示时务必等 PDF 正文渲染出来再截，避免截到深色空壳。
2. **LA-R（拒答）**：`根据线性代数讲义，如何用 SQL 创建数据库表并插入数据？`  
   预期：依据不足 / `NO_EVIDENCE`，不编造 SQL。

完整顺序与故障降级见 [中期演示运行卡](docs/中期演示运行卡.md)。

### 8. 常见坑

| 现象 | 处理方向 |
| --- | --- |
| 点引用 PDF 黑屏 / 打不开 | 查 `UPLOAD_DIR` 是否指向 `.../uploads_v2`；库内路径若是别人机器的绝对路径，本机文件对不上；等预览加载完成再截图 |
| 回答很假或 Embedding 报错 | 分清 **Fake vs Real**：`.env.example` 默认 Fake；真实演示须 SiliconFlow + DeepSeek Key（只写在 `.env`） |
| 连错库 / 课不对 | 确认库名 `univ_course_rag_cn_v2`，不要用已删除的旧默认库或历史隔离库 |
| 登录页异常 | 必须走 Vite 端口，勿直连后端 |
| 8000 / 5173 / 5432 占用 | 结束旧 uvicorn / Vite / 旧容器后再启；`docker compose ps` 看 Postgres |
| 误开 rerank / hybrid | 中期演示口径是 **dense + rerank 关闭**；勿临场改检索当主结论 |
| 端口或依赖版本不对 | 后端固定 Python 3.12 + `backend/.venv`；前端用仓库内 `package.json` / lockfile |

逐步验收与汇报口径以运行卡为准；系统结构见 [架构说明](docs/架构说明.md)。

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

1. 产品骨架可用；正式演示库 cn_v2 **4 / 27 / 2,501**；中期材料含双叙事亮点提纲 + 参考稿 PPT；彩排 **PASS**。
2. 生产 PDF 为 PyMuPDF；演示默认 dense、rerank 关；答案评价未经独立人工复核。
3. CI 对代码变更跑 Fake 后端 + 前端构建；纯文档变更可跳过。仓库计划公开——**勿提交本机 `.env` / Key**；队友 Real 演示自备 Key。

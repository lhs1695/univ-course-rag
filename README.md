# 基于大模型与 RAG 的高校课程知识库智能问答系统

面向高校课程的**有依据、可核对**知识库问答系统：以教师提供的课内资料为主要依据，经检索增强生成（RAG）给出回答与引用，学生可回到原 PDF / 课件页核对；教师可管理资料并查看课内问答反馈；管理员负责课程、成员与权限。

高校课程资料分散于讲义、课件与参考文档，通用大模型回答流畅却未必对应当前课程口径，也难核验出处。本仓库实现本机可运行的应用原型，强调**课程级访问隔离**、资料生命周期治理与证据约束生成。

## 许可与课件说明

- **自有代码与文档**：见根目录 [`LICENSE`](LICENSE)（MIT）。该许可证**不**覆盖第三方课件版权。
- **课内 PDF / corpus**：见 [`NOTICE`](NOTICE)。仓库内课件按公开分享教学资料收录，供演示与复现；**MIT 仅覆盖自有代码/文档**，不覆盖课件本身。

## 三角色能做什么

| 角色 | 能力摘要 |
| --- | --- |
| 学生 | 登录后进入已加入课程；提问并查看引用；页内预览课内已启用资料（PDF / PPTX / DOCX 等）；个人主页 |
| 教师 | 课内资料上传、文件夹整理、处理状态查看；问答反馈汇总；个人主页 |
| 管理员 | 全局账号与课程授权；资料**启用检索**；学院等业务配置；系统状态 |

全局角色 ≠ 自动拥有课内读写权；须课程成员关系。登录为 HTTP-only Cookie Session（非 JWT）。

## 主要能力

1. **多格式资料治理与可追溯索引** — 支持 PDF、PPTX、DOCX、Markdown、纯文本等上传、解析、切分与索引；保留来源元数据，建立从原文件到检索片段及引用位置的链路。
2. **课程约束下的检索** — 在课程授权范围内做向量检索（Dense），并可开关关键词混合（Hybrid）与可选重排（Rerank）。默认演示为 **dense、rerank 关闭**。
3. **证据约束生成与引用核验** — 回答绑定检索证据；依据不足时可拒答，不编造课外内容；前端支持引用摘录与原文件页定位。
4. **多角色权限与资料生命周期** — 学生 / 教师 / 管理员职责分离；围绕上传、启用、替换、删除与重新索引保持业务记录、原文件、切片与向量状态一致。
5. **教师侧基础反馈** — 教师可查看课内问答统计与资料处理状态，作为备课参考入口（不宣称个人掌握度或成绩分析）。

## 技术栈

| 层 | 选型 |
| --- | --- |
| 前端 | Vue 3 + Vite + Element Plus（建议 Node 20+） |
| 后端 | FastAPI + SQLAlchemy + Alembic（**Python 3.12**，`backend/.venv`） |
| 数据 | PostgreSQL 16 + pgvector（向量维 1024） |
| 解析 / 切分 | PyMuPDF；semantic-text-splitter |
| 模型 | SiliconFlow `BAAI/bge-m3`（Embedding）；DeepSeek 文本生成（默认 `deepseek-flash`）；测试可用 FakeEmbedder / FakeLLM |

数据流：上传 → 解析切分向量化 → 课内 dense 检索（可选 hybrid / rerank）→ 证据约束生成 + 引用 → 前端页内预览 / `#page=` 回原文件。结构详解见 [`docs/架构说明.md`](docs/架构说明.md)。

## 当前演示概览

本机正式演示库名：`univ_course_rag_cn_v2`。

| 项 | 说明 |
| --- | --- |
| 课程（4 门） | **机器学习**、**智能移动机器人**、线性代数、教育学原理 |
| 资料 | 课内已启用 PDF / 课件可入库检索；教育学等部分资料支持页内打开 |
| 检索默认 | dense；rerank 未启用 |
| 前端 | Vite `http://127.0.0.1:5173`；API `:8000` |

演示账号由 seed 补齐（用户名一般为 `admin` / `teacher` / `student`）；默认口令见本机 `backend/app/config.py` 的 `seed_*_password`，**勿写入公开材料**。学生展示名可为 `lhs`（账号仍为 `student`）。

已知边界：部分扫描/复杂版式 PDF 可能出现页面文字提取不完整，影响问答依据；过泛的问题仍可能「依据不足」。不得宣称生产可用或单一「准确率」。

## 克隆后启动

以下命令以 Windows PowerShell、仓库根目录为准；细节与禁区见 [`docs/workflow.md`](docs/workflow.md)。**勿将密钥写入仓库或公开渠道**。

### 1. 环境

| 项 | 说明 |
| --- | --- |
| 系统 | Windows（本仓库演示脚本按此写） |
| Python | **3.12**；在 `backend` 建 `.venv` |
| Node.js | 建议 20+；在 `frontend` 执行 `npm ci` |
| Docker Desktop | `docker compose up -d` 起 Postgres + pgvector |
| 云 Key | 真实问答需 SiliconFlow + DeepSeek（见 `.env.example`）；无 Key 时 Fake 仅能验证 UI |

### 2. 配置 `.env`

```powershell
Copy-Item .env.example .env
# 编辑 .env，至少确认：
# DATABASE_URL / POSTGRES_DB → univ_course_rag_cn_v2
# UPLOAD_DIR 指向本机课件目录（与库内路径一致）
# 真实演示：EMBEDDER_BACKEND=siliconflow、LLM_BACKEND=deepseek，并填写 Key
# 建议 RERANKER_BACKEND=disabled、RETRIEVAL_STRATEGY=dense
```

### 3. 安装依赖

```powershell
cd backend
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -U pip
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
cd ..

cd frontend
npm ci
cd ..
```

（若本机已有可用的 `backend/.venv` 与 `frontend/node_modules`，可跳过。）

### 4. 启动 Postgres、迁移与 seed

```powershell
docker compose up -d

cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app
cd ..
```

`python -m app` 会按配置 **seed 演示三角色**（只补不存在的账号）。账号 seed **不等于**向量库已就绪；完整「点引用开资料」需要库内已有课资料，且 `UPLOAD_DIR` 与库内路径一致。

### 5. 启动后端与前端

```powershell
# 仓库根：后端（8000）
backend\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# 另开终端：前端
cd frontend
npm run dev
```

浏览器打开 Vite 地址（一般为 `http://127.0.0.1:5173`）再登录。**不要**直连 `:8000` 做登录页。

可检查：`/health`、`/ready`、`/runtime`。

### 6. 示例问句

1. **线性代数（有引用）**：`根据线性代数讲义，线性代数主要研究哪两类对象？`
2. **拒答**：`根据线性代数讲义，如何用 SQL 创建数据库表并插入数据？` → 预期依据不足，不编造 SQL。
3. **机器学习 / 智能移动机器人**：问课件中的具体概念（如线性模型、过拟合、绪论要点）；过泛的词可能依据不足。

### 7. 故障排查

| 现象 | 处理方向 |
| --- | --- |
| 点引用 / 资料打不开 | 查 `UPLOAD_DIR` 与库内路径是否一致 |
| 回答很假或 Embedding 报错 | 分清 Fake vs Real；真实演示须本机 Key |
| 连错库 / 课不对 | 确认库名 `univ_course_rag_cn_v2` |
| 登录页异常 | 必须走 Vite 端口 |
| 端口占用 | 结束旧进程 / 容器后再启 |

## 文档入口

- 开发硬规则：[`AGENTS.md`](AGENTS.md)
- 文档地图：[`docs/INDEX.md`](docs/INDEX.md)
- 启动与禁区：[`docs/workflow.md`](docs/workflow.md)
- 架构：[`docs/架构说明.md`](docs/架构说明.md)

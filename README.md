# 基于大模型与 RAG 的高校课程知识库智能问答系统

面向高校课程的**有依据、可核对**知识库问答与教学反馈系统：以教师提供的课内资料为主要依据，经检索增强生成（RAG）给出回答与引用，学生可回到原 PDF 页核对；教师可查看问答反馈与资料处理状态；管理员负责课程、成员与权限。

高校课程资料分散于讲义、课件与参考文档，通用大模型回答流畅却未必对应当前课程口径，也难核验出处。本仓库实现本机可运行的应用原型（Python/FastAPI、Vue 3、PostgreSQL/pgvector），强调**课程级访问隔离**、资料生命周期治理、证据约束生成与分层效果评测，目标形成「资料建设 → 证据问答 → 教师核查 → 持续改进」的闭环。

## 许可与课件说明

- **自有代码与文档**：见根目录 [`LICENSE`](LICENSE)（MIT）。该许可证**不**覆盖第三方课件版权。
- **课内 PDF / corpus**：见 [`NOTICE`](NOTICE)。`uploads_v2` 按公开分享教学资料收录，供演示与复现；**MIT 仅覆盖自有代码/文档**，不覆盖课件本身。

## 主要能力

1. **多格式资料治理与可追溯索引**  
   支持 PDF、PPTX、DOCX、Markdown、纯文本等上传、解析、切分与索引；保留来源元数据，建立从原文件到检索片段及引用位置的链路。当前真实演示基线以 PDF 为主；扫描页 / 图内文字 / 公式等增强按代表样本评估，不以「已支持通用 OCR」对外宣称。

2. **课程约束下的检索与证据筛选**  
   在课程授权范围内做向量检索（Dense），并实现可开关的关键词混合（Hybrid）与可选重排（Rerank）。以固定题集分别看召回、答案要点、引用支持、页定位、耗时与调用成本，再决定策略；默认演示为 **dense、rerank 关闭**。

3. **证据约束生成与引用核验**  
   回答绑定检索证据与来源信息；依据不足时可拒答（如 `NO_EVIDENCE`），不编造课外内容。前端支持引用摘录与原 PDF `#page=` 定位，形成「问题 → 课程证据 → 回答 → 原页」可核对路径。

4. **多角色权限与资料生命周期**  
   学生 / 教师 / 管理员职责分离；课程成员关系贯穿资料列表、检索、问答、引用与原文件访问。围绕上传、失败重试、替换、删除与重新索引，保持业务记录、原文件、切片与向量状态一致（结题阶段继续加强回归）。

5. **教师侧基础反馈（学情分析方向）**  
   教师可查看课内问答统计与资料处理状态，并可发起**课程调查**（任务化回看，Fake/Replay 验流程）；保留实验性相似问句分组 API。完整「主题确认 → 处理记录 → 代表题回归」与独立标注评价仍有缺口，当前不宣称个人掌握度、成绩分析或结题通过。

6. **可诊断运行与可复现评测**  
   健康检查、运行配置态、FakeEmbedder / FakeLLM（无云 Key 可跑通 UI 与测试）。真实模型对照与分层核验结果登记在 [`docs/evaluation-results.md`](docs/evaluation-results.md)。流式输出与标准化并发基线为后续工程项。

**项目特色（技术侧）**：把课程证据、权限治理、人机协同反馈与分层评测放在同一套工程骨架里，而不是只堆聊天框；技术方案用固定题集、失败样本与可复现测试支撑取舍。

## 技术栈

| 层 | 选型 |
| --- | --- |
| 前端 | Vue 3 + Vite + Element Plus（建议 Node 20+） |
| 后端 | FastAPI + SQLAlchemy + Alembic（**Python 3.12**，`backend/.venv`） |
| 数据 | PostgreSQL 16 + pgvector（向量维 1024） |
| 解析 / 切分 | PyMuPDF；semantic-text-splitter |
| 模型 | SiliconFlow `BAAI/bge-m3`（Embedding）；DeepSeek 文本生成（默认 `deepseek-flash`）；pytest 默认 FakeEmbedder / FakeLLM |

数据流：上传 → 解析切分向量化 → 课内 dense 检索（可选 hybrid / rerank）→ 证据约束生成 + 引用 → 前端 `#page=` 回原 PDF。结构详解见 [`docs/架构说明.md`](docs/架构说明.md)。

相对早期设想中的 MySQL / Chroma·Milvus / LlamaIndex 等组合，现行实现收敛为 **PostgreSQL + pgvector** 与模块化检索链路，便于本机演示、权限一体与对照实验。

## 开源设计借鉴

公开设计调研（非整体迁移平台）：

- [RAGFlow](https://github.com/infiniflow/ragflow)：文档解析、处理状态与质量治理思路  
- [Kotaemon](https://github.com/Cinnamon/kotaemon)：文档问答中的证据展示与引用核对  
- Moodle Learning Analytics / Jisc 学习分析规范：教学反馈「指标—洞察—行动」与人工监督口径  
- [Arize Phoenix](https://github.com/Arize-ai/phoenix)：追踪与实验评测理念  

复用前会核对版本、许可证、传递依赖与集成成本；优先薄适配、小改现有骨架。

## 当前演示基线

| 项 | 值 |
| --- | --- |
| 正式库 | `univ_course_rag_cn_v2` |
| Alembic | **0015 (head)**（含 Agent / 业务表；中期冻结口述曾为 0011） |
| 规模 | **4 门课 / 27 份 PDF / 2,501 chunks** |
| 课程 | 线性代数、概率论与统计学、人力资源管理、教育学原理 |
| 课件路径 | `corpus/local/cn-replace-2026-10-18/rechunk/uploads_v2/`（约 57MB / 27 PDF） |
| 检索 | dense；**rerank 未启用** |
| 弱规则冒烟 | 可答题预期文档/页 12/12，拒答 4/4（**≠ 人工事实正确率**） |

另有 **22 题**真实模型 Dense / Hybrid 小样本对照（**开发者核验，非独立评测**）。分层指标示例（详见评测登记）：

| 评价指标 | Dense | Hybrid |
| --- | ---: | ---: |
| 全部应答题中的事实要点通过率（17 题为分母） | 15/17 | 16/17 |
| 已回答应答题中的引用支持通过率 | 16/16 | 16/16 |
| 严格预期页命中 | 12/16 | 12/16 |
| 明显课外问题的正确拒答 | 5/5 | 5/5 |

**口径**：严格预期页命中 ≠ 引用错误率；**不得宣称 Hybrid 整体显著优于 Dense**；勿合成单一「准确率」。完整说明见 [`docs/evaluation-results.md`](docs/evaluation-results.md)。

已知限制（诚实边界）：部分资料仍有 `COVERAGE_INCOMPLETE` 级覆盖警告；Hybrid 关键词独有候选的证据准入仍在校准；引用支持与严格页命中存在口径差；个别应答题仍可能依据不足。详情与后续计划见报告修订稿与 `docs/`。

结题主线（Agent M1–M3、业务 M4、最小 Trace）已在本机落地并有开发者观察证据；**默认不 push**；空白机部署与备份恢复**暂缓**；**不得宣告结题通过**。细节见 [`docs/当前交接.md`](docs/当前交接.md)。

## 三角色能做什么

| 角色 | 能力摘要 |
| --- | --- |
| 学生 | 登录后进入已加入课程；提问；查看引用并打开原资料；浏览课内已启用资料；个人主页（无提问历史） |
| 教师 | 课内资料上传/入库状态；成员/班级名单；问答反馈；**课程调查**（Fake/Replay 流程验收，非真模型质量声明） |
| 管理员 | 全局账号与课程授权；**业务**（学期/班级/名单）；资料**启用检索**；日志留存；系统状态 |

全局角色 ≠ 自动拥有课内读写权；须课程成员关系。登录为 HTTP-only Cookie Session（非 JWT）。

## 克隆后启动

以下命令以 Windows PowerShell、仓库根目录为准；与 [`docs/workflow.md`](docs/workflow.md) 对齐。**勿将密钥写入仓库或公开渠道**。

### 0. 仓库与密钥

- **Key：本机自备**。真实问答需 SiliconFlow + DeepSeek Key（见 `.env.example`）；无 Key 时 Fake 仅能验证 UI。
- **可在任意配好环境的机器上跑**：Docker Postgres、`univ_course_rag_cn_v2` 数据、`UPLOAD_DIR`、前后端。点引用打不开时优先查 `UPLOAD_DIR` 与库内路径是否一致。
- **仓库已公开**：勿将 `.env` / Key 写入仓库；课件说明见 [`NOTICE`](NOTICE)。

### 1. 需要的环境

| 项 | 说明 |
| --- | --- |
| 系统 | Windows（本仓库演示与脚本按此写） |
| Git | 克隆本仓库 |
| Python | **3.12**；在 `backend` 建 `.venv` 并安装依赖 |
| Node.js | 建议 20+；在 `frontend` 执行 `npm ci` / `npm run dev` |
| Docker Desktop | `docker compose up -d` 起 Postgres + pgvector |
| 可选云 Key | 仅真实演示需要；只写本地 `.env` |

### 2. 配置 `.env`

```powershell
Copy-Item .env.example .env
# 用编辑器打开 .env，至少确认：
# DATABASE_URL / POSTGRES_DB → univ_course_rag_cn_v2
# UPLOAD_DIR → corpus/local/cn-replace-2026-10-18/rechunk/uploads_v2
# 真实演示时：EMBEDDER_BACKEND=siliconflow、LLM_BACKEND=deepseek，并填写对应 Key
# DEEPSEEK_MODEL=deepseek-flash；建议 RERANKER_BACKEND=disabled、RETRIEVAL_STRATEGY=dense
```

正式库名是 **`univ_course_rag_cn_v2`**。课件树已纳入仓库（约 57MB / 27 PDF）。

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

（若仓库已带可用的 `backend/.venv` 与 `frontend/node_modules`，可跳过对应安装。）

### 4. 启动 Postgres

```powershell
docker compose up -d
```

### 5. 迁移与演示账号 seed

```powershell
cd backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m app
cd ..
```

`python -m app` 会按配置 **seed 演示三角色**（只补不存在的账号）。默认用户名在代码里是 `admin` / `teacher` / `student`；默认口令见 `backend/app/config.py` 的 `seed_*_password`。**口令不要写进公开材料**；若本机改过口令，以本机实际配置为准。

> 账号 seed **不等于**向量库。完整「点引用开 PDF」需要库内已有 cn_v2 数据，且本机 `UPLOAD_DIR` 与库内路径一致。路径细节见 [`docs/workflow.md`](docs/workflow.md) 与架构说明。

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

### 7. 示例问句（线性代数课）

1. **有引用**：`根据线性代数讲义，线性代数主要研究哪两类对象？`  
   预期：有回答与引用卡片；**点引用**打开原 PDF，URL 含 `#page=`。
2. **拒答**：`根据线性代数讲义，如何用 SQL 创建数据库表并插入数据？`  
   预期：依据不足 / `NO_EVIDENCE`，不编造 SQL。

### 8. 故障排查

| 现象 | 处理方向 |
| --- | --- |
| 点引用 PDF 黑屏 / 打不开 | 查 `UPLOAD_DIR` 是否指向 `.../uploads_v2`，并与库内路径一致 |
| 回答很假或 Embedding 报错 | 分清 Fake vs Real：`.env.example` 默认 Fake；真实演示须本机 Key |
| 连错库 / 课不对 | 确认库名 `univ_course_rag_cn_v2` |
| 登录页异常 | 必须走 Vite 端口，勿直连后端 |
| 8000 / 5173 / 5432 占用 | 结束旧进程 / 容器后再启；`docker compose ps` 看 Postgres |
| 误开 rerank / hybrid | 默认演示口径是 **dense + rerank 关闭**；改策略前先对照评测登记 |
| 端口或依赖版本不对 | 后端 Python 3.12 + `backend/.venv`；前端用仓库 lockfile |

## 文档索引

| 文档 | 用途 |
| --- | --- |
| [AGENTS](AGENTS.md) | 协作纪律与禁区 |
| [架构说明](docs/架构说明.md) | 系统结构详解 |
| [workflow](docs/workflow.md) | 启动 / 测试 / 禁区（一页） |
| [engineering](docs/engineering.md) | 现行组件边界摘要 |
| [validation](docs/validation.md) | 验收分层摘要 |
| [evaluation-results](docs/evaluation-results.md) | 评测登记与结果口径 |
| [implementation-plan](docs/implementation-plan.md) | 当前阶段状态摘要 |
| [docs/archive/](docs/archive/README.md) | 历史长文与归档说明 |

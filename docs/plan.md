# Plan：univ-course-rag 第一期

状态：阶段 0–10 已落地（第一期收敛）  
日期：2026-09-01  
对照：`intent.md`、`decisions/001–004`；失败分类见 `tech-recommendations.md`

**施工纪律：** 整份计划进上下文；一次会话只做下面某一个阶段；阶段结束写交接（做了 / 没做 / 怎么验）；偏离则同一批改动更新本文。禁止把 RAGFlow/Dify/LangChain 当运行时骨架。

---

## 1. 本计划关掉的产品未决（原 intent §6）

| 原问题 | 第一期决定 |
| --- | --- |
| 学生如何进课 | 管理员建用户与课程；教师把学生加入 `course_members`。无邀请码、无自助选课、无学校 CAS |
| 文件格式 | **PDF + Markdown/纯文本**。PPT/PPTX、Word 明确放到第一期之后的下一份 plan |
| 学情 | 教师两张表：高频问句（规范化后计数）、检索未命中/拒答问句。只展示问句内容与次数/时间，**不展示具体学生**（无用户名/`user_id`）。只统计课内学生提问。无知识点标签、无预警措辞 |
| 部署 | 本机 `docker compose` 演示。校园网服务器不在本 plan |
| Embedding | 硅基流动 `BAAI/bge-m3`，1024 维（已见 002） |
| Python 依赖 | 后端虚拟环境；见 [004](decisions/004-venv-corpus-vision.md) |
| 课程资料 | 开发用夹具；真课件可后补（004） |
| 图片/视觉 | 第一期不抽图、不用 vision 模型（004） |

---

## 2. 双方案与取舍（只保留会影响结构的）

| 题目 | 方案 A | 方案 B | **选定** |
| --- | --- | --- | --- |
| 业务库 + 向量 | Postgres + pgvector 一套 | 业务 Postgres + 另装 Qdrant/Chroma | **A**（课程过滤与学情同一事务边界） |
| 登录 | Cookie + `sessions` 表 | JWT 放前端 | **A**（001） |
| 入库异步 | 任务表 + FastAPI `BackgroundTasks` | 第一期就上 Celery/独立 worker 容器 | **A**；单文件解析超过约 60s 再拆 worker（本 plan 不预做） |
| 引用 v1 | prompt 枚举 Source id + 校验 ⊆ 检索集 | 一上来做 RAGFlow 句级 `insert_citations` | **A**；句级回贴列为阶段 5 之后的可选加分，不挡验收 |
| 测试打云 | CI 调硅基流动和 DeepSeek | FakeEmbedder + FakeLLM | **B 为默认 pytest**；可选 `backend/tests/integration` 标 `@pytest.mark.integration`，无 key 则 skip |
| 前端 | Vue 3 SPA 调 API | Jinja 服务端渲染 | **Vue 3 + Vite + Element Plus**（001） |

生成：`deepseek-v4-flash`，默认非 thinking。检索 k=4～8，注入 token 硬顶（实施时写死常数，例如合计约 4k–8k 字符量级，禁止整课灌入）。

---

## 3. 建议目录（实施阶段 0 创建；允许小幅更名，不允许长出第二套框架）

```
AGENTS.md
.env.example
docker-compose.yml          # postgres + pgvector
backend/
  .venv/                    # gitignore；Python 3.12
  pyproject.toml            # 或 requirements.txt + ruff/pytest
  alembic/                  # 从阶段 1 有表开始
  app/main.py
  app/api/
  app/models/
  app/services/
  app/security/
  tests/
  tests/fixtures/           # 阶段 3 起：sample.md、短 PDF、golden.json
frontend/                   # 阶段 6 再建即可
docs/
```

密钥只出现在本机 `.env`，**按阶段需要**：

| 阶段 | 需要的 key |
| --- | --- |
| 0 | 无云 key；`POSTGRES_*`。登录是 Cookie + `sessions` 表，不需要 JWT secret（`.env.example` 里 `SESSION_SECRET` 仅为占位，当前后端未读取） |
| 1–2 | 无云 key |
| 3–4 单测 | 无；真灌库才要 `SILICONFLOW_API_KEY` |
| 5 单测 | FakeLLM；真问答才要 `DEEPSEEK_API_KEY` |

---

## 4. 分阶段（每阶段 = 一次实施会话）

阶段完成的定义：勾选条件里的命令/测试为绿，且未做计划外重构。

### 阶段 0 — 宪法与可跑的空仓

- **做：** 根 `AGENTS.md`（怎么测、禁止密钥进日志、课件当不可信文本、一次会话一阶段、**必须在 `backend/.venv` 里装依赖**）；`.gitignore`（含 `.venv/`、`node_modules/`、`.env`）；`docker-compose.yml`（`pgvector/pgvector` 官方镜像或带 pgvector 的 postgres）；后端最小 FastAPI `/health`；`ruff` + `pytest`；`.env.example`。
- **不做：** 登录、RAG、前端脚手架可以暂缺。
- **改哪些：** 上列根文件 + `backend/app/main.py` + 一个 health 测试。
- **证明：** Python **3.12** 虚拟环境可复述；`docker compose up -d` 后 Postgres 可连；在 venv 内 `pytest backend/tests/test_health.py` 绿；`ruff check` 绿。

### 阶段 1 — 账号、Cookie session、角色

- **做：** Alembic 首迁；用户表（student / teacher / admin）；密码哈希（argon2 或 bcrypt，禁止明文）；仅 admin 创建账号；seed 三个演示用户（用户名进文档，密码只进 `.env.example` 占位）；`POST /auth/login` `POST /auth/logout` `GET /auth/me`；HTTP-only Cookie；未登录 401。
- **不做：** 邮箱验证、验证码、CAS、前端页。
- **证明：** `pytest`：错误密码失败；登录后带 Cookie 访问 `/auth/me`；无 Cookie 401；登出后再访问 401。

### 阶段 2 — 课程与成员隔离

- **做：** `courses`、`course_members`；管理员 CRUD 课程；教师给本课加/删学生；学生列出自己的课。所有后续资源必须先过「是否该课成员」。
- **不做：** 知识库、上传。
- **证明：** 学生 A 成员课 1、非成员课 2；访问课 2 的任意受保护 API → 403。教师不能改他课成员。

### 阶段 3 — 入库（PDF + Markdown）

- **做：** 教师上传；`documents` + `ingest_jobs`（pending/running/succeeded/failed + 错误信息）；解析（PyMuPDF / 文本）；切分（页或标题优先，再长度重叠）；`chunks` 含 `course_id, document_id, page, text, embedding vector(1024)`；Embedder 接口 + SiliconFlow 实现 + FakeEmbedder；失败任务教师能读到原因，无成功切片不出现「幽灵已索引」。
- **不做：** PPT/Word、OCR、问答接口、真 embedding 作为单测必过项。
- **证明：** `backend/tests/fixtures/sample.md`（含一句独一无二的课内原句）上传后 job 成功、chunk 带该课 `course_id`；损坏文件 → job failed 且无 chunk；FakeEmbedder 下 pytest 不访问外网。

### 阶段 4 — 检索契约与黄金题

- **做：** `POST /courses/{id}/search`（或等价）：鉴权 + 该课 WHERE + 向量 top-k；分数过低返回空列表而不是「猜的」。`backend/tests/fixtures/golden.json` 至少 **3** 条（MD + 可解析短 PDF）；断言命中预期 `document_id`/子串。跨课：课 2 有更相似文本时，课 1 的 search 不得返回课 2 的 chunk。阶段 4 前通读 `decisions/003` 的「对我们第一期的含义」即可，不必 clone RAGFlow。
- **不做：** 调用 DeepSeek、前端。
- **证明：** `pytest backend/tests/test_retrieve.py` 绿（FakeEmbedder 下用固定向量构造「能命中」的夹具，或对 fake 做确定性 hash，保证同类文本距离更近——实施时选一种并写进测试注释）。可选 integration：真硅基流动，无 key 则 skip。

### 阶段 5 — 问答生成与引用

- **做：** `POST /courses/{id}/ask`：检索 → 无命中则拒答（明确错误码/文案）仍写 `query_logs`；有命中则拼 Source id 列表调 DeepSeek；校验引用 ⊆ 本次 chunk id；日志含 hit/miss、chunk_ids、耗时，**不含** API key、默认不含完整课件正文。LLM 客户端可注入 FakeLLM。
- **不做：** 多轮 Agent、thinking 默认开、句级自动贴引用（可选后面加）。
- **证明：** FakeLLM 返回非法引用 id → 响应里被丢掉或降级；检索空 → 不调用 LLM（或调用了也不把其当课内事实；优先不调用）；命中时 citations 可对上夹具。禁止改 golden 迁就实现。

### 阶段 6 — 学生端 Vue

- **做：** Vite + Vue 3 + Element Plus；登录页（Cookie 跨域：开发期 Vite proxy 到后端，同源 Cookie）；课程列表；问答页展示答案 + 引用列表（资料名/页）。
- **不做：** 教师上传、管理端、学情。
- **证明：** 浏览器走通：登录 → 选课 → 提问 → 看到引用。无浏览器工具时：至少 Playwright 或手工清单写在交接里；优先用浏览器实点。

### 阶段 7 — 教师端

- **做：** 本课资料列表、上传、job 状态与失败原因、进入学生同款问答（便于核对）。学情入口可先链到空页或「阶段 9」。
- **不做：** 管理员用户管理、把提问原文公示全班。
- **证明：** 上传夹具 → 状态成功；故意坏文件 → 看见失败原因。

### 阶段 8 — 管理员端

- **做：** 用户列表/创建（三角色）、课程创建、把教师或学生绑到课（阶段 2 的 admin 成员 API 接 UI；列表另增 `GET /admin/users`、`GET /admin/courses/{id}/members`）。
- **不做：** 系统监控大盘、多租户。
- **证明：** 管理员创建学生并加入课程后，用该生账号能在阶段 6 看到该课。

### 阶段 9 — 学情两表

- **做：** 基于 `query_logs`：只聚合**课内角色为学生**的提问（教师核对问答不进表）。本课高频问句（命中：简单规范化——去空白、截断——后计数）；未命中/拒答（`NO_EVIDENCE`）单独一张表（规范化问句、次数、最近时间）。学情 API 与教师 UI **不返回学生标识**（无 `user_id`/用户名/名单展开）。日志表可仍存 `user_id` 供库内审计，对外与 stdout 仍避免完整提问。不做「学得差」文案。
- **不做：** 知识点图谱、成绩预测、按学生点名、去重「人数」列（小班易反推）。
- **证明：** pytest 插入若干 log 后聚合计数正确，且响应 JSON 不含 `user_id`/`username`；教师 UI 两表能看见问句与次数、看不见学生列。学生打不开该 API（403）。

### 阶段 10 — 对照收敛

- **做：** 对照 intent 验收清单逐条勾；黄金题 ≥3 且含 MD+PDF；抽掉资料后问答变拒答；串课用例仍绿；更新 `AGENTS.md` 里反复出现的纠正；intent/plan 若已偏则改文档。列出 **不做进本仓的**：PPT/Word、句级引用、独立 worker、CAS。
- **证明：** 本文「阶段 10 核对」一节全部打勾，或显式写缺口与是否开下一份 plan。

---

## 5. 阶段 10 核对（收敛时用）

- [x] 未登录受保护 API 为 401，不是空 200
- [x] 跨课程检索/问答不串库
- [x] 黄金题 MD+PDF 检索命中；删资料后拒答
- [x] 解析失败可见，无幽灵文档
- [x] 学情两表；学生 403；学情 API/UI 无学生标识
- [x] 普通日志无 key、无整份课件
- [x] 无 LangChain/RAGFlow 运行时依赖

---

## 6. 交接模板（每阶段结束贴进下一会话）

```
阶段 N：
做了：
没做：
怎么验（命令）：
下一步只做阶段 N+1，不要提前做阶段 …
```

---

## 7. 明确不在本 plan（不做进本仓）

PPT/Word、扫描件 OCR、视觉模型入库/问答、MinerU、Qwen3-Embedding、句级 `insert_citations`、Celery / 独立 worker、校园部署、邀请码 / CAS、多 Agent、把评测平台当产品。用户改删、系统监控大盘、多租户亦不在第一期。

第一期已收敛。下一份 plan 若要开，从上述清单里单独立项，不要在本仓继续加阶段 11。

下一会话入口：`docs/NEXT-SESSION.md`。

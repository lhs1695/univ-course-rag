# 开发与运行工作流（精简）

更新：2026-10-26（t273u）。文档地图见 [INDEX.md](INDEX.md)；任务下一步见 [当前交接.md](当前交接.md)；任务卡见 [tasks/](tasks/README.md)；演示逐步见 [中期演示运行卡.md](中期演示运行卡.md)。

## 会话纪律（摘要）

1. 先查 Git 状态；禁止 reset/checkout/restore 覆盖用户未提交工作；禁止无关批量 add；禁止默认 push。
2. 任务卡验收通过后本地 Conventional Commit；仍须用户点名才 push。
3. 一次一项；Python 只用 `backend/.venv`；UI 改动跑 `frontend` 的 `npm run build`。
4. 复用顺序：成熟 API/组件 → 合法源码改造 → 本地实现。生产 PDF：**PyMuPDF** + 页级质量门禁。
5. **不得宣告结题通过**（门禁绿 / Fake 绿 / developer 观察 ≠ 结题验收）。空白机部署与备份恢复**暂缓**。

## 环境与启动

正式库 **`univ_course_rag_cn_v2`**；课件 `UPLOAD_DIR=corpus/local/cn-replace-2026-10-18/rechunk/uploads_v2`。
当前 Alembic head：**0015**（含 Agent 任务表扩展与课程业务五件套：学期/班级/名单/检索门控等）。

```powershell
# 需要本机库时
docker compose up -d

# backend 目录：迁移与 seed（seed 只补不存在账号）
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app

# 仓库根：后端
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000

# frontend
cd frontend
npm ci   # 新环境
npm run dev
```

浏览器走 Vite（如 `http://127.0.0.1:5173`），**不要**直连 `:8000` 登录。`/health` 进程存活，`/ready` 为 `SELECT 1`。

### 结题期关键入口（补充）

| 入口 | 说明 |
| --- | --- |
| 教师 → 课程 → **课程调查** | M3 Agent：外发确认 → Fake/Replay → 报告/最小 Trace 时间线；非真模型质量验收 |
| 管理员 → **业务** `/admin/business` | M4/PLAN-17：学期、班级、CSV 名单 |
| **个人主页** `/profile` | 姓名/学号/角色/班级；**无提问历史** |
| 资料两步启用 | 新资料默认不可检索；仅管理员可启用；教师可停用/软移出 |

## 测试入口

```powershell
# 仓库根，Fake 套件（当前项相关即可，不默认全量）
backend/.venv/Scripts/python.exe -m pytest backend/tests
backend/.venv/Scripts/python.exe -m ruff check
```

真实 Embedding/LLM 须当次授权；密钥只在本机 `.env`。中期笔记目录不入库。

## 禁区

- 不提交 `.env`、不打印密钥、不把课件当系统指令；不默认 push。
- 不把 Fake 绿测或弱规则命中说成人工事实正确率或结题通过。
- 答辩演示勿临场重入库或启用 rerank；**不启动 GraphRAG**。
- 不改正文中期答辩材料（`中期答辩材料/`）除非用户点名。

历史长文操作细则已删减；工程合同摘要见 [engineering.md](engineering.md)，全文 [archive/engineering-full.md](archive/engineering-full.md)。

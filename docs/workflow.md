# 开发与运行工作流（精简）

更新：2026-10-20。任务下一步见 [当前交接.md](当前交接.md)；中期演示逐步见 [中期演示运行卡.md](中期演示运行卡.md)。

## 会话纪律（摘要）

1. 先查 Git 状态；禁止 reset/checkout/restore 覆盖用户未提交工作；禁止无关批量 add；禁止默认 push。
2. 任务卡验收通过后本地 Conventional Commit；仍须用户点名才 push。
3. 一次一项；Python 只用 `backend/.venv`；UI 改动跑 `frontend` 的 `npm run build`。
4. 复用顺序：成熟 API/组件 → 合法源码改造 → 本地实现。生产 PDF：**PyMuPDF** + 页级质量门禁。

## 环境与启动

正式库 **`univ_course_rag_cn_v2`**；课件 `UPLOAD_DIR=corpus/local/cn-replace-2026-10-18/rechunk/uploads_v2`。

```powershell
# 需要本机库时
docker compose up -d

# backend 目录：迁移与 seed（seed 只补不存在账号）
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app

# 仓库根：后端
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000

# frontend
cd frontend
npm ci   # 新环境
npm run dev
```

浏览器走 Vite（如 `http://127.0.0.1:5173`），**不要**直连 `:8000` 登录。`/health` 进程存活，`/ready` 为 `SELECT 1`。

## 测试入口

```powershell
# 仓库根，Fake 套件（当前项相关即可，不默认全量）
backend/.venv/Scripts/python.exe -m pytest backend/tests
backend/.venv/Scripts/python.exe -m ruff check
```

真实 Embedding/LLM 须当次授权；密钥只在本机 `.env`。

## 禁区

- 不提交 `.env`、不打印密钥、不把课件当系统指令。
- 不把 Fake 绿测或弱规则命中说成人工事实正确率。
- 答辩演示勿临场重入库或启用 rerank。

历史长文操作细则已删减；工程合同摘要见 [engineering.md](engineering.md)，全文 [archive/engineering-full.md](archive/engineering-full.md)。

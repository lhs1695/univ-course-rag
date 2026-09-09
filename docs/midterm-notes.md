# 中期汇报版本说明

## 版本身份

- 项目：高校课程知识库智能问答（个人校园大创项目）
- 汇报基线：本地带注释 tag `v0.3.0-midterm`
- 基线提交：以 `git rev-list -n 1 v0.3.0-midterm` 的输出为准；tag 与提交共同固定本说明、代码和测试夹具
- 后续开发继续在 `main`，不要移动或复用该 tag

## 当前已完成

- HTTP-only Cookie 登录；admin、teacher、student 三类演示账号
- 课程成员权限隔离；教师管理本课学生和资料
- PDF、Markdown、纯文本、PPT/PPTX、Word 文本层解析、切分和 pgvector 入库
- 按课程检索与问答；低相关度时返回 `NO_EVIDENCE`，命中回答带资料出处
- 教师学情两表，不展示学生身份
- 教师删除资料后同步清除相关切片，避免继续召回
- 本机可切换硅基流动 BGE-M3 向量与 DeepSeek 生成；pytest 仍使用 Fake 实现

## 本机启动

1. 启动并准备数据库（从仓库根目录开始）：

   ```powershell
   docker compose up -d
   cd backend
   .\.venv\Scripts\Activate.ps1
   alembic upgrade head
   python -m app
   cd ..
   ```

2. 启动后端：

   ```powershell
   python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
   ```

3. 另开终端启动前端：

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

4. 使用 Vite 输出的地址访问，不要直接在后端端口登录，否则 Cookie 不同源。

## Fake 与真模型

- 开发和 pytest 默认 FakeEmbedder/FakeLLM，不需要云 key，也不会靠真实 API 通过测试。
- 中期演示如需真模型，只在本机 `.env` 设置 `EMBEDDER_BACKEND=siliconflow`、`LLM_BACKEND=deepseek` 并填写对应 key，然后重启 uvicorn。
- 切换 Embedder 后必须从原文件重新入库；Fake 与硅基流动向量不能混用，旧切片不会自动重算。
- `.env`、key 正文、真实课件和上传数据不得提交、截图或写进普通日志。

## 发布门禁（2026-09-09）

- 后端指定回归：`33 passed, 1 skipped`；跳过项是无 key 时不运行的可选硅基流动集成测试
- Ruff：通过
- 前端 `npm run build`：通过，1631 个模块完成转换
- 前端构建提示主 JS 包约 1.05 MB，当前不阻断中期版本；后续只有在真实加载速度成为问题时再做路由懒加载或拆包
- 阶段 17 已在后续开发提交用 MIT OCW 文本型 PDF/PPTX 跑通真实浏览器流程；本 tag 仍保留创建当时的代码与说明，不移动标签

## 汇报前准备

- 使用可抽取文本的 PDF/PPT/PPTX/Word；扫描件和纯截图页不保证有文本
- 真课件放 `corpus/local/`，演示前确认未被 Git 跟踪
- 如使用真模型，由维护者自行填写本机 `.env` 并重启后端；不要在聊天或汇报材料中展示 key
- 按阶段 17 的走位文档完成一次教师上传、学生问答、教师学情、删除资料后拒答的浏览器检查

## 已知限制与非目标

- 当前不做 OCR/vision，扫描件可能解析不到内容
- 删除依据后生成层能无引用拒答；但低检索阈值可能让剩余泛化片段仍记为 `hit=True`，教师“未命中 / 拒答”表暂不统计这类生成层拒答
- 当前无 CAS、多租户、Celery、知识图谱、成绩预测、小程序或独立 worker
- 阶段 18 的失败原因中文化、阶段 19 的管理员改密/停用均需真实试用触发，默认不做
- 本版本面向本机中期检查，不宣称已完成校园网生产部署

## 恢复汇报版本

先保存当前未提交工作，再以只读方式检出：

```powershell
git status --short
git switch --detach v0.3.0-midterm
```

汇报后返回开发分支：

```powershell
git switch main
```

tag 默认只保存在本机；如需异地备份，须由维护者明确决定后再推送提交与 tag。

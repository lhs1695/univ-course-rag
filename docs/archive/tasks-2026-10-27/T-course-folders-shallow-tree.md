# TASK: 课内浅树资料夹（CourseFolder）

| 项 | 值 |
| --- | --- |
| 对应 PLAN | 无（结题演示增强；用户 t276–t279 拍板） |
| 状态 | implemented；待 bot 验收（完整构建 / UI 点验受环境限制，见完成记录） |
| 须授权 | 无（本卡只实现 schema/API/UI/测试；真实入库另批） |

## 目标

- 课内资料支持**浅树文件夹实体**（最多 1～2 层：根夹 + 可选一层子夹）。
- 教师：建夹 / 改名 / 删除空夹 / 移动资料到夹 / 上传时选目标夹。
- 学生：只读同树；未分组资料 `folder_id=null` 展示为「未分组」。
- 检索**默认仍整课**；不按夹限检索（后置）。
- 管理员资料启用页能看到夹名（分组展示即可，不强制管理夹）。

## 非目标（禁止顺手做）

- 调查 Agent 重设计、GraphRAG/KG、按夹检索/ACL、无限嵌套、拖拽排序、空白机。
- 不改中期答辩材料/ 正文；不 push；不读 `.env`。
- 不重写整站视觉；沿用现有 token / DocumentsView / StudentDocuments 风格。
- 不改上传 100MB 门禁（已在上一 commit 完成）。

## 验收标准（可判定真假）

- [x] Alembic **0016**（父 **0015**）：`course_folders` 表 + `documents.folder_id` 可空 FK；upgrade/downgrade 有隔离 SQLite 测 + PG offline DDL 测（仿 0015）。
- [x] API：课内文件夹 CRUD；上传 `folder_id` 可选；PATCH 可改 `folder_id`（移动）；DocumentOut 含 `folder_id` / `folder_name`（或等价路径字段）。
- [x] 深度校验：创建第 3 层 → 4xx；删除非空夹 → 409（含子夹、停用资料）。PATCH 仅改名，不支持换父级。
- [x] 权限：本课教师/管理员可写夹；学生只读列表；跨课 404/403。
- [ ] 前端：教师 DocumentsView 可建夹、选夹上传、列表按夹分组；StudentDocuments 按夹分组只读；AdminDocumentsView 至少显示夹名。（代码与组件编译已完成，待浏览器点验。）
- [x] 命令：`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_course_folders.py backend/tests/test_course_folders_migration.py -q -p no:cacheprovider --tb=short` 通过
- [x] `backend/.venv/Scripts/python.exe -m ruff check <本卡改动 py> --output-format concise`
- [ ] `cd frontend; npm run build` 通过；相关 Node 测若有则跑。

## 约束

- 栈：现有 FastAPI + SQLAlchemy + Alembic + Vue3 + Element Plus；无新依赖、无第二套 RAG。
- FK：`course_folders.course_id` → courses CASCADE；`parent_id` 自引用；`documents.folder_id` ON DELETE **SET NULL**（删夹不删资料，资料回未分组）——若选「拒删非空」则可不依赖 SET NULL，但仍建议 SET NULL 兜底。
- 同课同父下夹名唯一（注意 parent_id NULL 在 PG/SQLite 的唯一性处理）。
- 物理存储路径**不必**按夹改目录；夹只是组织元数据。
- 迁移不得连接演示库/默认 DATABASE_URL；只用 sqlite 内存与 offline DDL（同 0015）。

## 禁止改动的路径

- `.env`、密钥
- `中期答辩材料/` 正文
- 调查 Agent 主路径合同（`agent_*` runner/API 合同）
- 用户未点名的 `corpus/local` 大目录内容（本卡不复制课件）

## 相关上下文（指针）

- 模型：`backend/app/models/document.py`、`backend/app/models/course.py`、`backend/app/models/__init__.py`
- API：`backend/app/api/documents.py`、`backend/app/api/schemas.py`；可新建 `backend/app/api/folders.py` 并挂到 main
- 前端：`frontend/src/views/DocumentsView.vue`、`frontend/src/components/StudentDocuments.vue`、`frontend/src/views/AdminDocumentsView.vue`
- 迁移范例：`backend/alembic/versions/0015_course_business.py`、`backend/tests/test_course_business_migration.py`
- 业务权限范例：`backend/tests/test_course_business.py`

## 建议 API 草图（可微调命名，保持 REST 风格一致）

- `GET/POST /courses/{course_id}/folders`
- `PATCH/DELETE /courses/{course_id}/folders/{folder_id}`
- Upload form 增加可选 `folder_id`
- `DocumentUpdateRequest` 增加可选 `folder_id: UUID | null`（与 `retrieval_enabled` 可并存；注意管理员启用检索权限不变）
- 列表仍 `GET .../documents`，响应带 folder 字段；可选 `GET .../folders` 返回树或扁平+parent_id

## 验证步骤（Agent 必须贴原始输出）

1. 上述 pytest
2. ruff
3. frontend build
4. 简述 UI 改动点（建夹/选夹/分组）

## 完成记录

- 提交：（由 bot 验收后提交）
- 实现日期：2026-10-27；未 commit、未 push，未读取 `.env`、未连接演示库、未执行真实迁移或调用真实模型。
- 复用：现有 SQLAlchemy / Alembic batch 迁移、FastAPI 课程资料授权、Element Plus 控件；无新依赖、未改检索范围或上传大小限制。
- UI：根夹 / 子夹创建、同级改名、删除空夹；上传目标选择；逐条移动资料（可移回「未分组」）；教师与学生按根夹 / 子夹路径分组；管理员显示夹名列。
- 约束：根夹与子夹各用 partial unique index 覆盖同课同父名称唯一；文件夹删除与挂资料通过行锁协调；移动 PATCH 仅更新显式字段，保留管理员启用检索门禁及原上传授权。
- 验证命令与原始摘要：

```text
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_course_folders.py backend/tests/test_course_folders_migration.py -q -p no:cacheprovider --tb=short
................                                                         [100%]
16 passed, 1 warning in 17.10s

backend/.venv/Scripts/python.exe -m ruff check backend/app/models/course_folder.py backend/app/models/document.py backend/app/models/__init__.py backend/app/api/documents.py backend/app/api/folders.py backend/app/api/schemas.py backend/app/main.py backend/alembic/versions/0016_course_folders.py backend/tests/test_course_folders.py backend/tests/test_course_folders_migration.py --output-format concise
All checks passed!

backend/.venv/Scripts/python.exe -m pytest backend/tests/test_course_business.py -k upload_admin_enable_retrieval_and_agent_gate -q -p no:cacheprovider --tb=short
..                                                                       [100%]
2 passed, 18 deselected, 1 warning in 5.78s

cd frontend
node --test --test-isolation=none src/documentFolders.test.mjs
ℹ tests 6
ℹ suites 0
ℹ pass 6
ℹ fail 0

npm run build
> univ-course-rag-frontend@0.0.0 build
> vite build
failed to load config from D:\workspace\univ-course-rag\frontend\vite.config.js
error during build:
Error: spawn EPERM
```

- pytest 唯一 warning 为现有 Starlette TestClient 使用的 anyio BlockingPortal 弃用提示。
- Node 默认隔离进程同样遇到 `spawn EPERM`，改用 `--test-isolation=none` 后通过。6 项含分组 / 空夹 / 未分组 / 刷新竞态回退，以及三个受影响 Vue 组件的脚本和模板编译。
- 未做 / 风险：本环境拒绝启动 esbuild 子进程，普通与 PTY 构建均失败；组件编译不等同于完整 Vite 构建。待 bot 在可启动子进程的环境补跑 `npm run build` 并点验新控件。SQLite 与 PostgreSQL offline 测试不代表真实 PostgreSQL 在线迁移已验证。

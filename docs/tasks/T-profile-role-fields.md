# TASK: 角色主页与工号（Profile by role）

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-17 增量 / 业务优化 |
| 状态 | 实现完成；前端 build 验收受环境 EPERM 阻塞 |
| 须授权 | 库迁移（本批用户已授权） |

## 目标

- 个人主页按角色分支，去掉教师端「学生模板」错位。
- **学生**：姓名、**学号**、角色、所属**课内名单班**（现有 `classes`）。
- **教师**：姓名、**工号**、角色；**不展示所属班级**。
- **管理员**：姓名、角色；若有工号可展示；不展示班级。
- 后端 `users` 增加可空唯一 `employee_number`；`GET /auth/profile` 与账号管理按角色语义维护学号/工号。
- 管理员账号页：创建/编辑时，学生对「学号」、教师/管理员对「工号」；列表列标签随角色或双列展示。

## 非目标（禁止顺手做）

- 不做学院实体（见 T-college-minimal）。
- 不做资料夹 UI 大改（见 T-folders-ux-redesign）。
- 不重做课内名单班 / CSV / 学期；不改提问历史（仍不展示）。
- 不做 GraphRAG、第二套 RAG、换掉 pgvector。
- 不改密码重置/批量开户流程。

## 验收标准（可判定真假）

- [x] Alembic **0017**（父 **0016**）：`users.employee_number` 可空唯一；upgrade/downgrade 有隔离 SQLite 测 + PG offline DDL 测（仿 0015/0016）。
- [x] `GET /auth/profile` 响应含 `employee_number`；教师/管理员 `classes` 为空列表；学生仍返回课内名单班。
- [x] 管理员创建/PATCH 用户可写 `employee_number`；唯一冲突 409。
- [x] `ProfileView.vue` 已实现按 `role` 渲染：教师无「所属班级」、标签为工号；学生保留学号+班级（SFC 编译通过，浏览器点验待补）。
- [x] `AdminUsersView.vue` 已实现教师工号展示/编辑（双列展示，表单按角色切换；SFC 编译通过，浏览器点验待补）。
- [x] 命令：`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_course_business.py backend/tests/test_profile_role_fields.py -q -p no:cacheprovider --tb=short`（本次另含 `test_course_business_migration.py`）通过
- [ ] 定向 ruff 通过；`cd frontend; npm run build`（必要时 `--configLoader native`）通过

## 约束

- 栈：现有 FastAPI + Vue3 + Element Plus token；不另起皮肤。
- 迁移仅隔离验证为主；正式 cn_v2 upgrade 可在本卡或 College 卡末统一做一次（用户已授权迁移）。
- `student_number` 保留给学生/CSV；教师勿强制填学号。
- Conventional Commits 本地提交，不 push。

## 禁止改动的路径

- `.env`、密钥与 Cookie/Session 明文
- 评测金标 / `**/expected-outputs/**`
- 用户未点名的 `corpus/` 重解析产物
- Agent 合同 / Harness / PLAN-14～16 运行时主路径（除非仅为 profile schema 共用类型）
- 中期答辩材料/

## 相关上下文（指针）

- @docs/结题已拍板规格.md §3（本批已改为按角色主页）
- @docs/tasks/PLAN-17-course-business-foundation.md（历史「学号+班级」口径已由本卡覆盖增量）
- 代码：`backend/app/models/user.py`、`backend/app/api/course_business.py`（profile）、`backend/app/api/users.py`、`backend/app/api/schemas.py`、`frontend/src/views/ProfileView.vue`、`frontend/src/views/AdminUsersView.vue`

## 验证步骤（Agent 必须贴原始输出）

1. 隔离迁移测 + profile/账号相关 pytest
2. ruff 定向本卡 Python 文件
3. frontend build
4. diff 越界检查：仅本卡相关路径

## 完成记录

- 提交：按本次用户指令不提交、不推送，由 bot 提交。
- 验证摘要（2026-10-27）：
  - `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_course_business.py backend/tests/test_profile_role_fields.py backend/tests/test_course_business_migration.py -q -p no:cacheprovider --tb=short`
    原始输出：`37 passed, 1 warning in 16.32s`。唯一 warning 是 Starlette / AnyIO `BlockingPortal` 弃用提示。
  - `backend/.venv/Scripts/python.exe -m ruff check backend/app/models/user.py backend/app/api/schemas.py backend/app/api/users.py backend/app/api/auth.py backend/app/api/course_business.py backend/alembic/versions/0017_user_employee_number.py backend/tests/test_course_business.py backend/tests/test_profile_role_fields.py`
    原始输出：`All checks passed!`。
  - `cd frontend; npm run build` 原始输出：`failed to load config ... Error: spawn EPERM`（esbuild 子进程）。按卡重试 `npm run build -- --configLoader native`：`✓ 0 modules transformed.`、`[commonjs--resolver] spawn EPERM`（Vite `optimizeSafeRealPathSync` 子进程），未通过。
  - 两个变更页面用现有 `@vue/compiler-sfc` 的 `parse` + `compileScript(..., { inlineTemplate: true })` 检查；原始输出：`PASS Vue SFC compile: src/views/ProfileView.vue`、`PASS Vue SFC compile: src/views/AdminUsersView.vue`。此检查不替代 build / 浏览器点验。
- 未做 / 风险：正式库未执行迁移；仅隔离 SQLite 与 PG offline DDL 验证。前端完整 build 与浏览器点验待环境恢复后补齐。未扩展学院、资料夹、CSV 或密码流程。

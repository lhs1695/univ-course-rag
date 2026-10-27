# TASK: 最小学院实体（College）

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-17 增量 / 业务优化 |
| 状态 | implemented / 构建及浏览器验收受环境阻塞 |
| 须授权 | 库迁移（本批用户已授权） |

## 目标

- 结题加**演示级**学院实体，非完整教务组织树。
- 表 `colleges`：`code`（唯一）、`name`；可选时间戳。
- `users.college_id`、`courses.college_id` 可空 FK（ON DELETE SET NULL 或 RESTRICT——删学院前须无挂载，返回 409 亦可）。
- 管理员 CRUD 学院（建议挂 `/admin/business` 新小节，或同页 section）。
- 课程创建/编辑可选学院；课表/管理课程列表可见学院名。
- 个人主页展示所属学院名（有则显示）。
- 账号管理可为用户选学院。

## 非目标（禁止顺手做）

- **不做**：专业/年级树、培养方案、按学院权限隔离、真选课、教学班与行政自然班双轨重做。
- 课内 `course_classes` 仍为**课内名单班**，不改成行政自然班。
- 不做资料夹 UX（见 T-folders-ux-redesign）；不做 GraphRAG/第二套 RAG。

## 验收标准（可判定真假）

- [x] Alembic **0018 → 0017**：`colleges` + 两处可空 RESTRICT FK；隔离 SQLite upgrade/downgrade + PG offline DDL。
- [x] API：`GET/POST /admin/colleges`，`PUT/DELETE /admin/colleges/{id}`；code/name 校验；删前有用户或课程挂载 → 409。
- [x] `CourseCreate/Update`、管理员课程 PATCH、用户 create/PATCH 支持 `college_id`；`CourseOut`/`UserOut`/`ProfileOut` 带 `college_id`/`college_name`（或等价）。
- [ ] 前端：`AdminBusinessView`（或等价）可 CRUD 学院；课程归属可选学院；`ProfileView` 显示学院；`AdminUsersView`/`AdminCoursesView` 可见可编辑。
- [x] pytest：新建 `test_colleges.py`（+ migration 测）通过；相关 business/profile 回归通过（60 passed，1 项既有弃用警告）
- [ ] ruff + frontend build 通过

## 约束

- 学院**不是**权限边界；问答/检索/Agent 仍按课程成员，不按学院过滤。
- Element Plus / 现有 token；文案用「学院」。
- 种子数据：迁移可不强制种子；管理员可自建演示学院（如「计算机学院」）。

## 禁止改动的路径

- `.env`、密钥
- Agent 主路径 / Harness 合同（除非 CourseOut 字段扩展波及序列化测试的最小改动）
- 中期答辩材料/
- 大规模 corpus 重解析

## 相关上下文（指针）

- @docs/结题已拍板规格.md §3
- 代码：`backend/app/models/`、`backend/app/api/course_business.py`、`backend/app/api/courses.py`、`backend/app/api/users.py`、`frontend/src/views/AdminBusinessView.vue`、`AdminCoursesView.vue`、`AdminUsersView.vue`、`ProfileView.vue`

## 验证步骤（Agent 必须贴原始输出）

1. migration + colleges pytest
2. ruff；frontend build
3. diff 越界检查

## 完成记录

- 提交：按当次用户指令不提交，由 bot 提交。
- 实现：学院模型与管理员 CRUD；课程及账号学院设置/清除；登录、个人资料、课程列表输出学院；管理页与课程书架展示学院。沿用 Element Plus，未修改课程权限或 Agent/RAG。
- 验证摘要：见仓库根 `.codex-last-college.txt`，含实际命令及原始输出摘要。SQLite 仅隔离内存库；PG 仅 offline DDL，未迁移运行中的数据库。
- 未做 / 风险：标准 `npm run build` 被 Windows `spawn EPERM` 阻断，`--configLoader native` 也被同一环境问题阻断；五个修改页面的 Vue 脚本及模板独立编译通过。浏览器新控件点击验收待补，不据此宣称前端构建/浏览器验收通过。

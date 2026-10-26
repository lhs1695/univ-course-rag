# TASK: 课程业务基础完善

> 对齐 [结题已拍板规格](../结题已拍板规格.md)。

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-17 |
| 状态 | implemented / 定向测试+build 已过；Vite 人工点验与演示库迁移仍待本机 |
| 须授权 | 本轮已授权五件套实现与隔离测试迁移；正式库修改、真实名单导入仍未授权 |

## 目标

- 盘点并完善学期、班级、学生名单、个人主页与课程成员之间的最小业务模型。
- 明确学生、教师、管理员的业务权限和可见范围。
- 资料协作固定为教师上传 → 管理员可见 → 管理员启用检索的两步流程。

2026-10-26 确认：学期、班级、CSV 名单、极简主页（无提问历史）、资料两步启用检索五件套仍为必做，范围见 [拍板规格 §3](../结题已拍板规格.md#3-课程业务基础plan-17必做与-agent-并行盘点)。业务盘点与 Agent 运行时薄切并行；不以五件套全部完成为调查报告的前置。后续页面跟随已视觉通过的版式增补，不重开前端翻新。

## 非目标

- 不新建平行的 users/courses 身份或课程体系。
- 不在没有需求证据时建设复杂组织层级、审批流、消息通知或学习分析预测。
- 不在本卡顺手实现教师 Agent；与 PLAN-15/16 通过清晰接口协作。
- 不在正式演示库直接试验破坏性迁移。

## 验收标准

- [x] 先形成现有 users、courses、course_members、资料与问答日志的数据关系盘点（见 [现有模型盘点](PLAN-17-inventory-current-model.md)）。
- [x] 学期含名称与起止，课程可挂一个学期；班级为课下行政班，学生经名单进班并成为 `course_members`；先核对字段/关联/权限矩阵，再决定是否需要迁移。
- [x] CSV 名单为必做，字段为学号/姓名/班级；校验空行与重复，提供失败/导入结果摘要。本课教师或管理员可导入，不能跨越课程权限。
- [x] 教师、管理员和学生的关键业务路径有服务端权限测试；不能只靠前端隐藏入口。
- [x] 极简个人主页只展示姓名、学号、角色、所属班级，不展示提问历史。
- [x] 教师限本课上传与查看；上传后管理员可见，由管理员启用检索；启用前不得被普通检索或 Agent 工具读作证据。删除/禁用沿用现有软禁用思路，不增加审批层级。
- [x] 管理员负责启用检索、全站账号与学期；关键接口按上述权限矩阵验证。
- [x] 迁移在隔离数据库验证，旧行保留；定向测试、ruff 通过。
- [x] 前端 `npm run build` 本轮通过；关键 Vite 页面人工点验仍待本机。
- [x] 按本卡指定阅读/更新范围，同步拍板规格 §3、数据关系说明、施工计划、当前交接与会话状态，记录未做项和迁移风险。

## M4 实现与复用（2026-10-26）

基线 M3 `4587421`。复用 FastAPI/Pydantic、SQLAlchemy/Alembic、Cookie Session、现有 users/courses/course_members、Element Plus 与学/问、册/衡样式；无新依赖、模型调用、组织身份体系或 RAG 管线。Agent 主路径和合同均未修改，沿用其现有检索开关检查。数据关系及权限表见 [盘点附录](PLAN-17-inventory-current-model.md#m4-实现后的最小数据关系2026-10-26)。

- 学期：管理员 `/admin/semesters` GET/POST、`/{id}` PUT/DELETE；课程 POST/PATCH 可设置或清空 `semester_id`。日期及名称校验，仍被课程引用的学期不能删除。
- 班级：本课教师/管理员 `/courses/{course_id}/classes` GET/POST、`/{id}` PUT/DELETE；非空班不允许删除；课程间班级不能串用。
- CSV：`POST /courses/{course_id}/roster` multipart `file`，UTF-8（支持 BOM），固定表头 `学号,姓名,班级`，最多 1 MiB / 5000 行。学号保持字符串及前导零。匹配已有学生账号，姓名必须相符，按行报告空行、字段错误、重复、缺账号、非学生或班级冲突；摘要 total/imported/unchanged/rejected/errors。重复学号的所有出现均拒绝，同班重导 unchanged；不暗中换班，有效行一起提交，约束冲突返回 409 并整体回滚。
- 账号：管理员创建/编辑姓名与唯一可空学号；教师不能改全站账号。旧账号可由管理员补齐资料后导入。不实现名单批量开户/默认密码下发。
- 主页：`GET /auth/profile` 只读当前本人，四类白名单字段；班级随成员移出立即消失，无查询历史。
- 资料：新上传及 DB/ORM 默认 `false`；管理员可跨课列出、详情、原文和启用，但不因此获得问答/Agent 课程成员资格；教师只在本课上传/查看/重试/停用。学生列表、详情与原文都排除未启用资料。PATCH true 仅管理员；DELETE 复用 `retrieval_enabled=false`，保留原文/任务/chunks；不新增审批层。Dense/Hybrid、Agent 搜索/open_evidence/quality 及其既有来源复检均受开关约束。
- 前端：管理员「学期 / 班级」占位替换为 `/admin/business`，另有 `/admin/documents`；教师成员页复用 `CourseRosterPanel`；全角色 `/profile`；账号页可维护姓名/学号，教师上传后提示待管理员启用。M3「课程调查」入口保留。

## 迁移边界与实际验证

Revision：[`0015_course_business.py`](../../backend/alembic/versions/0015_course_business.py)，父 `0014`。新增学期/班级表及可空关联、姓名/学号、唯一/复合外键/日期约束；资料仅变更未来 INSERT 默认值，旧开关不改。隔离 SQLite batch DDL 期间 FK 关闭，验证阶段开启并执行 `foreign_key_check`；降级后旧账号、课程、成员和资料行保留，新增资料的 false 状态不被改成 true。降级会丢失新增个人资料/学期/班级关联数据，不在正式库试验。PostgreSQL 只编译 SQL，无真实连接或并发证据。

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_course_business.py backend/tests/test_course_business_migration.py backend/tests/test_agent_task_api.py backend/tests/test_agent_investigation_runner.py backend/tests/test_agent_investigation_api.py backend/tests/test_agent_task_runtime.py -q -p no:cacheprovider --tb=short
# 91 passed, 1 warning in 25.29s（业务 API 20 + 隔离迁移 2 + Agent 回归 69）
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_course_business_migration.py -q -p no:cacheprovider
# 隔离验证命令：显式 sqlite:// 内存连接，直接 Operations.context 执行 0015 upgrade/downgrade，不加载 alembic/env.py。
# 2 passed, 1 warning in 0.78s
backend/.venv/Scripts/python.exe -m ruff check backend/app/api/course_business.py backend/app/api/auth.py backend/app/api/users.py backend/app/api/courses.py backend/app/api/admin_courses.py backend/app/api/documents.py backend/app/api/schemas.py backend/app/models/__init__.py backend/app/models/course.py backend/app/models/document.py backend/app/models/user.py backend/app/main.py backend/alembic/versions/0015_course_business.py backend/tests/test_course_business.py backend/tests/test_course_business_migration.py --output-format concise
# All checks passed!
node --test --test-isolation=none frontend/tests/*.test.mjs
# tests 49 / pass 49 / fail 0
# frontend 目录：
npm run build
# 本轮（恢复后）npm run build：✓ built in ~7.6s，exit 0（chunk size warning only）
```

8 个相关 Vue 文件使用 stdin Node + `@vue/compiler-sfc` parse / compileScript / compileTemplate，全部 passed；不是 build 或 Vite 实点的替代品。Playwright skill 预检 npx 存在；`npx --no-install --package @playwright/cli playwright-cli --help` 被 npm-cache EPERM 阻断，未下载依赖。DevSpace open_workspace 返回 `MCP tool call requires approval, but approval policy is never`，未通过该工具修改或执行。

最后 auth 返回姓名/学号、router 注册位置微调后，M4 两文件复验 `22 passed, 1 warning in 9.63s`，ruff 通过。`npm run dev -- --host 127.0.0.1 --configLoader native --port 5177` 启动后，curl 检查首页 200、`/src/main.js` 与 `/src/views/AdminBusinessView.vue` 均 500（Vite Windows realpath 子进程 `spawn EPERM`），已 Ctrl-C 停止；无 UI 点验通过证据。

本地提交尝试：精确列出本卡 31 文件的 `git add -- …` 返回 `fatal: Unable to create 'D:/workspace/univ-course-rag/.git/index.lock': Permission denied`；暂存区为空，HEAD 仍 `4587421`，未生成 M4 commit/SHA、未 push。未尝试覆盖 .git 权限或暂存中期笔记。

另一次补跑原 `test_auth.py test_courses.py` 和上述 4 份 Agent 测试：`69 passed, 1 warning, 26 errors in 18.69s`，26 项都在公共 tmp_path fixture 因 `C:/Users/16747/AppData/Local/Temp/pytest-of-16747` WinError 5 失败，不能计为账号/课程回归通过。未运行全量 suite。业务专项独立 TestClient、内存 SQLite、FakeEmbedder/FakeLLM；上传测试 mock 文件写入和后台入库，用合成 chunk 验证证据门禁，原文响应使用既有 PDF fixture；没有真实模型或正式库上传。

## 本机待验与未做项

- [x] 本轮 build 已通过。仍待 Vite：管理员姓名/学号 → 学期增改/课程关联 → 班级/CSV 摘要。
- [ ] 用隔离、已迁移测试库：教师上传 → 教师不能启用 → 管理员可见并启用 → 学生检索/问答有依据 → 点击引用回原 PDF 页；停用后普通检索与调查来源不可读。教师「课程调查」仍可进入。
- [ ] 学生个人主页核对姓名、学号、角色、班级，无提问历史；教师/学生跨课班级和导入均被拒。
- [ ] 账号/课程既有回归及受资料发布/软删除新合同影响的既有用例，在本机权限正常时定向复核；本轮不宣称全仓回归通过。
- [x] 精确 stage 本卡文件并本地提交（见 SESSION_STATE）；不 push，未 stage 中期笔记。

未执行默认 DATABASE_URL / 演示库 / cn_v2 upgrade，未导入真实名单，未读 `.env`，未跑真实模型，未改中期材料。复杂 UI、批量开户、真实 PostgreSQL 迁移/并发、真实 Vite 端到端均无通过证据。

## 约束

- 先调查再定 schema；不得预设当前模型没有已有的学期/班级字段。
- 复用现有 PostgreSQL/Alembic、Session 与课程成员权限。
- 真实名单、正式库数据、破坏性迁移和外部数据导入须当次授权。
- 不把课程级问答统计解释为个人成绩或知识掌握度。

## 禁止改动的路径

- .env、密钥、Cookie/Session 明文、.git、venv、node_modules。
- 评测金标、用户未提交改动、未经授权的 corpus/local。
- 正式演示数据库及无关 RAG 检索逻辑。

## 相关上下文

- [产品合同](../结题产品定义与完工标准.md) §2、§4
- [施工计划](../implementation-plan.md) PLAN-17
- [PLAN-02 生命周期与权限](PLAN-02-lifecycle-permissions.md)
- 历史参考：`中期答辩材料/笔记/03-后期研究与结题规划.md`（冻结，非链接）
- [硬规则](../../AGENTS.md)、[会话状态](SESSION_STATE.md)

## 验证步骤

1. 检查 git status 和当前授权；不读取 .env。
2. 阅读现有 SQLAlchemy 模型、迁移、API 与页面，绘制当前数据关系。
3. 先提交数据模型/业务流程建议，再实施获准的最小改动。
4. 在隔离数据库验证迁移、旧数据兼容、权限和回滚路径。
5. 运行定向 pytest、ruff、前端 build 和相关 UI 路径；贴原始输出与未完成项。


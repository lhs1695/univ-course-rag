# TASK: 撤下课内调查 Agent 产品面（保留 Key 槽位）

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-14/15/16 产品面撤回（Key 预留） |
| 状态 | implemented；定向回归通过；完整 build / 本地提交受权限阻塞，待 bot 收尾 |
| 须授权 | 无（删产品代码；不做破坏性删表迁移除非必要） |

## 目标

- **删除课内调查半成品产品面**：
  - 前端：`InvestigationView.vue`、路由 `/courses/:courseId/investigation`、App 导航「课程调查」、`investigationApi` 及专用文案/错误码展示、相关 frontend 测试。
  - 后端：挂载的调查任务 API（`agent_tasks` 路由及 retention 若仅服务调查）、`agent_investigation` runner/服务、仅服务该产品的调用链；删除或改写依赖调查路径的 pytest（`test_agent_investigation_*`、`test_agent_task_*` 等中产品 API 测）。
- **保留**：
  - `.env.example` / Settings 中 `AGENT_DEEPSEEK_API_KEY` / `AGENT_DEEPSEEK_MODEL` / `AGENT_DEEPSEEK_BASE_URL`（及注释：教师 Agent 预留，调查产品已撤下）。
  - 若有独立「设置页」仅展示 Agent Key 配置，保留；若 Key 仅在 `.env`，保持文档说明即可。
  - Alembic 历史与 `agent_tasks` 表结构可保留（避免破坏性迁移）；代码不再暴露产品入口。可在模型/包留下最短说明注释「schema retained; product withdrawn」。
- **文档**：更新 `docs/tasks/SESSION_STATE.md`、`docs/当前交接.md`、`docs/workflow.md` 中「课程调查」验收口径 → 已撤下、Key 预留；拍板规格若写死「M3 调查入口保留」则加一句现行变更，勿大段改写中期材料。

## 非目标

- 不重做新 Agent
- 不删 Insights「问答反馈」
- 不删 `.env` 真密钥、不读不打印密钥
- 不强制 DROP 表（除非你能证明零风险且测试绿；默认保留表）

## 验收标准

- [ ] 前端无 investigation 路由/菜单/页面；相关测 65/65 通过；完整 build 被 `spawn EPERM` 阻塞，未计通过
- [x] `main.py` 不再 include 调查产品 router；调查任务与 retention API/服务删除
- [x] 定向 pytest：删除的测不再被收集；其余既有测（auth/docs/business/folders 等）不受损；会话级隔离临时目录下 136 passed（标准 tmp_path 权限失败另记）
- [x] `.env.example` 仍含 `AGENT_DEEPSEEK_*` 且注释标明预留
- [x] workflow/交接写明调查 Agent 产品已撤下

## 禁止改动

- `.env` 真值
- 中期答辩材料正文大改
- RAG 主路径

## 相关上下文

- @frontend/src/views/InvestigationView.vue
- @frontend/src/App.vue / router.js / api.js
- @backend/app/api/agent_tasks.py
- @backend/app/services/agent_investigation.py
- @backend/app/main.py
- @.env.example

## 验证步骤

1. git grep investigation / 课程调查（产品路径应仅剩历史 docs/注释）
2. pytest 子集 + ruff 改动文件
3. frontend tests + build

## 完成记录

- 日期：2026-10-27；只做本卡；不 push。
- 提交：无新 SHA。已按下列 34 个路径精确尝试 `git add -- <路径清单>`，但 `.git/index.lock` Permission denied，未能 stage/commit；交由 bot 本地提交，建议标题 `chore(agent): retire investigation product keep AGENT key slots`，不要 push。
- 实现：删除 InvestigationView、路由/菜单/helper/专用错误文案；删除任务与 retention API、runner/runtime/store/retention 服务、仅服务调查的 contracts/Replay 包与 9 份后端产品测试及 1 份前端测试。清除 AdminDocumentsView 的调查引用文案与公共 schemas 中调查专用 retention DTO。业务测试去掉调查工具依赖，保留资料授权与 Dense/Hybrid 启停检索断言。
- 保留：Settings/.env.example 三个 `AGENT_DEEPSEEK_*` 槽位和兼容访问器；`agent_tasks` / `agent_task_events` 模型及 Alembic 历史（schema retained），两项原迁移测试保留。未 DROP 表、未执行正式库迁移或数据清理；Insights/RAG 主路径未改；未读写 `.env` 真值。中期材料 D/M、既有临时文件、未跟踪 corpus 均未改动或暂存。
- 工具限制：DevSpace 返回 `MCP tool call requires approval, but approval policy is never`；项目提及的 `univ-course-rag-dev-loop` 未出现在可用技能/本机两个技能目录，按用户本次实现指令使用本地工具。没有调用 bot 或子代理。

### 实际命令与原始输出摘录

产品路径核查（exit 1 = 无匹配）：

```powershell
git grep -n -I -E '/courses/.*investigation|课程调查|investigationApi|InvestigationView|agent-tasks' -- frontend/src frontend/tests backend/app/main.py
# 无输出；exit 1
git grep -n -I -E 'investigation|Investigation|课程调查|agent-tasks' -- frontend/src frontend/tests backend/app
```

```text
backend/app/config.py:58:    # Teacher Agent reserved; investigation product withdrawn. No runner consumes these slots.
backend/app/models/agent_task.py:1:"""Schema retained; investigation product withdrawn. No task API or runner is exposed."""
```

`git grep -n -I -E 'test_agent_investigation|test_agent_task_(api|runtime|store|retention)|app\.agent|services\.agent_' -- backend/tests` → 无输出，exit 1。
`git grep -n -E 'AGENT_DEEPSEEK_(API_KEY|MODEL|BASE_URL)=' -- .env.example`：

```text
.env.example:77:AGENT_DEEPSEEK_API_KEY=
.env.example:79:AGENT_DEEPSEEK_MODEL=
.env.example:80:AGENT_DEEPSEEK_BASE_URL=
```

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests --collect-only -q -p no:cacheprovider
```

```text
729 tests collected in 3.48s
```

全量仅收集、不运行；调查产品测均删除，仅 `test_agent_task_migration.py` 两项仍收集。Starlette/anyio 弃用 warning 1 条。

标准运行（以下命令及 auth 单文件 `-x` 复核均遇临时目录权限；首轮中止，不能计为通过）：

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_auth.py backend/tests/test_courses.py backend/tests/test_course_business.py backend/tests/test_course_business_migration.py backend/tests/test_course_folders.py backend/tests/test_course_folders_migration.py backend/tests/test_colleges.py backend/tests/test_colleges_migration.py backend/tests/test_profile_role_fields.py backend/tests/test_insights.py backend/tests/test_agent_task_migration.py -q -p no:cacheprovider --tb=short --basetemp=.tmp-retire-investigation-pytest-20261027
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_auth.py -x -q -p no:cacheprovider --tb=short --basetemp=.tmp-retire-investigation-auth-20261027
```

```text
PermissionError: [WinError 5] 拒绝访问。: 'D:\\workspace\\univ-course-rag\\.tmp-retire-investigation-auth-20261027'
```

无需 tmp_path 的原始子集：

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_course_business.py backend/tests/test_course_business_migration.py backend/tests/test_agent_task_migration.py backend/tests/test_colleges_migration.py backend/tests/test_course_folders_migration.py -q -p no:cacheprovider --tb=short
```

```text
28 passed, 1 warning in 12.20s
```

补充回归使用以下 stdin 会话级插件：仅替代临时目录创建，普通 `Path.mkdir()` 创建本次唯一目录，仍跑原测试/断言和内存 SQLite/Fake fixture；不修改仓库公共 fixture、不变更 ACL。补齐 storage 文件/PDF 访问回归。

```powershell
@'
from pathlib import Path
from uuid import uuid4
import pytest

root = Path.cwd() / ('.tmp-retire-investigation-regression-' + uuid4().hex)
root.mkdir()

class SessionTempPaths:
    @pytest.fixture
    def tmp_path(self):
        path = root / uuid4().hex
        path.mkdir()
        return path

paths = [
    'test_auth.py', 'test_courses.py', 'test_storage.py',
    'test_course_business.py', 'test_course_business_migration.py',
    'test_course_folders.py', 'test_course_folders_migration.py',
    'test_colleges.py', 'test_colleges_migration.py',
    'test_profile_role_fields.py', 'test_insights.py',
    'test_agent_task_migration.py',
]
raise SystemExit(pytest.main(
    ['backend/tests/' + name for name in paths]
    + ['-q', '-p', 'no:cacheprovider', '--tb=short'],
    plugins=[SessionTempPaths()],
))
'@ | backend/.venv/Scripts/python.exe -
```

```text
136 passed, 1 warning in 60.71s (0:01:00)
```

OpenAPI + HTTP 无数据库调用冒烟：backend 工作目录、`.venv/Scripts/python.exe -` stdin；导入 app 之前先设 `Settings.model_config['env_file'] = None`，断言 OpenAPI 无 `agent-tasks` / `investigation`、仍有 `/courses/{course_id}/insights` 与 `/courses/{course_id}/ask`，TestClient POST 原路径：

```text
POST /courses/retired/agent-tasks -> 404
POST /admin/agent-tasks/retention -> 404
OpenAPI: investigation absent; Insights and ask retained: PASS
```

```powershell
backend/.venv/Scripts/python.exe -m ruff check backend/app/main.py backend/app/api/schemas.py backend/app/config.py backend/app/models/agent_task.py backend/tests/test_course_business.py
node --test --test-isolation=none frontend/tests/*.test.mjs
```

```text
All checks passed!
ℹ tests 65
ℹ pass 65
ℹ fail 0
ℹ skipped 0
```

frontend 工作目录 `npm run build` → exit 1（未通过）：

```text
> univ-course-rag-frontend@0.0.0 build
> vite build

failed to load config from D:\workspace\univ-course-rag\frontend\vite.config.js
error during build:
Error: spawn EPERM
```

补充 `node --input-type=module` stdin 调用 `@vue/compiler-sfc` 的 parse/compileScript/compileTemplate 检查 App.vue → `App.vue script/template compilation: PASS`；`node --check src/router.js` / `node --check src/api.js` 无输出，exit 0；AdminDocumentsView 编译由前端相关测覆盖。以上不替代完整 build 或浏览器验收。本轮没有新增控件，未启动 Vite 点验。

`git diff --check` → exit 0，无空白错误（Git 有 LF→CRLF 提示）；迁移目录 `git diff --name-only -- backend/alembic` 无输出。新增文档链接只指向本卡/既有 workflow 与交接。

- 未做：完整 build 成功复验（EPERM）；浏览器点验；真实模型/正式库操作；新 Agent；无关历史文档/中期材料改写；push。没有把 Fake/开发者验证宣称为人工正确率或结题通过。

### 待 bot 提交的精确文件清单（34 项）

原始输出：

```text
fatal: Unable to create 'D:/workspace/univ-course-rag/.git/index.lock': Permission denied
```

只 stage 下列本卡文件；不要批量 add 工作区，不碰用户已有中期材料 D/M、临时文件或未跟踪 corpus。先在本机复验 `cd frontend; npm run build`，权限允许时可用标准 pytest 命令复验上面的 12 文件子集。模型/迁移历史保留，不在待提交清单中。

```text
.env.example
backend/app/agent/__init__.py
backend/app/agent/contracts.py
backend/app/agent/replay_harness.py
backend/app/api/agent_task_retention.py
backend/app/api/agent_tasks.py
backend/app/api/schemas.py
backend/app/config.py
backend/app/main.py
backend/app/models/agent_task.py
backend/app/services/agent_investigation.py
backend/app/services/agent_task_retention.py
backend/app/services/agent_task_runtime.py
backend/app/services/agent_task_store.py
backend/tests/test_agent_contracts.py
backend/tests/test_agent_e5a_fixture.py
backend/tests/test_agent_investigation_api.py
backend/tests/test_agent_investigation_runner.py
backend/tests/test_agent_replay_harness.py
backend/tests/test_agent_task_api.py
backend/tests/test_agent_task_retention.py
backend/tests/test_agent_task_runtime.py
backend/tests/test_agent_task_store.py
backend/tests/test_course_business.py
docs/tasks/SESSION_STATE.md
docs/tasks/T-retire-investigation-agent.md
docs/workflow.md
docs/当前交接.md
frontend/src/App.vue
frontend/src/api.js
frontend/src/router.js
frontend/src/views/AdminDocumentsView.vue
frontend/src/views/InvestigationView.vue
frontend/tests/investigation.test.mjs
```

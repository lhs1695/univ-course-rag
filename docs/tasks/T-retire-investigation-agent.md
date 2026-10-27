# TASK: 撤下课内调查 Agent 产品面（保留 Key 槽位）

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-14/15/16 产品面撤回（Key 预留） |
| 状态 | ready |
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

- [ ] 前端无 investigation 路由/菜单/页面；`npm` 相关测与 build 通过
- [ ] `main.py` 不再 include 调查产品 router（或 router 空壳删除）
- [ ] 定向 pytest：删除的测不再被收集；其余既有测（auth/docs/business/folders 等）不受损；可跑一轮相关子集
- [ ] `.env.example` 仍含 `AGENT_DEEPSEEK_*` 且注释标明预留
- [ ] workflow/交接写明调查 Agent 产品已撤下

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

- 提交：
- 验证摘要：

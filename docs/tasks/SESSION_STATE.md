# SESSION_STATE

更新：2026-10-26（Asia/Shanghai）。此文件用于在长任务中断后恢复上下文；实际状态以代码、测试输出与工作区为准。现行拍板见 [结题已拍板规格.md](../结题已拍板规格.md)。

## 当前目标

**PLAN-FE-01 前端全面翻新已落地（本地提交，未 push）**。下一步：用户本机 Vite 点验 UI → 再 Codex 审结题开工计划 / PLAN-14～17。产品主线仍是教师侧课内问题调查 Agent（M1→M2→M3）与课程业务最小集；**GraphRAG/知识图谱结题不做**。

## 已确认决策（2026-10-26 拍板）

- 场景锁死：课内问题调查；验收 = 发起调查 → 结构化报告 → Fake/Replay 可回放。
- Agent 分期：M1 合同+Harness+任务可读；M2 报告 API；M3 教师 UI+最小 lease/取消/恢复。
- 业务：学期 / 班级 / CSV 名单 / 极简主页（无提问史）/ 资料两步启用检索；盘点 ∥ Agent。
- Key：硅基流动 Embedding + DeepSeek 官方问答 + 可选 `AGENT_DEEPSEEK_*`；默认 Fake 可开发。
- GraphRAG / 知识图谱：**结题不做**；主线全部完成后再考虑演示锦上添花。
- 不上默认 LangGraph/LlamaIndex；RAG 附线仅有限校准。
- 中期答辩材料/**冻结**；结题以 `docs/` 为准。精华摘自 `中期答辩材料/笔记/04`（Harness 12 类）、`…/07`（E5-A）。
- 用户独立试用已取消；空白机/备份恢复暂缓。
- 真实模型、问句外发、正式库破坏性迁移须当次授权；不默认 push。
- **前端翻新优先**：学生学/问可切换（默认学）；教师「册」、管理「衡」；同源 token；三角色+登录一次换齐；结题导航占位灰项；先 FE 后后端开工。提示词见 `frontend/prompts/FE-refresh-v1.md`。

## 本轮文档整理

- 新增 [结题已拍板规格.md](../结题已拍板规格.md)。
- 更新 implementation-plan / backlog / 当前交接 / INDEX / 产品定义与 validation 中 GraphRAG 口径与施工顺序。
- `.gitignore` 忽略 `.tmp-*.log` 等本地运行日志；`results/` 仍 ignore，本机评测文件保留。
- **未改** `中期答辩材料/` 正文；PLAN-14 `backend/app/agent/` 半成品本轮可不强制提交（另议）。

## 工作区分堆（整理时）

| 堆 | 内容 | 本轮处理 |
| --- | --- | --- |
| docs SSOT / 计划 / 任务卡 | 已拍板规格、PLAN-14～17、合同审计等 | 文档 commit |
| `backend/app/agent/` + agent 测试 | PLAN-14 半成品 | 暂留工作区，另议提交 |
| `.tmp-*.log` | 本地 uvicorn/vite 日志 | gitignore，不入库 |
| `results/` | 评测 JSON 等 | 已 ignore，不删 |
| `中期答辩材料/` 及笔记 | 冻结历史；工作区或有旧 diff | **不 stage、不改正文** |

## 验证（历史，PLAN-14 半成品）

- 最近记录：`test_agent_contracts` + `test_agent_replay_harness` → 26 passed（须用 `backend/.venv`）；不代表生产运行时已完成。

## 下一步

1. 用户本机 `npm run dev` 按 `frontend/DESIGN-TOKENS.md` 验收学/问、三角色与演示闭环观感。
2. 验收通过后，**Codex 只审**开工计划包：结题已拍板规格、implementation-plan、PLAN-14～17、teacher-agent-task-contract（对照 Harness 12 类与 E5-A）。
3. 审通过并用户点头后：整理 PLAN-14 半成品本地提交（可选）→ 授权 15A（仅隔离库迁移）或 17 盘点。
4. 不对默认 `DATABASE_URL` / 正式 `cn_v2` 跑迁移；不 push 除非用户点名。
# SESSION_STATE

更新：2026-10-26（Asia/Shanghai）。此文件用于在长任务中断后恢复上下文；实际状态以代码、测试输出与工作区为准。现行拍板见 [结题已拍板规格.md](../结题已拍板规格.md)。

## 当前目标

结题开工计划文档收口完成；审阅必须改项已全部确认，见 [确认记录](PLAN-review-开工计划-2026-10-26.md)。前端视觉已通过，下一步待用户决定是否下令开 M1；本轮仅改 Markdown，不开实现。

2026-10-26 PLAN-FE-01 visual punch：学生「问」强化为深蓝证据台、「学」加强纸墨与实心按钮，教管仍浅色；前端 46/46 测试通过；本机 `npm run build` 已通过；未 push。前端视觉已获用户通过（既有测试/build 记录，本轮未复跑）。

## 已确认决策（2026-10-26 拍板）

- 场景锁死：课内问题调查；验收 = 发起调查 → 结构化报告 → Fake/Replay 可回放。
- Agent 分期退出：M1 合同+Fake/Replay Harness+任务创建后独立持久化可读/无权拒绝；M2 报告 schema/来源校验落库、失败有终态；M3 教师 UI+最小 lease/取消生效/一次进程中断后显式恢复。
- 任务创建/单任务读取/报告读取统一课程教师权限；同课 queued/running/cancel_requested 仅 1 个活跃调查，冲突确定；retry 为同任务新 attempt，不静默重启终态。
- 主路径 queued → running → succeeded|failed|cancelled|budget_exceeded，另含 cancel_requested、interrupted → 显式 resume 回 queued 或失败。预算跨 attempt 累计，下一调用前检查、有限超时/工具重试、取消优先与合法 finish 例外详见 [任务合同 §3](../teacher-agent-task-contract.md#3-任务状态合同) / [§7](../teacher-agent-task-contract.md#7-初始预算与可判定终止规则2026-10-26-用户确认)。
- Harness M1 内存+任务落库读取，M2 报告/外发零调用/空窗/E5-A，M3 取消/恢复/DB 幂等/来源不可用/UI 确认与 Vite PDF 回页；物理 TTL 可后置，失效来源不可解析不可后置。
- 未 confirm_external_processing（及 M3 UI 确认）创建前拒绝，外部 LLM/Embedding/语义分组各 0 调用；重要结论回溯 Document/页码，删除/禁用/越权不展示。
- E5-A 固定同课程/时间窗/样本快照 A 统计列表、B 相似组（若可用）、C 报告；开发者核验固定事实/来源与零捏造/零确定化候选原因等门禁；无真实教师不得宣称效率已验证，真实模型质量单列。
- 业务：学期 / 班级 / CSV 名单 / 极简主页（无提问史）/ 资料两步启用检索；盘点 ∥ Agent。
- Key：硅基流动 Embedding + DeepSeek 官方问答 + 可选 `AGENT_DEEPSEEK_*`；默认 Fake 可开发。
- GraphRAG / 知识图谱：**结题不做**；主线全部完成后再考虑演示锦上添花。
- 不上默认 LangGraph/LlamaIndex；RAG 附线仅有限校准。
- 中期答辩材料/**冻结**；结题以 `docs/` 为准。精华摘自 `中期答辩材料/笔记/04`（Harness 12 类）、`…/07`（E5-A）。
- 用户独立试用已取消；空白机/备份恢复暂缓。
- 真实模型、问句外发、正式库破坏性迁移须当次授权；不默认 push。
- **前端翻新优先**：学生学/问可切换（默认学）；教师「册」、管理「衡」；同源 token；三角色+登录一次换齐；结题导航占位灰项；先 FE 后后端开工。提示词见 `frontend/prompts/FE-refresh-v1.md`。

## 本轮文档收口（仅 Markdown）

- 6 项已确认决策写入拍板规格与 task-contract；implementation-plan、PLAN-14～17、审阅确认记录与交接/索引同步。
- PLAN-14～17 四处历史笔记断链改为 `中期答辩材料/笔记/...` 纯文本；详细预算只在合同维护。
- Agent 半成品与两份测试、中期笔记目录仍未跟踪；本轮不读、不改、不暂存。未改业务代码/中期正文、未读密钥、未运行产品测试/迁移/模型/服务；仅做文档内容/链接与 diff 自检。
- 本地提交：`ee8578e` `docs(plan): freeze M1-M3 exits, budget, harness map after review confirm`（13 份 Markdown）；`main` 比远程 ahead 7；**未 push**。

## 本轮实际验证（纯文档）

- `backend/.venv/Scripts/python.exe -`（stdin 文档自检，不导入业务代码）：6 项确认决策/预算/硬验收与 H01–H12、timeout/external 分期检查 PASS；13 份 Markdown、175 个本地链接（含 17 个节锚点）检查，broken_links=0；四处旧笔记断链已移除；初审必须改/建议改/可开工正文保持原样，待确认勾选=0。
- `git diff --check`：退出码 0、无输出。`git status --short` 初检仅原有未跟踪 Agent/测试/中期笔记，另有临时目录访问被拒警告，未进入临时目录。
- 未运行 pytest、ruff、build、Vite、迁移或模型；没有把历史 26 passed/前端记录当成本轮输出。本地提交已完成（ee8578e）；未 push。

## 工作区分堆（整理时）

| 堆 | 内容 | 本轮处理 |
| --- | --- | --- |
| docs SSOT / 计划 / 任务卡 | 本轮 13 份 Markdown | 保留 diff；git add 权限拒绝，待补本地 commit |
| `backend/app/agent/` + agent 测试 | PLAN-14 半成品 | 原有未跟踪项，保留且不暂存 |
| `.tmp-*.log` | 本地 uvicorn/vite 日志 | gitignore，不入库 |
| `results/` | 评测 JSON 等 | 已 ignore，不删 |
| `中期答辩材料/` 及笔记 | 冻结历史；工作区或有旧 diff | **不 stage、不改正文** |

## 验证（历史，PLAN-14 半成品）

- 最近记录：`test_agent_contracts` + `test_agent_replay_harness` → 26 passed（须用 `backend/.venv`）；不代表生产运行时已完成。

## 下一步

1. 等用户决定是否下令开 M1；审阅必须改项已确认，不再安排重复计划审阅或前端视觉验收为阻塞。
2. 用户下令后先核对 PLAN-14 半成品真实证据，再按一次会话一个实现项补合同/Fake Harness，结合 PLAN-15 最小存储/课程教师权限与创建/单任务读取 API 交付 M1；本轮不整理或提交半成品。
3. M2 报告 API 按外发零调用/来源/空窗/E5-A 门禁验收，再开 M3 UI+PDF 回页+最小 lease/取消/显式恢复；PLAN-17 五件套仍必做，可并行盘点。
4. 开工前明确当前切片与隔离数据库测试范围；真实模型、问句外发、破坏性迁移仍须当次授权。禁止默认 DATABASE_URL/正式 cn_v2 迁移；不默认 push。

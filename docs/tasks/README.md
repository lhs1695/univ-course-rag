# 任务卡（docs/tasks）

结题施工的**可执行切片**放这里；路线图仍以 [implementation-plan.md](../implementation-plan.md) 的 PLAN-00～13 为准。

## 约定

1. 一卡一事；文件名建议 `PLAN-0x-短名.md` 或 `T-短名.md`。
2. 从 [`_template.md`](_template.md) 复制；验收标准必须可判定真假，并写明验证命令。
3. 长会话把目标/闸门/下一步写入 [`SESSION_STATE.md`](SESSION_STATE.md)，避免只活在聊天里。
4. 实现默认：小改由本仓 coding bot；其余 Codex CLI（见根 `AGENTS.md`）。**只本地 commit，用户点名才 push。**
5. 高成本动作（真实云调用、全量解析/重入库、大依赖/大模型下载、破坏性迁移）须当次授权，写进任务卡「须授权」栏。

## 与结题合同的关系

| 层级 | 文档 |
| --- | --- |
| 产品 | [结题产品定义与完工标准.md](../结题产品定义与完工标准.md) |
| 验收 | [validation.md](../validation.md) |
| 路线图 | [implementation-plan.md](../implementation-plan.md) |
| 本卡 | `docs/tasks/*.md`（开工与勾选） |

阶段 2 将由 Codex 把 PLAN 拆成具体任务卡；本目录阶段 1 先落模板与状态文件。

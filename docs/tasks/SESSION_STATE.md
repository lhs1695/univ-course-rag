# SESSION_STATE

会话外状态（长任务用）。更新：2026-10-22（Asia/Shanghai）。

## 当前目标

阶段 1：文档体系治理（`docs/INDEX.md`、瘦 `AGENTS.md`、`docs/tasks/` 骨架）→ 本地提交。  
下一阶段（待用户点头后）：Codex 按 PLAN-00～10 拆可勾选任务卡（阶段 2）。

## 已定架构 / 约束

- 唯一工作区：`D:\workspace\univ-course-rag`；后期跟 `main`
- 中期快照 tag：`midterm-freeze-2026-10-21`（`f8278d7`）
- 只本地 commit，不默认 push
- 少打断用户验收；Codex 额度可积极消耗；额度用尽停工
- 高成本（真实云调用 / 全量解析重入库 / 大依赖）仍须当次授权
- 不引入 LangChain/LlamaIndex 整体重构；不换掉 PostgreSQL+pgvector

## 验证门（未贴原始输出不得勾 done）

- 文档任务：内容与链接自检 + `git diff --check`
- 代码任务：任务卡写明的 pytest/ruff/build；禁止只靠「看起来能跑」

## 下一步命令 / 动作

1. 完成阶段 1 本地提交
2. 用户确认后开阶段 2：Codex 生成 `docs/tasks/PLAN-*.md` backlog

## 活跃 diff / 进行中文件

- 阶段 1 已落盘：`docs/INDEX.md`、`docs/tasks/*`、瘦身 `AGENTS.md`、交接/workflow 指针。

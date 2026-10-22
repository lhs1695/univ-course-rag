# SESSION_STATE

会话外状态（长任务用）。更新：2026-10-22（Asia/Shanghai）。

## 当前目标

**PLAN-00/01 done** → 下一步 **PLAN-02** → PLAN-03 → PLAN-04 → PLAN-05（本轮用户要求；可不插队 PLAN-07）。

## 已定架构 / 约束

- 工作区 `D:\workspace\univ-course-rag`；tag `midterm-freeze-2026-10-21`
- 只本地 commit；禁止默认 push
- 指标冻结：`docs/metrics-data-boundary.md`（`metrics-v1`）
- 复用决策：`docs/opensource-reuse-decisions.md`
- 真实模型预算：≤ 约 2 元人民币
- Codex：gpt-6.1-sol / gpt-6-luna，思考 high

## 验证门

- 文档：`git diff --check` + 链接自检
- 代码：卡上真实命令 + 原始输出

## 下一步

1. PLAN-02 生命周期与权限收口（对照代码补测试/小修）

## 活跃 diff

- PLAN-01 产物（提交后清空）
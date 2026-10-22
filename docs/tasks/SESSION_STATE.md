# SESSION_STATE

会话外状态（长任务用）。更新：2026-10-22（Asia/Shanghai）。

## 当前目标

**PLAN-00～02 done** → 下一步 **PLAN-03** → PLAN-04 → PLAN-05。

## 已定架构 / 约束

- 指标：`docs/metrics-data-boundary.md`（metrics-v1）
- 复用：`docs/opensource-reuse-decisions.md`
- 权限矩阵：`docs/lifecycle-permissions-matrix.md`
- 只本地 commit；真实模型预算 ≤ 约 2 元
- Document.retrieval_enabled 软停用；正式库需 Alembic 0012

## 下一步

1. PLAN-03 教师学情描述层/主题总览

## 活跃 diff

- （提交后清空）
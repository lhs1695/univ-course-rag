# PLAN-FE-01 · 前端全面翻新

| 项 | 内容 |
| --- | --- |
| 状态 | **已实现并本地提交**（2026-10-26）；未 push |
| 优先级 | 高于结题后端 PLAN-14～17；本卡完成后可恢复审计划 |
| Codex 提示词 | [`frontend/prompts/FE-refresh-v1.md`](../../frontend/prompts/FE-refresh-v1.md) |
| 模型 | gpt-6.1-sol / high；子代理 gpt-6-luna / high |
| 范围 | 登录 + 学生（学/问）+ 教师「册」+ 管理「衡」；同源 token；占位灰项 |
| 不做 | 假业务 API、GraphRAG/图谱装饰、Insights 大屏、改 backend、装气质主题 Skill |
| 验收 | 见提示词 §6；演示闭环契约保留 |

## 实现摘要

- 新增 `frontend/src/theme.css` / `theme.js`；`DESIGN-TOKENS.md`。
- 三角色壳层与登录/各视图换皮；学生学/问切换（默认学，`localStorage`）；教/管无切换器。
- 占位灰项：「课程调查」「学期 / 班级」。
- 未改 backend；未新增 npm 依赖。

## 验证

- `npm run build`：通过（调用方本机；Codex sandbox 曾 EPERM，由 bot 复验通过）。
- `node --test --test-isolation=none tests/*.test.mjs`：44/44 通过。
- 浏览器真实闭环：待用户本机 `npm run dev` 点验。

## 依赖与顺序

1. ~~提示词落档 → Codex 实现~~ **已完成**。
2. 用户本机验收 UI 后，再恢复结题计划审阅 / PLAN-14～17。

## 相关文档

- [结题已拍板规格.md](../结题已拍板规格.md)
- [SESSION_STATE.md](SESSION_STATE.md)
- [frontend/DESIGN-TOKENS.md](../../frontend/DESIGN-TOKENS.md)

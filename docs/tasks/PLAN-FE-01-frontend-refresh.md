# PLAN-FE-01 · 前端全面翻新

| 项 | 内容 |
| --- | --- |
| 状态 | 提示词已落档；**实现未开工**（待用户授权 Codex） |
| 优先级 | **高于**结题后端 PLAN-14～17 开工；用户要求先翻新前端 |
| Codex 提示词 | [`frontend/prompts/FE-refresh-v1.md`](../../frontend/prompts/FE-refresh-v1.md) |
| 模型建议 | gpt-6.1-sol / high |
| 范围 | 登录 + 学生（学/问）+ 教师「册」+ 管理「衡」；同源 token；占位灰项 |
| 不做 | 假业务 API、GraphRAG/图谱装饰、Insights 大屏、改 backend、装气质主题 Skill |
| 验收 | 见提示词 §6；演示闭环不断 |

## 依赖与顺序

1. 本卡提示词落档（本文件）→ 用户确认 → Codex 按 FE-refresh-v1 实现。
2. 前端翻新完成并验收后，再恢复结题计划审阅 / PLAN-14～17 实现。

## 相关文档

- [结题已拍板规格.md](../结题已拍板规格.md)（产品边界；本卡不实现 Agent/业务后端）
- [SESSION_STATE.md](SESSION_STATE.md)

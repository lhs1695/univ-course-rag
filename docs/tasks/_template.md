# TASK: <短标题>

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-0x（或无） |
| 状态 | draft / ready / doing / blocked / done |
| 须授权 | 无 / 列出（真实 LLM、重入库…） |

## 目标

- …

## 非目标（禁止顺手做）

- …

## 验收标准（可判定真假）

- [ ] …
- [ ] 命令：`backend/.venv/Scripts/python.exe -m pytest <path> -q` 通过（贴原始输出）
- [ ] （若 UI）`cd frontend; npm run build` 通过；关键路径点一次

## 约束

- 栈与版本：现有 FastAPI + Vue3 + pgvector；不引入第二套 RAG 框架
- …

## 禁止改动的路径

- `.env`、密钥与 Cookie/Session 明文
- 评测金标 / `**/expected-outputs/**`（若有）
- 用户未点名的大规模 `corpus/` 重解析产物
- …

## 相关上下文（指针）

- @docs/结题产品定义与完工标准.md §…
- @docs/validation.md §…
- @docs/implementation-plan.md PLAN-0x
- 代码示例：`…`

## 验证步骤（Agent 必须贴原始输出）

1. …
2. …

## 完成记录

- 提交：
- 验证摘要：
- 未做 / 风险：

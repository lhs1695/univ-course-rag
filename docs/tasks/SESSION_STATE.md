# SESSION_STATE

会话外状态（长任务用）。更新：2026-10-22（Asia/Shanghai）。

## 当前目标

阶段 1～2 文档骨架与任务卡已完成。
实现进度：**PLAN-00 done** → 下一步 **PLAN-01** → PLAN-02 →（用户本轮要求做到 PLAN-05；可不插队 PLAN-07）。

## 已定架构 / 约束

- 工作区 `D:\workspace\univ-course-rag`；tag `midterm-freeze-2026-10-21`
- 只本地 commit；禁止默认 push
- Codex：主 `gpt-6.1-sol` / 子 `gpt-6-luna`，思考 **high**
- 真实模型调用预算：总花费 ≤ 约 2 元人民币（本轮用户授权）
- 不换 pgvector；不上第二套 RAG；不默认全量 Vision/重入库

## 验证门

- 文档：`git diff --check` + 链接自检
- 代码：卡上真实命令 + 原始输出；人工/真实证据不可用 Fake 替代

## 下一步

1. PLAN-01 冻结结题指标与数据边界
2. 再 PLAN-02～05

## 活跃 diff

- PLAN-00 产物与索引/卡状态（提交后清空）
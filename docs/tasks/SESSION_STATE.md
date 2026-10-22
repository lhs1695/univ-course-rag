# SESSION_STATE

会话外状态（长任务用）。更新：2026-10-22（Asia/Shanghai）。

## 当前目标

阶段 1 完成；阶段 2 **任务卡已产出且经 bot 验收通过**（待本地提交）。  
下一步实现：默认 **PLAN-00 → PLAN-01 → PLAN-02 → PLAN-07**，再学情分析链；一次一卡。

## 计划验收结论（bot）

- 接受 backlog 建议顺序（检索回归 PLAN-07 提前到学情大段之前）。
- PLAN-11～13 暂缓合理。
- 各卡含非目标 / 须授权 / 禁改路径；PLAN-04/08 真实云调用未授权不得做。
- 卡内 `backend/tests/test_planNN_*.py` 为**拟路径**：开工须先核对/复用现有测试并改回真实命令，禁止空测刷绿。
- 未改业务代码；不默认 push。

## 已定架构 / 约束

- 工作区 `D:\workspace\univ-course-rag`；tag `midterm-freeze-2026-10-21`
- 只本地 commit；Codex 主/子思考 **high**
- 高成本须当次授权；不换 pgvector；不上第二套 RAG

## 验证门

- 文档：`git diff --check` + 链接自检
- 代码：卡上真实命令 + 原始输出；人工/真实证据不可用 Fake 替代

## 下一步

1. 开 PLAN-00（开源复用决策表）
2. 再 PLAN-01、PLAN-02

## 活跃 diff

- 无（提交后清空）

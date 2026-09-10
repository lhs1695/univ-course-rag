# 文档索引

给实施 Agent 和人看。会话不当记忆。

## 下一会话

先读 [`NEXT-SESSION.md`](NEXT-SESSION.md)。第一至五期技术线已收敛；第六期从资料质量可见性阶段开始，聚焦本机产品完善。阶段 25 仍等待外部试用。第五期结果见 [`plan-5.md`](plan-5.md) 与 [CI 工作流](../.github/workflows/ci.yml)。

## 权威顺序

冲突时以更具体的施工合同为准：

1. [`plan-6.md`](plan-6.md) — **第六期**当前合同（本机产品可解释性、数据边界与效果证据；阶段 38–42）
2. [`plan-5.md`](plan-5.md) — **第五期**已收敛（单机可运维性与失败边界；阶段 32–37）
3. [`plan-4.md`](plan-4.md) — **第四期**技术线已收敛（阶段 25 仍等待外部）
4. [`plan-3.md`](plan-3.md) — **第三期**已收敛（16–17 完成；18–19 仍按反馈触发）
5. [`plan-2.md`](plan-2.md) — **第二期**已冻结（主线 11–13；14–15 默认跳过）
6. [`plan.md`](plan.md) — **第一期**已冻结（阶段 0–10）
7. [`decisions/`](decisions/README.md) — 已拍板取舍（001–004）
8. [`intent.md`](intent.md) — 产品要什么 / 不做什么
9. [`tech-recommendations.md`](tech-recommendations.md) — **仅**检索失败分类

## 按需读

| 何时 | 文件 |
| --- | --- |
| 登录 / 前端 | `decisions/001-frontend-and-session.md` |
| 向量 API | `decisions/002-embedding.md` |
| 阶段 3–5 借鉴开源 | `decisions/003-rag-reference-repos.md` |
| 学情口径（阶段 9） | 第一期 `plan.md` §1 学情行 + 阶段 9；`intent.md` §2 |
| 第二期范围 / 语料 | [`plan-2.md`](plan-2.md)（已收敛；夹具进仓、真课件不进 git） |
| 第三期试用 / 答辩 | [`plan-3.md`](plan-3.md)（已收敛；18–19 仍按反馈触发） |
| 第四期中期交付 / 加固 | [`plan-4.md`](plan-4.md)（技术线阶段 20–24、26–31 已完成；阶段 25 等待外部） |
| 第五期单机可运维性 | [`plan-5.md`](plan-5.md)（阶段 32–37 已完成；CI 工作流已推送并成功完成） |
| 第六期本机产品完善 | [`plan-6.md`](plan-6.md)（计划已修订；下一阶段 38 为入库质量信号） |
| pgvector 查询证明 | [`pgvector-query-proof.md`](pgvector-query-proof.md)（精确 Top-K、索引选择、迁移与 EXPLAIN） |
| 入库恢复合同 | [`ingest-recovery.md`](ingest-recovery.md)（批次、心跳、租约、重试状态与限制） |
| 上传文件生命周期 | [`storage-lifecycle.md`](storage-lifecycle.md)（路径边界、补偿顺序、清理与日志） |
| 中期汇报版本 | [`midterm-notes.md`](midterm-notes.md)（tag、启动、门禁、限制与恢复） |
| 中期汇报材料 | [`midterm-presentation.pptx`](midterm-presentation.pptx) 与 [`midterm-script.md`](midterm-script.md)（10 页 PPT、5/10 分钟口播） |
| 试用课走位 | [`demo.md`](demo.md)（教师上传、学生问答、学情、删除后拒答） |
| 非开发者试用记录 | [`usability-test-template.md`](usability-test-template.md)（匿名任务结果、问题分类与阶段触发判断） |
| 怎么测（仓级） | 根目录 [`AGENTS.md`](../AGENTS.md)「怎么测」；不限第二期 |
| 检索失败口播 | [`tech-recommendations.md`](tech-recommendations.md)（阶段 17 走位对照） |

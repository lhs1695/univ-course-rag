# 当前交接

更新：2026-10-20（Asia/Shanghai）。以 `origin/main` 为准；勿把下文历史段落当作「正在施工」。

## 当前状态（冻结演示）

| 项 | 口径 |
| --- | --- |
| 正式演示库 | `univ_course_rag_cn_v2`：**4 课 / 27 份 PDF / 2,501 chunks**（线代、概率论与统计学、人力资源、教育学原理） |
| 课件目录 | `corpus/local/cn-replace-2026-10-18/rechunk/uploads_v2/`（私仓已跟踪；克隆侧设 `UPLOAD_DIR`） |
| PPT | **final-v5**（`build/midterm-presentation/output/final-v5.pptx` + handoff 副本）；**v4 已淘汰**，勿再当演示稿 |
| 彩排 | **PASS**（2026-10-19）；摘要见 [`midterm-handoff/evidence/REHEARSAL-STATUS.md`](../midterm-handoff/evidence/REHEARSAL-STATUS.md) |
| 队友材料 | [`midterm-handoff/`](../midterm-handoff/README.md) |
| 架构说明 | [`docs/architecture.md`](architecture.md) |
| 运行卡 | [`docs/midterm-demo-runbook.md`](midterm-demo-runbook.md) |
| 旧库 | `univ_course_rag` 已 DROP；历史英文四课 17/385（`r7b6_real`）**仅历史对照**，不作当前演示 |

默认配置（`.env.example` / docker-compose）已指向 `cn_v2`。演示前确认后端进程读到该库与 `UPLOAD_DIR`；指标为弱规则 / AI 预标，**不是**人工事实正确率。不默认启用 Vision / rerank。

## 建议下一项

中期材料已收口（文档、PPT v5、彩排、私人仓 handoff）。**产品下一阶段待用户定**（例如 Demo Reset、成本/资源专项、结题范围等）。未授权前不擅自开新工程卡、不重入库、不 push。

可选人工动作（非阻塞）：本机 Office 打开 final-v5 复核字体换行；把两位队友加成 GitHub collaborator。

## 已知限制（仍有效）

- 库内 `storage_path` 多为入库机绝对路径；他机打开引用 PDF 需设 `UPLOAD_DIR` 或重入库。
- 纯图/矢量页、图内字、部分公式控制字符：文字路径可入库但覆盖不全。
- 同名 PDF 须按 `course_id` 隔离。
- 勿把 Fake 索引、旧 R7 / R7B-7 的 17/385 数字冒充当前四课基线。

## 历史指针（压缩）

详细流水与旧授权项已不在此展开。施工历史见 [`implementation-plan.md`](implementation-plan.md)；评测登记见 [`evaluation-results.md`](evaluation-results.md)；R7B-L1…R9 证据多在 `corpus/local/`（gitignore）。staff F1–F20 见 [`archive/NOTES-F1-F20.md`](archive/NOTES-F1-F20.md)。

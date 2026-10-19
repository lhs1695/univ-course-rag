# 基于大模型与 RAG 的高校课程知识库智能问答系统

面向高校各类课程的有依据、可核对问答原型；开源组件适配，本机演示，结题争取小范围多人试用。

## 文档索引

| 文档 | 用途 |
| --- | --- |
| [新开题资料](新开题资料.md) | 研究方案与阶段成果 |
| [AGENTS](AGENTS.md) | 协作纪律与禁区 |
| [workflow](docs/workflow.md) | 环境、启动、测试与复用规则 |
| [implementation-plan](docs/implementation-plan.md) | 唯一施工顺序与 R7B 子项门槛 |
| [NEXT-SESSION](docs/NEXT-SESSION.md) | 最新状态与下一项 |
| [engineering](docs/engineering.md) | 现行代码合同与已接入组件 |
| [validation](docs/validation.md) | 验收方法与通过/失败门槛 |
| [evaluation-results](docs/evaluation-results.md) | 已跑数字与运行日志登记 |
| [中期演示运行卡](docs/midterm-demo-runbook.md) | 本机切库、启动、固定问句、故障降级与汇报口径 |
| [中期答辩队友包](midterm-handoff/README.md) | PPT v5、讲稿、彩排截图与口径说明（给答辩队友） |

## 当前现状（三行）

1. 产品骨架可用（权限、入库、dense、引用、反馈）；**当前正式演示库**为中文新四课 `univ_course_rag_cn_v2`：**4 / 27 / 2,501**（课 / PDF / chunks）。旧英文四课与 `r7b6_real` 的 17/385 仅作历史对照。
2. Docling 全量解析已停止；生产 PDF 使用 PyMuPDF + 页级质量门禁。演示未启用 rerank；答案评价未经独立人工复核。
3. **中期收口完成**：彩排 PASS、PPT **final-v5**、R9 刷新、runbook 已对齐 cn_v2。队友答辩材料见 [midterm-handoff](midterm-handoff/README.md)；运行卡见 [midterm-demo-runbook](docs/midterm-demo-runbook.md)。默认库与 `.env.example` 已指向 `univ_course_rag_cn_v2`；课件在 `corpus/local/cn-replace-2026-10-18/rechunk/uploads_v2/`（约 57MB / 27 PDF，私人仓已纳入）。勿把本机 `.env` 密钥提交进 Git。其余以 [NEXT-SESSION](docs/NEXT-SESSION.md) 为准。

## 中期课件位置

| 项 | 值 |
| --- | --- |
| 路径 | `corpus/local/cn-replace-2026-10-18/rechunk/uploads_v2/` |
| 规模 | 4 课 / 27 PDF / 约 57 MB |
| 课程 | 线性代数、概率论与统计学、人力资源管理、教育学原理 |
| 环境变量 | `UPLOAD_DIR` 指向上述目录；`DATABASE_URL` / `POSTGRES_DB` 使用 `univ_course_rag_cn_v2` |
| 说明 | 本机 DB 的 `storage_path` 为绝对路径；克隆后若需打开引用 PDF，保持该相对目录并设置 `UPLOAD_DIR`，或按需重入库。证据类其它 `corpus/local/` 内容仍被忽略。 |

## 运行入口

后端仅用 `backend/.venv`。数据库、迁移、seed、前后端启动见 [workflow](docs/workflow.md)。密钥在本机 `.env`，不进 Git；真实云调用须当次授权。CI 见 [.github/workflows/ci.yml](.github/workflows/ci.yml)。

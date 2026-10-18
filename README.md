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

## 当前现状（三行）

1. 产品骨架可用（权限、入库、dense/hybrid、引用、反馈）；四课真实基线已在隔离库建立：4 门课程、17 份 PDF、385 chunks。R7 单课结果是历史对照，不代替这份四课基线。
2. Docling 全量解析因线性代数公式页耗时过高已停止；生产 PDF 使用 PyMuPDF + 页级质量门禁（R7B-L1…L3、R7B-5、R7B-6B/6C、R7B-7 已完成）。不续跑旧 Docling 任务、不新增解析器依赖。当前答案评价未经独立人工复核；Hybrid 只完成检索对照，尚未证明相对 Dense 有增益。
3. **R8 与 P7-3 恢复子项均已通过，R9 冻结身份清单已生成；下一项是中期演示材料准备**。恢复与冻结证据在本机忽略区 `corpus/local/r9-recovery-2026-10-18/`。演示仍使用 `univ_course_rag_r7b6_real`；根 `.env` 可能指向旧库，启动必须按 [NEXT-SESSION](docs/NEXT-SESSION.md) 与 [workflow](docs/workflow.md) 进程级明确切库。其余进度以 [NEXT-SESSION](docs/NEXT-SESSION.md) 为准。

## 运行入口

后端仅用 `backend/.venv`。数据库、迁移、seed、前后端启动见 [workflow](docs/workflow.md)。密钥在本机 `.env`，不进 Git；真实云调用须当次授权。CI 见 [.github/workflows/ci.yml](.github/workflows/ci.yml)。

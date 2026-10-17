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

1. 产品骨架可用（权限、入库、dense/hybrid、引用、反馈）；R7 仅心理学单课有限纯文字对照，**不是四课中期基线**。
2. Docling 全量解析因线性代数公式页耗时过高已停止；**生产 PDF 默认已切回 PyMuPDF + 页级质量门禁**（R7B-L1…L3、R7B-5 通过）。不续跑旧 Docling 任务、不新增解析器依赖；下一项 R7B-6 受控入库须另授权。
3. 细节与阻碍以 [NEXT-SESSION](docs/NEXT-SESSION.md) 为准；施工步骤见 [轻量解析计划](docs/implementation-plan.md#r7b-lightweight-plan)，验收门槛见 [validation](docs/validation.md#r7b-parser-selection)。

## 运行入口

后端仅用 `backend/.venv`。数据库、迁移、seed、前后端启动见 [workflow](docs/workflow.md)。密钥在本机 `.env`，不进 Git；真实云调用须当次授权。CI 见 [.github/workflows/ci.yml](.github/workflows/ci.yml)。

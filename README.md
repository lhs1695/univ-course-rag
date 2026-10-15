# 基于大模型与 RAG 的高校课程知识库智能问答系统

面向高校各类课程，采用开源组件进行课程适配、系统开发和效果验证。当前为本机原型；中期本机演示，结题争取小范围多人试用。

## 从这里开始

- [研究方案与阶段成果](新开题资料.md)
- [当前施工计划](docs/implementation-plan.md)与[最新交接](docs/NEXT-SESSION.md)：下一项 R7，需资料与评测授权。
- [开发与运行工作流](docs/workflow.md)、[协作规则](AGENTS.md)

docs 只保留以下六份，不另设索引：

| 文档 | 用途 |
| --- | --- |
| [workflow](docs/workflow.md) | 开发、环境、测试与文档规则 |
| [implementation-plan](docs/implementation-plan.md) | 当前施工项、顺序与证明 |
| [NEXT-SESSION](docs/NEXT-SESSION.md) | 最新状态、阻碍与下一项 |
| [engineering](docs/engineering.md) | 开源选型、文件存储、入库恢复与日志留存 |
| [validation](docs/validation.md) | 评测设计、演示步骤、试用模板与基准运行 |
| [evaluation-results](docs/evaluation-results.md) | 新版评测登记、资料来源与待验状态 |

## 当前能力与边界

当前代码具备角色/课程授权、PDF/PPTX/DOCX/Markdown/纯文本入库、质量计数、失败重试、课程内向量检索、引用原资料入口、教师问句聚合及管理员到期日志预览/分批清理。前端 Vue 3 + Vite + Element Plus，后端 Python/FastAPI，业务与向量存储 PostgreSQL + pgvector；真实接口为 SiliconFlow BGE-M3 与 DeepSeek，测试使用 Fake。

默认检索仍是课程内向量检索。hybrid 可显式开启：先形成两路完整有界候选并集，再经保守余弦门槛选择证据；重排 API 适配默认关闭，只经 Fake/Mock 验证。关键词独有候选可接受重排，但高分不等于依据充分，当前仍不自动放行。结构切分直接复用组件，记录清洗后来源字符范围与版本；回答复用 markdown-it 安全显示 Markdown 和内联引用，证据卡展示模型实际看到的对应正文。当前不支持 OCR/vision、旧二进制 Office 或生产部署。引用合法不等于答案事实正确，抽取计数不是质量评分。

教师反馈已可按时间筛选，并显示 UTC 日计数、高频问句、待核对问句和需确认的候选组。候选分组默认关闭，阈值未校准，不在打开页面时外发问句；合成验证不能代替真实语义效果。反馈按最终结果、提问时角色和明确分母统计；旧日志保留未知，不表示人数或正确率。代码仍需迁移0011，真实目标库未核验，旧来源/日志不自动回填。默认dense、重排disabled不变；真实混合问答、事实支持仍未验收。下一实现项为 [R7](docs/implementation-plan.md)，需新的课程资料和评测授权。

## 运行与验证

后端仅使用 backend/.venv。数据库、迁移、seed、后端与前端启动见 [workflow](docs/workflow.md)。浏览器使用 Vite 地址，由代理访问后端。

真实模型配置由维护者在本机 .env 设置；不输出密钥、不提交真资料。Fake 与真实向量不能混用，换模型需匹配索引身份。实际云调用需当次明确联网与计费授权。CI 定义见 [.github/workflows/ci.yml](.github/workflows/ci.yml)，历史 CI 记录不代表当前工作区已重新验证。

## 效果与数据

中期汇报前以改进后的项目重新建立基线、入库和跑数据。旧阶段报告与汇总数字已清理，[evaluation-results](docs/evaluation-results.md) 仅登记新运行及资料来源，当前新版真实效果仍待验证。新对照设计与现有 CLI 限制见[验证指南](docs/validation.md#eval-protocol)。

提问默认留存 90 天，教师视图不显示身份；当前库清理不立即抹除外部备份。详见 [留存合同](docs/engineering.md#query-log-retention)。独立用户试用尚未完成，当前任务脚本见 [demo](docs/validation.md#demo)。

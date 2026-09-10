# univ-course-rag

高校课程知识库智能问答（个人大创项目）。Python / FastAPI / Vue 3 / PostgreSQL+pgvector / DeepSeek v4-flash 生成 / 硅基流动 BGE-M3 向量。

**先读 [`docs/INDEX.md`](docs/INDEX.md)。第一至五期技术主线和第六期 [`docs/plan-6.md`](docs/plan-6.md) 的阶段 38–42 已收敛；当前本机产品具备入库质量信号、受控重试、受鉴权引用追溯、提问日志留存维护和合成规模基线。阶段 25 的非开发者试用仍在等待，不能由开发者测试替代。**

当前进度：课务、PDF/PPTX/DOCX/Markdown/纯文本入库、本机真模型开关与真课件试用已落地；旧二进制 PPT/DOC 不支持。资料计数只反映抽取和切片结果，不是答案质量评分；引用只允许本课成员访问原文件，PDF 可尝试定位页码，其他格式不承诺页内定位。教师学情只聚合当前提问留存窗口内的数据，不展示学生身份；管理员可在“日志维护”先 dry-run 再分批删除到期记录。完整试用走位见 [`docs/demo.md`](docs/demo.md)。真课件与 API Key 不要进 git。

提问日志默认留存 90 天，可在 `.env` 通过 `QUERY_LOG_RETENTION_DAYS` 调整为 1–3650 天；单批清理默认 100 条，可通过 `QUERY_LOG_CLEANUP_BATCH_SIZE` 调整为 1–1000 条。清理仅作用于当前数据库，不能立即抹除外部备份或快照，详见 [`docs/query-log-retention.md`](docs/query-log-retention.md)。

阶段 41 的纯合成本机基准不调用云模型，命令、SQLite/pgvector 路径和不过度外推的判读规则见 [`docs/synthetic-benchmark.md`](docs/synthetic-benchmark.md)。当前基线只说明本机合成规模下的退化趋势，不能作为真实课程准确率或生产容量承诺。

开发期前端：`cd frontend && npm install && npm run dev`（Vite proxy 到 `127.0.0.1:8000`）。

密钥放本机 `.env`，不要提交、不要贴进聊天。

CI 工作流见 [`.github/workflows/ci.yml`](.github/workflows/ci.yml)：使用 FakeEmbedder/FakeLLM，运行 Ruff、全量 pytest、迁移后的 pgvector 检索证明和前端 lockfile 构建；不读取云 key 或本地语料。提交 `4b805e9` 的历史 CI 已成功完成；阶段 38–42 的当前工作尚未默认 push。

本项目仍定位为本机产品：不包含 OCR/vision、旧二进制 Office、定时任务平台、多 Agent、生产部署或法律合规认证。下一项外部工作是由未参与开发的人按 [`docs/usability-test-template.md`](docs/usability-test-template.md) 完成阶段 25 独立试用；开发者走位和自动化测试不能代替。

# univ-course-rag

高校课程知识库智能问答（个人大创项目）。Python / FastAPI / Vue 3 / PostgreSQL+pgvector / DeepSeek v4-flash 生成 / 硅基流动 BGE-M3 向量。

**先读 [`docs/INDEX.md`](docs/INDEX.md)。第一期 [`docs/plan.md`](docs/plan.md)、第二期 [`docs/plan-2.md`](docs/plan-2.md) 均已收敛。第三期草案 [`docs/plan-3.md`](docs/plan-3.md) 未立项。**

当前进度：教师可管本课学生与资料；入库覆盖 PDF / Markdown / 纯文本 / PPT·PPTX / Word（文本层）。真课件不要进 git。阶段 14、15 默认跳过。

开发期前端：`cd frontend && npm install && npm run dev`（Vite proxy 到 `127.0.0.1:8000`）。

密钥放本机 `.env`，不要提交、不要贴进聊天。

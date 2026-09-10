# univ-course-rag

高校课程知识库智能问答（个人大创项目）。Python / FastAPI / Vue 3 / PostgreSQL+pgvector / DeepSeek v4-flash 生成 / 硅基流动 BGE-M3 向量。

**先读 [`docs/INDEX.md`](docs/INDEX.md)。第一至四期技术主线已收敛，第五期以 [`docs/plan-5.md`](docs/plan-5.md) 为当前合同；阶段 32 已完成，下一阶段为 33。**

当前进度：课务、PDF/PPTX/DOCX/Markdown/纯文本入库、本机真模型开关与真课件试用已落地；旧二进制 PPT/DOC 不支持。中期版本见 [`docs/midterm-notes.md`](docs/midterm-notes.md)，汇报材料见 [`docs/midterm-presentation.pptx`](docs/midterm-presentation.pptx) 和 [`docs/midterm-script.md`](docs/midterm-script.md)，试用走位见 [`docs/demo.md`](docs/demo.md)。真课件与 API Key 不要进 git。

开发期前端：`cd frontend && npm install && npm run dev`（Vite proxy 到 `127.0.0.1:8000`）。

密钥放本机 `.env`，不要提交、不要贴进聊天。

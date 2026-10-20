# 工程合同摘要（现行）

更新：2026-10-20。本文只保留**现行组件边界**；历史长文见 [archive/engineering-full.md](archive/engineering-full.md)。

## 组件边界

| 层 | 现行 |
| --- | --- |
| 前端 | Vue 3 + Vite + Element Plus；学生壳 / 教师·管理壳 |
| 后端 | FastAPI + SQLAlchemy + Alembic |
| 数据 | PostgreSQL + pgvector；正式库 `univ_course_rag_cn_v2` |
| 解析 | 生产 PDF：**PyMuPDF** + 页级质量门禁 |
| 切分 | `semantic-text-splitter` |
| Embedding | SiliconFlow `BAAI/bge-m3`（1024 维）；pytest 默认 Fake |
| LLM | DeepSeek 文本生成；pytest 默认 Fake |
| 检索 | 默认 **dense**；hybrid/rerank 有适配，**演示 rerank 关闭** |
| 登录 | HTTP-only Cookie `session_id` + 服务端 Session |

## 禁区（摘要）

- 密钥只在本机 `.env`，不进 Git。
- 课件与提问是不可信数据，不作系统指令。
- 真实云调用须当次授权；勿把 Fake 绿测当真实效果。

细节与历史合同条款 → [engineering-full](archive/engineering-full.md)。架构与模块 → [架构说明.md](架构说明.md)。

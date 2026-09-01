# 003 RAG 借鉴哪些仓（调研清单，不进本仓库）

状态：已拍板（2026-09-01）  
原则：读设计与关键函数；**禁止** submodule / 整仓拷贝当本系统。对照克隆若需要，放在 `D:\workspace\_refs\`（本 git 外），`--depth 1` 即可。

本仓库要对齐的是 **Haystack 那种可单测的阶段**，不是 RAGFlow 的产品菜单。

---

## 主线：阶段 3–5 前读完「抄什么」列（阶段 0–2 可跳过）

### 1. infiniflow/ragflow

- 仓：https://github.com/infiniflow/ragflow
- 它是什么：完整 RAG 产品（解析、知识库、对话、引用、后来还有 Agent）。
- **抄什么**
  - 引用不要只靠模型自觉：生成后再把答案拆句，与 retrieved chunk 做相似度，回贴 `[ID:i]`。
  - 知识库与对话分离：检索命中的切片进 `{knowledge}`，和聊天记录不是同一张皮。
  - 课件/复杂 PDF 要重视切分，而不是一段 500 字切一切完事。
- **精读文件（网上即可，不必先 clone 全仓）**
  - [`rag/nlp/search.py`](https://github.com/infiniflow/ragflow/blob/main/rag/nlp/search.py) — `insert_citations`：分句、阈值从 0.63 降到 0.3、句向量与 chunk 向量 + 词面混合相似度。我们第一期可以做成「可选后处理」，20～80 行量级，不要搬它的 tokenizer 全家桶。
  - 对话拼知识库：`api/db/services/dialog_service.py` 里用检索结果填 prompt 占位符、chunk 之间分隔符的做法（文件会随版本挪，搜 `{knowledge}`）。
  - 前端如何把 `[ID:i]` 渲染成引用气泡：`web/src` 下 citation 正则（旧格式 `##i$$` 已淘汰）。
- **不抄**：Elasticsearch/Infinity 部署、它的账号权限、Agent canvas、整份前端。
- **对我们第一期的含义**：API 返回 `answer` + `citations: [{chunk_id, doc_id, page, snippet}]`；模型输出的页码若与 chunk 元数据冲突，以 chunk 为准。

### 2. deepset-ai/haystack（及官方教程，不必当运行时依赖）

- 仓：https://github.com/deepset-ai/haystack  
  教程：https://github.com/deepset-ai/haystack-tutorials/blob/main/tutorials/27_First_RAG_Pipeline.ipynb  
  文档：https://docs.haystack.deepset.ai/docs/pipelines
- 它是什么：显式 Pipeline（组件有输入输出名，`connect` 时校验类型）。
- **抄什么（架构纪律）**
  - 索引一条链、查询一条链：DocumentEmbedder ≠ Query Embedder，但 **必须同一模型**。
  - 每段可单独测：embedder / retriever / prompt / generator 失败能定位。
  - Retriever 只输出 Document 列表，LLM 看不到整库。
- **精读**
  - 上述 tutorial 27：`SentenceTransformersTextEmbedder` → Retriever → `PromptBuilder` → LLM。
  - 文档里 Pipeline 的四步：`add_component` → `connect` → `run` 传入的是**组件名到输入的字典**（避免隐式全局状态）。
- **不抄**：把本应用写成 Haystack YAML；Agent 循环、websearch fallback 教程（与 intent 非目标冲突）。
- **对我们第一期的含义**：目录按 `ingest / retrieve / generate / citations` 分模块，pytest 按模块红绿，而不是一个 `rag.py` 三千行。

### 3. LlamaIndex CitationQueryEngine（示例级，不引入包当后端）

- 文档：https://developers.llamaindex.ai/python/examples/workflow/citation_query_engine/
- **抄什么**：召回后再把节点改写成 `Source 1: ...` 塞进 prompt；生成模板禁止引用未出现的编号。
- **不抄**：`VectorStoreIndex` + 默认 Ingestion 当 FastAPI 本体。
- **对我们第一期的含义**：prompt 里枚举本次检索到的 id 列表，后处理丢掉不在列表里的引用（比 RAGFlow 的句级回贴更简单，作为 **v1 必做**；句级回贴作为 v1.1）。

---

## 辅线：第二期或对照产品，现在只登记

| 对象 | 何时读 | 抄什么 | 不抄 |
| --- | --- | --- | --- |
| [opendatalab/MinerU](https://github.com/opendatalab/MinerU) | 扫描件/双栏课件解析失败成为主因之后 | 版面解析思路、评测自己的 PDF | 第一期核心路径绑 GPU |
| [FlagOpen/FlagEmbedding](https://github.com/FlagOpen/FlagEmbedding) | 上本机 BGE-M3 或要 sparse 向量时 | `BGEM3FlagModel.encode` 的 dense/sparse 开关 | 把它的训练代码进业务仓 |
| FastGPT / QAnything | 做教师端「知识库」UX 对照 | 按文档可见、引用列表怎么摆 | 二次开发它们的全栈 |
| GraphRAG / LangGraph | 不读当主线 | — | 与「单次检索 + 单次生成」冲突 |

---

## 建议的阅读顺序（仍属讨论/探路，不改本仓业务代码）

1. Haystack tutorial 27（建立阶段心智，1h）。  
2. LlamaIndex citation 示例的 prompt 形态（30min）。  
3. RAGFlow `insert_citations` 通读一遍，决定 v1 是否只做「引用集合校验」、把句级回贴标成后续（1h）。  
4. 需要本机 M3 时再看 FlagEmbedding README。  
5. 解析翻车再开 MinerU 探路会话（单独分支，结论进新 intent，禁止探路 diff 进功能分支）。

---

## 准备动作（现在做这些就算「准备好」，不是开工）

- [x] 本决策写清抄与不抄、精读路径。  
- [ ] （可选）`mkdir D:\workspace\_refs` 后浅克隆 ragflow / haystack-tutorials，**不要**放进 `univ-course-rag`。  
- [ ] 实施 RAG 的那次会话：把本文件和黄金题一起放进上下文。  
- [ ] 禁止：为了「借鉴」把 RAGFlow 的 docker-compose 当本项目启动方式。

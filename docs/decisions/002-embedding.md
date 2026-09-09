# 002 Embedding：云厂商与模型

状态：已拍板（2026-09-01，云 API 选定硅基流动）  
相关事实：DeepSeek API **没有** `/embeddings`；v4-flash 只负责生成。

## 结论（先读这段）

走 **云 embedding**。厂商锁定 **硅基流动（SiliconFlow）**，模型锁定 **`BAAI/bge-m3`**（1024 维，单条最长 8192 token）。

代码仍做成 `embed(texts) -> list[vector]` 接口 + FakeEmbedder 单测，避免业务代码写死 SDK 细节。库表记下 `embedding_model`；换模型必须整库重灌，禁止混维。

| 角色 | 选择 | 不要当默认 |
| --- | --- | --- |
| **主路径** | 硅基流动 + `BAAI/bge-m3`，`https://api.siliconflow.cn/v1` | OpenAI embedding（国内不稳定、贵） |
| **备选（仅报销/发票逼你用大厂时）** | 阿里云百炼 `text-embedding-v3`（默认也是 1024 维，但向量空间不同，要重灌） | 智谱、Jina、Cohere（多一家账号没有收益） |
| **本机** | 不再作为开发默认；仅当云挂了、要离线灌库时再开 BGE-M3 本机 | 本机 7B；英文 MiniLM 灌中文课件 |

## 为什么是硅基流动，不是阿里/智谱/OpenAI

- **接口**：OpenAI 兼容 `/v1/embeddings`，和 DeepSeek 一样用官方 `openai` 客户端，只换 `base_url` 和 key。
- **模型**：`BAAI/bge-m3` 就是中文 RAG 最常见的开源向量模型，文档长窗口 8192，维度 1024 固定；同一家还提供 Qwen3-Embedding，以后要升再评估，**第一期不要用 8B**（贵、慢、过杀）。
- **网络与成本**：大陆走 `api.siliconflow.cn`；BGE 档在该平台长期是低价/免费档（额度以控制台为准，可能有 TPM 限流）。阿里百炼按 token 计费、免费包有 90 天期限，学校要发票时再换。智谱 `embedding-3` 是 2048 维，多一家账号且 SDK 不统一。
- **不要用硅基流动国际域名当默认**：文档里的 `api.siliconflow.com` 给境外；你这边用 **`.cn`**。

平台可能对模型上下架发公告。锁定的是「OpenAI 兼容 + BGE-M3 + 1024 维」；若 `BAAI/bge-m3` 下线，再评估同维度替代，而不是默默改成 Qwen3 却不重灌。

## 本机（仅灾备，不是默认）

云挂了才考虑 CPU 版 PyTorch + 本机 `BAAI/bge-m3`（约 2.3GB）。单测永远用 FakeEmbedder，不打真实 API。

默认 schema 按 **1024 维** 写。

## 硅基流动怎么配

免费档、限流以官网当时规则为准，注册后看一眼控制台。

1. 打开 [siliconflow.cn](https://siliconflow.cn) / [cloud.siliconflow.cn](https://cloud.siliconflow.cn) 注册。
2. 控制台创建 API Key（只出现一次，当密码）。
3. 本机 `.env`（不进 git）。运行时开关是 **`EMBEDDER_BACKEND`**（见 `app/config.py`），不是下文曾用过的 `EMBEDDING_PROVIDER`：

```
EMBEDDER_BACKEND=siliconflow
SILICONFLOW_API_KEY=sk-...
EMBEDDING_MODEL=BAAI/bge-m3
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
```

4. 开通后用 curl 自检（key 自行替换）：

```bash
curl https://api.siliconflow.cn/v1/embeddings ^
  -H "Authorization: Bearer sk-..." ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"BAAI/bge-m3\",\"input\":\"课程知识库测试\"}"
```

成功则 `data[0].embedding` 长度为 1024。不要给 bge-m3 传 `dimensions` 参数（该模型不支持，会 400）。

5. 代码侧用 `openai` 官方客户端：`OpenAI(api_key=..., base_url="https://api.siliconflow.cn/v1").embeddings.create(...)`。

换到阿里/智谱必须换适配器并**整库重灌**。业务代码只依赖 Embedder 接口。

## 和检索决策的关系

召回差时：先确认切分/课程过滤/关键词，再考虑硅基流动上的 Qwen3-Embedding 或加 rerank；不要先换 DeepSeek 型号。见 `003` 与 `tech-recommendations.md` 失败分类。

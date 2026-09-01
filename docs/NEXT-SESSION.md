# 下一会话

工作区：`D:\workspace\univ-course-rag`。会话记录不当记忆。

## 第二期交接（已收敛）

```
第二期：
做了：阶段 11 教师本课学生+删资料；12 PPT/PPTX 入库；13 Word 入库；golden 追加 PPT+Word，未改坏 MD+PDF。
没做：阶段 14 句级引用（默认跳过）；阶段 15 worker（未触发跳过）；CAS、Celery、OCR/vision、LangChain/RAGFlow。
怎么验：仓级以根目录 AGENTS.md 为准。二期证明点已分别在 11–13 会话跑过对应 pytest；不要为收尾默认全量。
```

## 下一会话不要做什么

- 不要实施阶段 14、15，除非引用观感或解析超时成为真实痛点，并先改 `plan-2.md` / 立项 `plan-3.md`。
- 不要把 [`plan-3.md`](plan-3.md) 当合同去写代码：该文是**未立项草案**。
- 不要重开 Cookie session、pgvector、FakeEmbedder/FakeLLM 默认 pytest、无 LangChain/RAGFlow 骨架。

若要开第三期：先拍板 `plan-3.md`（很少几条带证明的阶段），再改 `AGENTS.md` 当前合同指针，然后一次会话只做一个阶段。

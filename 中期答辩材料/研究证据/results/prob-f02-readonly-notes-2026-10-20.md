# PROB-F02 只读诊断笔记（2026-10-20 Asia/Shanghai）

基于已落盘 `manual-verify-2026-10-20-*.json` 与 cn_v2 库只读查询。**无新增云调用、不重入库**。根因猜测不得写成结论。

## 题目与机器结果（原记录）

- 问句：概率论与统计学导论课件目录中，第一章包含哪些主要小节？
- 期望文档：`01-prob.pdf`；期望页：`[2]`；要点：四节目录标题。
- Dense / Hybrid：**`status=no_evidence`**，`answer=""`，`citations=[]`，`error=null`，`system_error` 计数为 0。
- 两侧均有非空 `retrieval_hit_documents` / `retrieval_hit_pages`（含 `01-prob.pdf` 与页码集合中的 `2` 等）。

## 库内只读事实

- 课程「概率论与统计学」下 `01-prob.pdf` 有 48 个 chunks；页字段范围约 1–55。
- **含完整四节目录标题 + `CONTENTS` 的块**：
  - `page=3`，`unit_index_start=2`，`unit_index_end=3`（合并 PDF#2–#3）；
  - 以及后续重复目录块（如 page=12/21/47，同样为两页合并）。
- PDF 阅读器 **#2** 确为目录页（四节标题）；**#3** 起为「步骤1…」正文。题集期望页 2 与阅读器目录页一致。
- 因合并，**不存在**单独的 `Chunk.page==2` 专块；目录文本挂在 `page=3`（末页）等块上。

## 现有评测 JSON 能证明什么

1. 检索阶段**并非**空召回：最终 evidence 列表对应的文档/页聚合非空（见 `retrieval_hit_*`）。
2. 生成阶段结果被记为 **`no_evidence`**（空回答、无引用）；与 `system_error` 不同。
3. 开发者核验：`fact_ok/citation_supports/page_ok=fail`，`no_hallucination=pass`（未编造）。
4. Hybrid 候选层统计存在（keyword_only 等），且 keyword-only **未**进入最终 evidence（与全局门控一致）。

## 现有记录不能证明什么

1. **不能**指出最终 Top-k evidence 里是否包含「目录合并块」(page=3)：旧 runner 只存了聚合的文档名/页码，**没有**逐条 chunk_id/分数/截断文本配对。
2. **不能**区分生成侧细分状态：旧结果无法分辨「模型输出字面 `NO_EVIDENCE`」vs「空串」vs「有文但无合法引用」——三者都落成同一 `status=no_evidence`。
3. **不能**仅凭「hit_pages 含 2」断言命中了 PDF#2 目录：聚合页码可能来自**其他文档**的 page=2；缺配对记录。
4. **不能**把根因断定为「阈值过严 / 合并丢目录 / 模型拒答 / prompt」中的某一个；以上均为**假说**，需新诊断字段或受控单题复跑才能检验。

## 后续工具改进（本轮代码，不重跑 22×2）

评测 runner 将保存：

- `retrieval_hits[]`：文档名、页码、chunk_id、分数、截断片段（配对）；
- `generation_status`：`answered` / `no_evidence_marker` / `empty_output` / `no_valid_citations` / `no_retrieval_hits` / `system_error`；
- Hybrid：`retrieval_ms` 与 `diagnosis_ms` 分离，避免诊断重复检索污染耗时对比。

在未用新字段复跑前，**PROB-F02 对外口径**仍是：应答题依据不足（机器），原因未定位。

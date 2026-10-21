# COVERAGE_INCOMPLETE 现状（只读核实）

更新：2026-10-20（Asia/Shanghai）  
库：`univ_course_rag_cn_v2`（只读 SQL）；页级离线重算：本机 PyMuPDF + `build_native_pdf_quality_report`（**未写库、未重入库**）。

## 1. 库内汇总（可复核）

| 指标 | 数值 |
| --- | ---: |
| 资料总数 | 27 |
| `quality_warning = COVERAGE_INCOMPLETE` | **20** |
| `quality_warning` 为空 | **7** |
| 其他警告 | 0 |
| chunks | 2,501 |

### 分课

| 课程 | 资料数 | COVERAGE_INCOMPLETE |
| --- | ---: | ---: |
| 线性代数 | 1 | 1 |
| 概率论与统计学 | 12 | 11（仅 `07-prob.pdf` 无警告） |
| 人力资源管理 | 8 | 8 |
| 教育学原理 | 6 | **0** |

## 2. 警告如何产生（代码）

1. 入库调用 `parse_document_with_quality`（`ingest.py`）。
2. 原生 PDF：`build_native_pdf_quality_report`（`parse_quality.py`）：
   - 空页 → empty；
   - 非空但 `len(strip)<50` → **sparse**；
   - 含异常控制字符 → **abnormal_characters**；
   - 任一页带上述 notes → 该页 `PARTIAL`；任一 PARTIAL 页 → 文档 `status=PARTIAL`。
3. `document.quality_warning = COVERAGE_INCOMPLETE` **当且仅当** `quality.status is PARTIAL`。
4. **documents 表不保存** empty/sparse 页号列表；chunk `source_metadata` 仅有 parser/hash 等，**无页级 sparse 标记**。

因此：**20/27 是「至少一页被标为覆盖异常」的信号，不是 20 份入库失败。** 例如仅末页 sparse 也会整份打上警告。

## 3. 离线重算抽样（与库警告一致性抽查）

| 文件 | 页数 | 离线 status | empty | sparse | abnormal | 与库警告 |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| `01-linear-algebra-full.pdf` | 695 | partial | 0 | 58 | 47 | 一致（有警告） |
| `01-prob.pdf` | 55 | partial | 0 | 1 | 0 | 一致（末页 sparse 即可触发） |
| `07-prob.pdf` | 133 | succeeded | 0 | 0 | 0 | 一致（无警告） |
| `12-prob.pdf` | 25 | partial | 0 | 1 | 0 | 一致 |
| `01-L1-3-HRM概论.pdf` | 99 | partial | 5 | 20 | 0 | 一致 |
| `02-L10-11-绩效管理.pdf` | 85 | partial | 0 | 24 | 0 | 一致 |
| `01-edu.pdf` / `02-edu.pdf` | 6 / 14 | succeeded | 0 | 0 | 0 | 一致（教育学 6 份均无警告） |

演示相关页对照（原页文字 vs 抽取）：见下节；**公式页可抽取但版式/控制字符可能异常**，不代表问答一定失败（LA-01 彩排仍 PASS）。

## 4. 演示相关代表页（原文对照摘要）

| 场景 | 文件页 | 抽取观察 | 对问答影响 |
| --- | --- | --- | --- |
| 引用演示 LA-01 | `01-linear-algebra-full.pdf` p.9 | 两类对象文字清晰 | 彩排可答可引用 |
| 公式/线性函数 | 同文件 p.10–11 | 公式碎片化；p.11 离线计为 abnormal | 术语问答仍可能命中；不宜宣称公式理解完备 |
| 向量长度定义 | 同文件 p.30 | 根号/上下标线性化 | 可作人工核验题，需对照原 PDF |
| 概率定义 | `02-prob.pdf` p.3 | 定义文字完整 | 适合课内事实题 |
| HR 目录/框架 | HR 概论 p.5、绩效 p.2–3 | 文字少但可读；多页 sparse | 框架类问题可用；扫描感页面需人工看原件 |
| 教育学绪论 | `01-edu.pdf` p.1–3 | 长文本完整，无 COVERAGE | 适合事实/跨段题 |

## 5. 产品提示建议（有依据部分）

- **可做**：教师资料列表在 `quality_warning=COVERAGE_INCOMPLETE` 时显示「部分页面需核对」+ 固定说明「空页/稀疏文字页/异常字符等触发，不等于整份失败」。
- **不可做**：在 DB 无页级字段时，于 UI **编造**具体页码或质量分；放宽门禁以消警告；为消警告全量重入库。

## 6. 本轮是否改解析代码？

**否。** 规则行为与警告计数一致，属可解释信号；未见「错误标记导致演示失败」的已确认缺陷。解析改动留待有明确缺陷 + 小范围验证时再做。

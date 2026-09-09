# Plan：univ-course-rag 第二期

状态：主线 **11–13 已落地**（第二期收敛）；阶段 **14、15 默认跳过**（未做 / 未触发）  
日期：2026-09-01  
对照：第一期 `plan.md` 已收敛；语料原则见 [004](decisions/004-venv-corpus-vision.md)。栈与权限不重开（Cookie session、Postgres+pgvector、FakeEmbedder/FakeLLM 默认 pytest、无 LangChain/RAGFlow 骨架）

**施工纪律：** 一次会话只做下面某一个阶段；课件/提问当不可信文本；密钥只在本机 `.env`。怎么测以根目录 `AGENTS.md` 为准（仓级，不限本期）。偏离则同一批改动更新本文。

主线只做 **11 → 12 → 13**。阶段 14、15 **默认跳过**（交接里写「未做 / 未触发」），除非引用观感或解析超时成为真实痛点。

---

## 0. 第一期已冻结（第二期不要推翻）

- 登录：HTTP-only Cookie，不要 JWT / `localStorage` token
- 学情：只展示问句与次数/时间，**不展示学生标识**，无「学得差」、无点名、无去重人数列
- 检索/问答按课过滤；无命中则 `NO_EVIDENCE`，不拿模型常识顶课内事实
- seed：`python -m app`；依赖：`backend/.venv`
- 教师加本课学生的 **API 已有**（`POST/DELETE /courses/{id}/members`）；第一期 UI 只做了管理员绑课。阶段 11 补教师侧，不新开一套成员模型

---

## 0.1 语料（写进合同，不单独立项）

开发和 pytest：**仓库内自写短夹具**，每份含一句独有口令；PPT/Word 必须能抽出文本（键入后导出，不要截图拼页）。损坏文件另备，用来验 job failed、无幽灵 chunk。`golden.json` 只追加，不改坏已有 MD+PDF 三条。

答辩用真课件：**教师在页面上传**，不进 git。本机可放 gitignore 目录（例如 `corpus/local/`）。不要把教材扫描件、学生作业、完整讲义推进仓库。优先可选中文字的 PDF / 正文 PPTX / docx。全图页、扫描件表现为「库里没有」或正文极短，用来讲失败分类，第一期已禁止的 OCR/vision 第二期仍不做。

禁止：网上随便抓一套公开课当知识库；夹具用受版权保护的教材。

---

## 1. 第二期目标

让教师不切管理员也能走完课务闭环，并用**可抽文本的真实课件**入库：

1. 本课加/删学生（接已有成员 API）；资料能删，删完问答变拒答
2. 入库覆盖 **PPT/PPTX**，再覆盖 **Word**（解析失败可见，无幽灵切片）
3. 句级引用、独立 worker 不挡 1–2

不做：CAS、多租户、Celery 预装、知识图谱、成绩预测、小程序、OCR/vision。

---

## 2. 分阶段（每阶段 = 一次实施会话）

### 阶段 11 — 教师：本课学生 + 删资料

- **做：** 教师在本课管理学生（列出本课学生成员；添加已有学生账号；移出学生）。资料页删除（确认后调已有 `DELETE /courses/{id}/documents/{document_id}`）；学生看不见删除与成员管理。不把学情里的提问归因到人。加入学生仍走已有 `POST /courses/{id}/members`：可继续传 `user_id`，教师页用学生用户名（账号）。
- **不做：** 批量删除资料、回收站、改文件名；创建新用户（仍仅 admin）；改教师成员；管理员改密/删账号。
- **证明：** pytest：学生调删除资料或改成员仍 403；教师不能改他课成员（第一期已有则保持绿）；教师按用户名加入后该生 `GET /courses` 能看见。浏览器（若改 UI）：教师本课学生页加入一次、资料页确认删除一次即可。删后拒答以已有 `test_ask_after_document_deleted` 为准，不必再问黄金题。

### 阶段 12 — PPT/PPTX 入库

- **做：** 教师可上传 `.ppt`/`.pptx`；解析抽文本（成熟库，不自研排版引擎）；走现有切分/embedding/job 状态。失败原因教师可见；失败无 chunk。上传区允许 ppt。夹具 + golden 追加至少 1 条 PPT 口令题。
- **不做：** 抽图、vision、动画/母版还原、扫描件 OCR。
- **证明：** pytest（`test_ingest` 及本阶段新增用例）：夹具 pptx 含独有口令，job 成功且 chunk 带该课 `course_id`；损坏 pptx → failed 且无 chunk。仍 FakeEmbedder。不改坏已有 MD+PDF 黄金题。浏览器仅当上传区改了 accept：教师选一次 pptx、看见成功或失败标签即可，不必再问黄金题。

### 阶段 13 — Word 入库

- **做：** `.doc`/`.docx` 同上（文本层）。与 PDF/MD/PPT 同一 `documents` + `ingest_jobs` 管道，不另起一套知识库。golden 再追加至少 1 条 Word 来源。
- **不做：** 复杂域/修订追踪当产品功能；宏。
- **证明：** pytest：夹具 docx 独有口令可检索命中；坏文件 failed 无幽灵。不改坏已有黄金题。浏览器同阶段 12：只点新上传类型一次。

### 阶段 14 — 句级引用（默认跳过）

- **做：** 仅当答辩/试用明确觉得「整段引用对不齐」时再开。在现有 Source id ⊆ 检索集之上按句贴引用；对不齐则降级，不编页码。不搬 RAGFlow tokenizer。
- **不做：** 多轮 Agent、thinking 默认开。
- **证明：** 若实施：FakeLLM 可对齐句时引用带页或切片；无 key pytest 绿。未实施则交接写「默认跳过」。

### 阶段 15 — 大文件 worker（默认跳过）

- **做：** 仅当单文件解析**经常**超过约 60s 时再拆 worker（任务表已有）。
- **不做：** Celery 集群、K8s。未触发则交接写「未触发，跳过」。

---

## 3. 明确仍不进仓

校园网部署、邀请码/CAS、用户改删（账号）、系统监控大盘、多租户 SaaS、OCR/vision、MinerU 当骨架、换 Qwen3-Embedding、Fine-tune DeepSeek。

管理员改密/删用户若以后需要，见 [`plan-3.md`](plan-3.md) 阶段 19（默认跳过），不塞进 11–13。

---

## 4. 开工顺序

**11 → 12 → 13**。不要一次做完 PPT+Word。14、15 默认不做。

第二期已收敛。第三期合同是 [`plan-3.md`](plan-3.md)（试用与答辩），不要在本文续写 16。

---

## 5. 第二期核对（收敛时用）

- [x] 教师本课加/删学生（已有 members API）；学生改成员/删资料 403
- [x] 资料可删；删后问答拒答沿用第一期 `test_ask_after_document_deleted`
- [x] PPT/PPTX 入库；损坏文件 job failed、无幽灵 chunk
- [x] Word 入库；损坏文件 job failed、无幽灵 chunk；与 PDF/MD/PPT 同一管道
- [x] `golden.json` 追加 PPT + Word 口令题；未改坏第一期 MD+PDF 三条
- [x] 阶段 14 句级引用：默认跳过（试用未出现「整段对不齐」痛点）
- [x] 阶段 15 独立 worker：未触发跳过（解析未经常超过约 60s）
- [x] 无 LangChain/RAGFlow 运行时依赖；无 OCR/vision；无 CAS；无 Celery 预装


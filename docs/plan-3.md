# Plan：univ-course-rag 第三期

状态：已立项；主线 **中期汇报与试用**；阶段 16、16.5 已完成；阶段 17 走位文档已完成，待维护者浏览器实走
日期：2026-09-01  
对照：第一期 `plan.md`、第二期 `plan-2.md` 已收敛。栈不重开（Cookie session、Postgres+pgvector、**pytest 默认 FakeEmbedder/FakeLLM**、无 LangChain/RAGFlow 骨架）

**施工纪律：** 一次会话只做下面某一个阶段；课件/提问当不可信文本；**两个云 key 只写本机 `.env`，不进 git、不进普通日志、不贴进聊天。** 怎么测以根目录 `AGENTS.md` 为准。偏离则同一批改动更新本文。

主线 **16（已完成）→ 16.5（已完成）→ 17**。阶段 **18** 仅当试用发现失败原因完全读不懂时再做。管理员改密、句级引用、独立 worker **默认不做**（未触发则交接写「未做 / 未触发」）。

---

## 0. 前两期已冻结（第三期不要推翻）

- 教师可管本课学生与资料；入库：PDF / MD / 纯文本 / PPT·PPTX / Word（文本层）
- 问答按课过滤；无命中 `NO_EVIDENCE`；学情两表、不展示学生标识
- `golden.json` 只追加，不改坏已有题；夹具进仓，真课件不进 git（`corpus/local/` 已 gitignore）
- 阶段 14、15 仍默认跳过，除非试用中出现「整段引用对不齐」或解析经常超过约 60s

---

## 1. 第三期目标

让老师/评委在本机 **像用产品一样走完一课**，而不是再堆 RAG 功能：

1. 演示用 **真向量 + 真生成**（硅基流动 BGE-M3 + DeepSeek v4-flash）；pytest 仍 fake、无 key 也必须绿
2. 一门试用课：页面上传可抽文本的真课件 → 学生提问能看到出处 → 学情有问句 → 删资料后拒答
3. 能口头讲清失败分类（没解析 / 没切好 / 没召回 / 召回了没用上），不靠 OCR 假装抽到图里的字
4. 中期检查前保留一个可复现的 Git 汇报基线，后续开发不覆盖当时可运行状态

不做：CAS、多租户、Celery、知识图谱、成绩预测、小程序、换 embedding、Fine-tune。

---

## 1.1 两个 key（写进合同）

本机 `.env`（可从 `.env.example` 复制后改，**不要把填好的 `.env` 提交**）：

| 用途 | 变量 | 演示取值 | pytest |
| --- | --- | --- | --- |
| 向量 | `SILICONFLOW_API_KEY` | 硅基流动 key | 不需要 |
| 向量开关 | `EMBEDDER_BACKEND` | `siliconflow` | 默认 `fake`（测试夹具覆盖） |
| 生成 | `DEEPSEEK_API_KEY` | DeepSeek key | 不需要 |
| 生成开关 | `LLM_BACKEND` | `deepseek` | 默认 `fake` |

改完 **重启** `uvicorn` 才会读到。key 由维护者自己粘贴进 `.env`；对话里只确认「已写入本机」，禁止把 key 正文发给 Agent。

---

## 2. 分阶段（每阶段 = 一次实施会话）

### 阶段 16 — 本机真模型演示开关（已完成）

- **做：** 核对（必要时只补缺口）`AGENTS.md` / `.env.example`：如何填两个 key、如何切 `siliconflow`/`deepseek`、如何重启后端、pytest 为何仍 fake。立项时这两处已有演示段，**不要整篇重写**。核对 `app/config.py` 字段与示例变量名一致；代码已有「`EMBEDDER_BACKEND=siliconflow` 且 key 非空才走云、否则 fake」（`llm.py` 对 DeepSeek 同理）；不要新开一套客户端。不要把 key 写入仓库或示例里的真值。**不要新建 `docs/demo.md`**（走位长文是阶段 17）。
- **不做：** 改黄金题；接第三个云厂商；把默认 pytest 改成打真 API。
- **证明：** `.env.example` 与 `AGENTS.md` 演示段变量名与 `app/config.py` 一致；仓库内无真实 key。若改了 Python，只跑直接改到的测试 + 仓库根 `python -m ruff check`。浏览器：不测黄金题；维护者本机填 key 后重启，以一次真实问答为准（Agent 不得在聊天里索要 key）。

### 阶段 16.5 — 中期汇报 Git 基线（已完成）

- **做：** 先审计当前 `git status` / diff，把已有改动按第三期立项与阶段 16 等真实主题整理成可读提交；不得用 reset/checkout 丢弃不明改动。新增 `docs/midterm-notes.md`，记录汇报基线的 commit/tag、启动方式、已完成功能、Fake/真模型模式、演示前准备、已知限制与恢复方式；叙事定位为校园大创个人项目，不写成面试项目。确保 `.env`、真实 key、`corpus/local/` 真课件、上传文件、数据库数据、`.venv`、`node_modules` 不进版本。发布门禁通过且工作区干净后，在当前确认过的提交创建本地带注释 tag **`v0.3.0-midterm`**；后续开发从该提交继续，汇报时可按 tag 复现。远端 push（含 tag）只有维护者明确要求时才做。
- **不做：** 不改业务功能、不提前写阶段 17 的 `docs/demo.md`、不制作汇报 PPT、不调用真实云 API、不重写 Git 历史、不为了快照新增长期分支。
- **证明：** 在 `backend/.venv` 环境按仓库门禁运行 `pytest backend/tests/test_health.py backend/tests/test_auth.py backend/tests/test_courses.py backend/tests/test_ingest.py backend/tests/test_retrieve.py backend/tests/test_ask.py backend/tests/test_insights.py` 与仓库根 `python -m ruff check`，前端运行 `npm run build`；记录命令和结果但不记录密钥。`git status --short` 为空；`git show v0.3.0-midterm` 指向验收提交；检查该 tag 的文件树不含 `.env`、`corpus/local/`、上传数据或其他敏感内容。浏览器与真实问答留到阶段 17。

### 阶段 17 — 试用课走位（走位文档已完成，浏览器待实走）

- **做：** 书面走位（建议 `docs/demo.md`）：教师登录 → 本课上传 1–3 份**可抽文本**的真 PPT/PDF（文件放 `corpus/local/`，不进 git）→ 学生用 Vite 地址提问（命中则有出处）→ 教师看学情两表 → 删一份资料后同一问应变拒答。附一句失败分类口播，对照 `tech-recommendations.md`。上传区文案可提示「扫描件/纯截图页抽不到字」。
- **不做：** 把真课件推进 git；为演示改 golden；OCR/vision。
- **证明：** 走位文档与现有路由/权限一致（不新开成员模型）。浏览器由维护者按脚本点一遍；Agent 若文件选择器卡住，交接写「浏览器未点真课件，以文档为准」。不跑全量 pytest。

### 阶段 18 — 失败原因人话（默认跳过）

- **做：** 仅当试用时教师完全看不懂 `ParseError: …` 再开。把常见解析失败映射成短中文（无法打开、无文本层、空文件），仍失败无幽灵 chunk。
- **不做：** 用 OCR 把失败变成「成功」。
- **证明：** 损坏夹具仍 failed 无 chunk；教师页能看到人话。未实施则交接写「默认跳过」。

### 阶段 19 — 管理员改密/停用（默认跳过）

- **做：** 仅当试用不能接受「密码只在 seed/.env」时再开。仅 admin；不自助注册；教师仍不能创建账号。
- **不做：** 用户改自己的角色；删课级联大扫除当本期主线。
- **证明：** 若实施：admin 改密后旧 session 失效或须重登；pytest 绿。未实施则交接写「未触发，跳过」。

---

## 3. 明确仍不进仓

校园网部署、邀请码/CAS、多租户 SaaS、OCR/vision、MinerU 当骨架、换 Qwen3-Embedding、Fine-tune DeepSeek、Celery 集群、知识图谱、成绩预测、小程序、把评测平台当产品。

---

## 4. 开工顺序

**16（已完成）→ 16.5（已完成）→ 17**。18、19 默认不做。不要把真课件或 API Key 写入仓库。

下一步由维护者按 `docs/demo.md` 完成阶段 17 浏览器实走，再根据真实反馈决定是否触发阶段 18 或 19。不要提前实施，也不要默认 push。

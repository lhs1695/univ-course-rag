# 开发者观察：M3/M4 本机验收（2026-10-26）

> **标注**：developer 代观察 / API+本机 Playwright headless；**非独立用户试用**，不得写成独立核验或结题验收通过。
> 时区：Asia/Shanghai。证据目录：[`evidence-2026-10-26/`](evidence-2026-10-26/)。

## 环境

| 项 | 值 |
| --- | --- |
| 工作区 | `D:\workspace\univ-course-rag` |
| 演示库 | `univ_course_rag_cn_v2` |
| Alembic | **before ≈ 0013 → after 0015 (head)**（本轮 `alembic upgrade head`） |
| 后端 | `http://127.0.0.1:8000`（`/health` `/ready` ok） |
| 前端 Vite | `http://127.0.0.1:5173` |
| 课程 | 线性代数 `93a86e31-8e5f-4708-a42f-ad93518ce32c` |
| 代码锚点（验收时 HEAD） | `301cc6c`（其上 M3=`4587421`，M4=`59ab09f`） |
| 登录 | `get_settings()` 的 seed_*；未 cat `.env`、未写入文档 |

脚本：`evidence-2026-10-26/run_accept_api.py`、`run_ui_smoke.py`；矩阵 JSON 同目录。

## 验收矩阵

### 基础设施

| 项 | 结果 | 证据 |
| --- | --- | --- |
| health / ready | PASS | `api-matrix.json` → `health_ready` |
| 三角色登录 | PASS | `login_roles` |
| Vite 关键资源 200 | PASS | `vite_asset:*` |
| cn_v2 → Alembic 0015 | PASS | `alembic current` = `0015 (head)` |

### M3 调查（API）

| 项 | 结果 | 证据 |
| --- | --- | --- |
| 未勾外发确认创建被拒 | PASS | `invest_reject_without_confirm` → 422 `external_processing_confirmation_required` |
| 勾选后创建 → Fake run → succeeded | PASS | `invest_create` / `invest_fake_run`；`fake-report.json` |
| Replay run | PASS | `invest_replay_run` |
| 取消 queued | PASS | `invest_cancel_queued` |
| 取消后显式 retry | PASS | `invest_retry_after_cancel` |
| 显式 resume（无安全检查点） | PASS（路径可达） | `invest_resume_interrupted`：SQL 强制 interrupted 无 checkpoint → `failed`/`investigation_checkpoint_unsafe`（设计行为） |
| 报告读取 | PASS | `invest_report_and_page_url`；本轮 Fake 样本多为 no_evidence，**报告内 page_urls 为空** |
| 引用 `#page=` | PASS（服务/前端拼装） | 真问答路径见下；Fake 报告本轮无带页证据。API `content_url` 无 hash；前端 `citationUrl` 在有 `page` 时追加 `#page=` |

### M3 调查（UI Playwright headless）

| 项 | 结果 | 证据 |
| --- | --- | --- |
| 教师登录 → 课程调查路由 | PASS | `ui-matrix.json` / `ui-investigation.png` |
| 未勾确认点创建 | PASS | `ui-investigation-actions.json`：提示「请先勾选本次外发处理确认…」 |
| 勾选 → 创建 → Fake → 报告可见 | PASS | 同文件；`body_has_报告=true`；`ui-investigation-after-actions.png` |
| UI 取消按钮 | SKIP/部分 | 某次 queued 态「取消」按钮存在但 **disabled**（超时未点成）；**取消路径以 API PASS 为准** |
| 浏览器实际 PDF 落页 | SKIP | 未在浏览器内点击 PDF 新窗核对落页；仅服务层/前端 URL 拼装断言 |

### M4 业务（API）

| 项 | 结果 | 证据 |
| --- | --- | --- |
| admin 建学期 / 课程挂学期 | PASS | `admin_create_semester` / `admin_attach_semester` |
| 账号姓名/学号维护 | PASS | `admin_patch_student_profile` / `admin_patch_teacher_name` |
| 本课班级 CRUD | PASS | `class_create` / `class_rename` |
| 真实小 CSV 导入 | PASS | 见下节 |
| `/profile` 无提问历史 | PASS | `profile_no_history` keys=`full_name,student_number,role,classes` |
| 资料两步：停用→学生不可见/不可读；启用→可见；教师不能启用 | PASS | `admin_disable_retrieval` … `teacher_cannot_enable`（演示库已有资料，未新上传） |

### M4 业务（UI）

| 项 | 结果 | 证据 |
| --- | --- | --- |
| `/admin/business` 含学期/班级文案 | PASS | `ui-admin-business.png` / `ui_admin_business` |
| `/profile` 可达 | PASS | `ui-profile.png` |
| 学生 ask 路由 | PASS（路由） | `ui-student-ask.png`；textarea 计数依实现，**真问走 API** |

## CSV 名单

文件：`evidence-2026-10-26/roster-sample-2026-10-26.csv`（3 行数据：已存在匹配 / 缺账号 / 姓名不符）。

摘要：`total=3, imported=1, unchanged=0, rejected=2`；错误码 `student_account_missing`、`name_mismatch`。**不自动开户**。

## 真实模型小样本（当次授权）

| 项 | 值 |
| --- | --- |
| 路径 | **学生问答**（调查外发仍以 Fake 为主验收） |
| 课程 | 线性代数 |
| 问句 | 「用一句话说明线性代数主要研究什么？」 |
| LLM | DeepSeek / `deepseek-flash` |
| Embedding | 硅基流动 / `BAAI/bge-m3` |
| 回答 | 有正文 + 1 条 citation；chunk page=10 |
| 前端拼装 URL | `.../content#page=10` |
| usage / 精确花费 | API `usage=null`，**CNY 精确花费未知**；单次短问 + 检索，粗估 **远低于 ¥2**（未二次重试烧钱） |
| 质量声明 | **不宣称质量达标**；仅证明真实链路可返回答案与依据 |

证据：`real-ask-response.json`；矩阵项 `real_ask_deepseek`。

## 诚实边界 / 未做

- 非独立用户试用；开发者脚本与 headless UI。
- Fake 调查报告本轮无带页证据链接；PDF 浏览器实落页未验。
- UI 取消按钮在观察瞬间 disabled；cancel/resume/retry 以 API 为准。
- 未 push；未 stage `中期答辩材料/笔记/`；未读/输出 `.env` 明文。
- 物理 TTL、完整 Trace UI、PG 真实并发、空白机部署：仍后置/暂缓。
- PLAN-06/07 等正式人工核验缺口仍在。

## 结论

本机演示库已升至 **0015**；M3 Fake/Replay/外发确认/取消/retry/resume 路径与 M4 学期/班级/CSV/主页/检索门控 **API 主路径 PASS**；Vite 关键页与调查确认门禁 + Fake 报告 **UI 已实点**。真实 DeepSeek+硅基流动学生短问 **链路 PASS**，花费未精确计量但单次可控。文档已按本观察对齐；见同日 SESSION_STATE / 当前交接 / backlog。
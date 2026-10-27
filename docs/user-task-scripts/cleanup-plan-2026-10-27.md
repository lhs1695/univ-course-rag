# 拟删/归档清单 · 2026-10-27（t299）

用户拍板：清理杂乱；过期 docs/tasks 与旧中期附件索引一并收；砍「人力资源管理」；不 push。

## A. 本机垃圾（未跟踪 / 可直接删，不进 git）

- 根目录 `.codex-plan-*.txt`、`.codex-plan15-ttl-summary.txt`、`.codex-t272-*.txt` 等未 ignore 的临时 txt（已 ignore 的 `.codex-prompt*` / `.codex-last*` / `.codex-prompts/` 一并清磁盘）
- `.pytest-tmp-*`、`.tmp-*`（含 validation/retire/ingest/uvicorn/vite 临时目录与 log）
- `docs/user-task-scripts/_tmp_*.py`（本轮探测脚本）
- **不删**：`backend/.venv`、`frontend/node_modules`、`.env`、正式 `corpus/`、`backend/corpus/`（教育学路径修复用的运行时副本，未跟踪但演示需要）

## B. 中期答辩材料（工作区已 D，stage 删除并重写 README）

磁盘上已不存在、git 仍跟踪的旧附件（彩排截图、汇报PPT、研究证据、图示、提纲、格式、旧开题等）→ **确认 git rm / stage 删除**。

**保留并纳入仓**：
- `中期答辩材料/中期报告-修订稿.md`
- `中期答辩材料/Agent设计与开工笔记.md`（目前 untracked，加入）
- `中期答辩材料/README.md`（重写为只描述现存文件；数字错位不改报告正文）

**已删 docs 侧**：`docs/中期演示运行卡.md`（工作区已 D）→ stage 删除；运行说明改以 `docs/当前交接.md` / 根 README 为准。

## C. 过期 docs/tasks → 归档到 `docs/archive/tasks-2026-10-27/`

惯例：archive 不直接硬删历史卡。拟归档（产品已撤或本批业务卡已合入）：
- PLAN-14 / PLAN-15 / PLAN-16（调查 Agent 主线，产品已撤）
- PLAN-review-开工计划-2026-10-26.md
- T-retire-investigation-agent.md（撤下已完成）
- T-college-minimal.md / T-course-folders-shallow-tree.md / T-docs-library-ux.md / T-folders-ux-redesign.md / T-profile-role-fields.md（已落地）

**tasks 根保留**：`README.md`、`SESSION_STATE.md`、`backlog.md`、`_template.md`、PLAN-00～10、PLAN-17*、PLAN-FE-01（仍作历史指针；README 注明调查卡已归档）。

## D. 演示库删课

- 库：`univ_course_rag_cn_v2`
- 删：`人力资源管理`（DELETE `/admin/courses/{id}`，同删概率论路径）
- 目标余课：线性代数、教育学原理、机器学习、智能移动机器人

## E. 待你确认（本轮不删）

- `docs/archive/midterm-*` 历史归档（已在 archive）
- `output/`（gitignore，可清磁盘缓存，非源码）
- 正式规格：`结题*.md` / `validation.md` / `implementation-plan.md` / `架构说明.md` 等
- `backend/corpus/` 运行时 PDF 副本（勿当垃圾删）

# FE-refresh-v1 · 前端全面翻新（Codex 提示词）

> 状态：已落档，待用户授权后交给 Codex 实现。  
> 机位：`D:\workspace\univ-course-rag`（Windows）。  
> 模型建议：`gpt-6.1-sol`，思考 `high`。  
> 本文件同时作为后续 FE 任务卡的可复用模板：改标题/范围/验收即可派生 FE-02…。

---

## 0. 给 Codex 的执行约束（先读）

1. **只改** `frontend/` 内实现（含本提示词不改业务契约）；可新增 `frontend/src` 下主题/token 模块与必要样式。
2. **禁止**：改 `backend/`、迁移、`.env` / `.env.example`（本卡不碰密钥）、`中期答辩材料/`、假造未上线业务 API、安装「气质主题」Skill、引入大型新依赖（除非极必要且说明理由）。
3. **先读再改**：`frontend/src/router.js`、`App.vue`、`main.js`、`styles.css`、`student.css`、`session.js`、`api.js`、`courseAccess.js`、各 `views/*`、`components/*`、`package.json`、现有 `frontend/tests/`（若有）。对照 `docs/结题已拍板规格.md` 仅理解产品边界，**本卡不实现 Agent/业务后端**。
4. 工作区可能有未提交的 `backend/app/agent/` 等：**不要** stage/提交那些文件。
5. 完成后在仓库根用 Vite/既有前端测试做自检；不默认 `git push`；是否 commit 由调用方决定（本卡作者可本地 commit 文档，实现卡另议）。
6. 输出：简述改了哪些文件、主题切换如何测、已知限制。

---

## 1. 目标与非目标

### 目标

- **全面翻新**前端观感与壳层信息架构：登录 + 学生 + 教师 + 管理员**第一期一次换齐**。
- 现有视觉可整体重设计，**不必保留旧紫皮/旧文案风格**；**必须保留**现有 API 调用、角色权限、路由能力与演示闭环：
  - 登录 → 书架（我的课程）→ 提问 → 回答含依据 → 回跳/打开 PDF。
- 学生端：**可切换「学 / 问」**两种工作态；**默认「学」**；`localStorage` 记住上次选择；演示观感精美、可彩排。
- 教师端固定气质词 **「册」**（对内设计约束，**UI 不展示主题名、无切换器**）。
- 管理员端固定气质词 **「衡」**（同上）。
- **全站同源 design token**（颜色语义、字号、圆角、状态色、焦点环）；学生「学/问」只是同一 token 的两套表面，教/管是同源浅色工作台的不同密度，不是第二套品牌色。
- 导航为结题能力预留**占位灰项**（如「课程调查」「学期 / 班级」）：可见、禁用或标注「即将推出」，**不请求假 API、不编造数据**。
- Insights / 问答反馈：**保持精简**，不恢复大屏学情。
- **无**营销 Hero、**无** GraphRAG / 知识图谱装饰图或关系图模块。
- Element Plus：管理台与表格/表单可继续用；学生提问主路径可更多原生控件；将 `--el-color-primary` 等映射到本卡 token。
- 尊重 `prefers-reduced-motion`：动效可关或降级。

### 非目标（本卡不做）

- 后端契约变更、新 REST、Agent 运行时、学期/班级/名单真实功能。
- 拷贝研究目录下气质主题 HTML/CSS 为整站皮肤；学/问样张**仅机制参考**（双主题切换 + 语义 token），视觉由模型按 brief **自行发挥**。
- 安装或全局启用「气质主题 Skill」。
- 为「好看」重写 RAG/引用/权限逻辑。

### 优先级（用户已拍板）

**先完成前端翻新，再开工其他结题计划**（含后端 PLAN-14～17 实现与审计划后的开工）。本卡是当前最高优先的前端工作。

---

## 2. Design brief

### 2.1 四词气质（对内；勿做成可切换第三、第四主题）

| 表面 | 词 | 谁用 | UI 行为 |
| --- | --- | --- | --- |
| 学 | 学 | 学生 | 可切换；偏浏览、选课、资料目录；纸面、留白、导航清晰 |
| 问 | 问 | 学生 | 可切换；偏提问与证据台；对比度略高、信息更密 |
| 册 | 册 | 教师 | **不切换**；讲义/备课台；浅纸面、墨色字、表格清晰 |
| 衡 | 衡 | 管理员 | **不切换**；秩序/权限/全局；同源 token，强调状态与列表可读 |

学生默认进入 **「学」**；切换控件放在学生壳层显眼但不挡主路径处；键名建议 `univ-course-rag.student-surface` = `study` | `ask`（或同等清晰命名），写入 `localStorage`。

### 2.2 同源 token（必须落地）

在全局 CSS（或小型 theme 模块）定义语义变量，至少覆盖：

- 背景 / 表面 / 表面次级 / 分割线
- 墨色字阶（强 / 正文 / 次要）
- 强调色（accent）及 hover/active
- 成功 / 警告 / 危险 / 信息
- 圆角、间距阶梯、内容最大宽
- 焦点环（`:focus-visible`）
- Element Plus：`--el-color-primary` 及常用 text/border 映射到上述 token

「学」「问」通过 `data-theme="study"|"ask"`（或根 class）切换同一组变量的取值；教师「册」、管理「衡」用角色壳 + 可选 `data-surface="ce"|"balance"` **仅文档化/微调密度**，不提供用户切换。

### 2.3 视觉发挥与忌讳

- **鼓励**：有辨识度的文教产品气质、清晰层级、精致空态与错误态、中文排版可读。
- **禁止**：通用 AI 模板脸（无意义紫渐变玻璃拟态堆砌、假仪表盘、装饰性关系图谱、大段营销口号 Hero）。
- **禁止**：为风格破坏对比度与可访问性（文字对比、焦点可见、跳过链接保留）。
- 登录页纳入翻新；文案保持产品语气（课内资料为据），可重写润色但不要假功能承诺。

### 2.4 壳层与导航

- 学生壳：品牌 + 学/问切换 + 课程上下文 + 提问/资料等现有 Tab；结题占位灰项可放在课程级或全局次要区。
- 教师壳：气质「册」；课程上下文 + 现有 Tab（提问/资料/本课学生/问答反馈）+ 占位「课程调查」等。
- 管理壳：气质「衡」；现有后台链（账号/课程授权/提问日志/系统状态）+ 占位「学期 / 班级」等。
- 三角色信息架构对齐同源组件语言（按钮、页眉、空态），避免「三套完全不像的产品」。

---

## 3. 范围文件（指引）

### 必触 / 大概率重写

- `frontend/src/main.js` — 引入全局样式/主题
- `frontend/src/App.vue` — 三角色壳层、学生切换入口、占位导航
- `frontend/src/styles.css`、`frontend/src/student.css` — 收敛为 token + 角色表面（可拆 `theme.css` 等，保持清晰）
- `frontend/src/router.js` — **路由表与守卫逻辑保持能力等价**；仅当翻新需要 meta（如 surface）时可小幅扩展，不删现有路径
- `frontend/src/views/LoginView.vue`
- `frontend/src/views/CoursesView.vue`
- `frontend/src/views/AskView.vue`
- `frontend/src/views/DocumentsView.vue`
- `frontend/src/views/MembersView.vue`
- `frontend/src/views/InsightsView.vue`（精简，不扩成大屏）
- `frontend/src/views/AdminUsersView.vue`
- `frontend/src/views/AdminCoursesView.vue`
- `frontend/src/views/AdminMaintenanceView.vue`
- `frontend/src/views/AdminSystemStatusView.vue`
- `frontend/src/components/*`（AnswerBody、StudentDocuments、RuntimeStatus、InsightTrend 等随壳重皮，不改调用契约）

### 逻辑模块（可调样式调用，慎改行为）

- `session.js`、`api.js`、`courseAccess.js`、`askHistory.js`、`citationDisplay.js`、`documentDisplay.js`、`answerMarkdown.js`、`drafts.js`、`insightTrend.js`
  → 默认保持行为；若仅为主题/class 挂钩可最小改动。

### 测试与笔记

- 更新或补充 `frontend/tests/` 中与壳/主题相关的断言（若现有测试依赖旧 class，一并修）。
- 可选：在 `frontend/DESIGN-NOTES-STAFF.md` 顶部加一段指向本提示词与「册/衡」说明（短），或新建 `frontend/DESIGN-TOKENS.md` 一页；**不要**长篇重写中期材料。

### 明确不在范围

- `backend/**`、`docs/tasks/PLAN-14*` 实现代码、`中期答辩材料/**`、根目录密钥与 docker 密钥。

---

## 4. 实现步骤（建议顺序）

1. **盘点**：列出当前路由与三角色入口；确认演示闭环相关组件（Ask、引用、PDF）。
2. **Token 地基**：建立同源 CSS 变量与 `study`/`ask` 两套取值；映射 EP primary。
3. **主题状态**：学生表面 store 或小型 composable + `localStorage`；默认 `study`。
4. **壳层**：重做 `App.vue` 学生壳 / 教师「册」壳 / 管理「衡」壳；加入占位灰项。
5. **逐页换皮**：Login → Courses → Ask（重点）→ Documents → Members → Insights → Admin 四页。
6. **提问主路径打磨**：依据列表、打开原文、空态/失败态、reduced-motion。
7. **自检**：三角色账号走主路径；切换学/问刷新后仍保持；缩窄窗口基本可用。
8. **收尾**：删无用旧样式；说明如何本地 `npm run dev` 验收；不 push。

---

## 5. 禁改清单（硬）

- 不改后端 API 形状与权限语义。
- 不读、不打印、不提交任何真实 API Key / `.env`。
- 不把占位导航做成可提交的假表单成功态。
- 不上 GraphRAG/知识图谱可视化。
- 不恢复 Insights 大屏。
- 不安装气质主题 Skill；不整站拷贝研究目录 HTML。
- 不默认 `git push`；不 force push。

---

## 6. 验收清单

- [ ] 学生：默认「学」；可切到「问」；刷新后记忆仍在。
- [ ] 学生：登录 → 课程 → 提问 → 回答/依据 → 打开 PDF 的路径可用（接现有后端）。
- [ ] 教师「册」：课程资料/成员/精简反馈等主路径可用；无主题切换器。
- [ ] 管理员「衡」：账号/课程授权/日志/系统状态主路径可用；无主题切换器。
- [ ] 结题占位灰项可见且不可伪造成功调用。
- [ ] 同源 token：三端观感同族；EP 主色已挂 token。
- [ ] `prefers-reduced-motion: reduce` 下无强动画干扰。
- [ ] 未引入不必要的大型新依赖；`package.json` 变更有说明。
- [ ] 未改 backend / 中期材料 / 密钥文件。

---

## 7. 后续 FE 卡如何复用本模板

派生新卡时保留 §0 约束、§2 token 规则、§5 禁改；替换：

- 标题与目标范围（例如「教师调查页」「名单导入页」）
- §3 文件清单
- §4 步骤与 §6 验收

新页必须复用本卡落地的 token 与壳层，禁止另起一套色板。

---

## 8. 一句话任务（可直接贴给 Codex）

在 `D:\workspace\univ-course-rag` 按 `frontend/prompts/FE-refresh-v1.md` 全面翻新前端：学生学/问可切换（默认学、localStorage）、教师册、管理衡、同源 token、三角色+登录一次换齐、结题导航占位灰项、保留 API 与演示闭环、无假 API/无图谱/无营销 Hero；只改 frontend，自检后汇报。

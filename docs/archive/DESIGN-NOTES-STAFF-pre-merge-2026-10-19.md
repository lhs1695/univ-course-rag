# 教师与 Admin：A 紫色书签品牌

本卡在 `feat/staff-admin-align-a`、基线 `f567d42` 上实施。教师管理学生与核对问答，管理员维护账号、课程授权和系统状态；各页继续以操作栏和表格回答这些管理问题。

- Token：纸白 `#FFFFFF`、冷白 `#F8F7FB`、葡萄紫 `#633A88`、墨紫 `#342447`、淡藤 `#EEE8F5`、铅笔黄 `#F0D97C`、线 `#DDD6E5`。黄色仅保留为品牌 token，不添加无业务意义的装饰。Element Plus primary 的深浅阶与 student.css 一致，全局配置也覆盖挂到 body 的弹层；成功、警告和删除继续保持语义色。
- 壳策略：保留现有横向导航、1200px 内容区、白纸操作面板和清晰表格；标题用本机宋体，正文用 Segoe UI / 苹方 / 微软雅黑。唯一造型标识为顶栏紫色「课」书签，面板减少阴影，导航用紫色文字与下划线表示当前页，不采用学生书架布局。
- 复用：沿用 lockfile 中 Vue 3.5.42、Element Plus 2.14.5（MIT）的既有组件，不新增依赖、字体或外部素材。只适配 CSS 与模板文案；创建、授权、移出、刷新等事件和脚本保持原样。
- 学生边界：App.vue 的 `studentSurface` 计算、`.study-app` 模板、student.css、Login / Courses / Ask / Documents 均未改。全局 primary 对齐 A；教师 Documents 继续留在学生壳，共享紫色表格 token，上传与入库逻辑不变。Members / Insights 与 `/admin/*` 继续走 app-shell，路由守卫不变。
- 自检：检查 Vue 模板 / scoped CSS 与全局 CSS 可解析，核对业务脚本与事件绑定未变、学生门控和模板未变，执行 `git diff --check`。按本卡要求不运行 `npm run build`；未做浏览器登录、视觉截图或操作验收，这些由外层补验，不把静态检查当作端到端通过。

视觉复核重点：Admin 顶栏与主按钮为紫色，教师 Members / Insights 与 Admin 同壳，课程行选中为淡藤色，表格空态提示下一步；学生登录与课程书架仍使用 A 原模板。维护页删除提示、问答依据不足与系统故障的区分均保留。

实际自检结果：6 个修改过的 Vue 模板及其 scoped CSS、全局 CSS 解析通过；业务脚本与动态绑定、学生模板与门控、学生四页和 router.js 与基线一致；7 个 primary 深浅色值与 student.css 一致；`git diff --check` 通过。Node 子进程调用 Git 曾遇 EPERM，改由 PowerShell 读取基线完成对比。

提交阻塞：已尝试指定文件的 `git add` 与 `git commit`，均因主仓 Git 管理目录不在沙箱可写范围内，无法创建 `D:/workspace/univ-course-rag/.git/worktrees/feat-staff-admin-align-a/index.lock`（Permission denied）。未暂存、未生成提交，HEAD 仍为 `f567d42`。外层需仅暂存本卡 7 个前端源码文件、本说明和两份计划/交接记录，再提交 `feat(ui): align staff/admin shell with A bookmark brand`；不要纳入原有提示词与执行日志。

# 前端视觉与验收

本轮范围：[FE-refresh-v1](prompts/FE-refresh-v1.md)。暖纸、墨绿、阅读排版；复用 Vue / Element Plus，无新增依赖。API、权限守卫、流式问答与 PDF 地址逻辑保留。

- `src/theme.css`：唯一语义 token 来源，包含表面、文字、强调/状态色、字号、圆角、间距、焦点与 Element Plus 映射。根节点承载变量，弹窗和下拉菜单同样继承。
- 学生默认「学」；页头可切「问」。`data-theme="study|ask"` 调整同组 token 的取值与阅读密度；不会导航或重建问答页。课程卡主按钮随工作态优先进入资料或提问。
- `src/theme.js`：`univ-course-rag.student-surface` 保存 `study|ask`；浏览器禁用存储时退化为当前页面内存，刷新后恢复默认。
- 教师「册」与管理员「衡」分别使用 `data-surface="ce|balance"`，仅调整密度；界面不展示这些内部名称，也没有切换器。登录始终使用浅纸面。
- 占位入口为原生禁用按钮，不绑定路由或请求。「课程调查」「学期 / 班级」尚未实现。
- 全局 `:focus-visible` 与跳过链接覆盖三角色；`prefers-reduced-motion: reduce` 禁用 CSS 动画/过渡。现有可选图表也在渲染时尊重该偏好，反馈页未增加图表。

## 本地验收

在 `frontend` 执行 `npm run dev`，浏览器打开 Vite 地址（默认 `http://localhost:5173`）。后端沿用已有本机服务，不需要真实模型调用来检查外观。

1. 登录学生：首次显示「学」；切到「问」后刷新仍保留，切回「学」同样保存。
2. 学生书架 → 资料 / 提问；回答中的引用聚焦依据卡，原文链接保留 PDF 的 `#page=N`。仅在已授权的 Fake/Replay 环境或获得真实模型调用授权后提交问题。
3. 教师检查资料、成员、精简反馈；管理员检查账号、课程授权、日志预览与系统状态。两者均不出现工作态切换。
4. 缩至手机宽度，导航折成顶部区域；宽表格可横向滚动。键盘 Tab 检查焦点和跳过链接；系统开启减少动态效果后检查加载态。

构建：`npm run build`。回归：`node --test tests/*.test.mjs`（不允许子进程的环境可用 `--test-isolation=none`）。主题测试覆盖默认、刷新恢复、非法值和存储异常。自动化样例数据只验证前端链路，不代表真实回答正确率或真实后端端到端验收。

## 本次校验记录（2026-10-26）

- `node --test --test-isolation=none tests/*.test.mjs`：`tests 44 / pass 44 / fail 0`。旧上传错误测试原本期待 `15 MB`，现同步为已有 API 错误文案「文件过大」，没有改 API 模块。
- Vue 编译器直接检查：`15 files passed`，覆盖 App、所有 views 与 components 的脚本、模板与局部 CSS。
- `npm run build`：调用方本机复验 **通过**（Vite 7.3.6，约 16.6s）。Codex sandbox 内曾因 `spawn EPERM` 未能构建，属沙箱限制而非源码错误。
- 浏览器点击与真实后端演示闭环：留给用户本机 `npm run dev` 验收（见上文清单）。本卡未做真实 embedding / LLM 调用。

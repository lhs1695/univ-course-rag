# F1–F20 修复交付

基线：9246139；分支：fix/staff-admin-f1-f20。仅本 worktree 修改，未读 .env、未修改后端、未修改/提交新开题资料.md、未 push。

| 项 | 状态 | 实现与边界 |
| --- | --- | --- |
| F1 | 已修 | App 按会话角色选壳，教师/Admin 所有课程页使用 staff；capability 仅控制授权与入口。 |
| F2 | 已修 | Admin 课程标题、空态按角色分支，显眼链接至课程与授权，说明需课内身份。 |
| F3 | 已修 | 管理表独立打开原文列，复用 documentContentUrl/isPdfDocument/clampDocumentPage；仅 succeeded 可打开，PDF 带 #page=。 |
| F4 | 已修 | Admin 后台和我的课程保持 staff 壳；登录与学生课程保留 study。 |
| F5 | 已修 | 教师顶栏与书架教师 pill、备课文案，本课学生/问答反馈改为可见边框操作。 |
| F6 | 已修 | 非学生资料页使用管理表；上传、删除、重试仍服从原 capability，不扩大权限；学生仍用 StudentDocuments。 |
| F7 | 已修 | 默认待核对、备课建议、趋势；建议基于 no_evidence/cited，无数据诚实说明；统计口径、引用问句与相似分组默认折叠。无新增模型调用。 |
| F8 | 已修 | 双壳页签统一提问/资料。 |
| F9 | 已修 | 找不到学生文案统一；提交锁与输入禁用，页面单处 Toast，Element Plus grouping 合并同文案提示，API 层不弹消息。 |
| F10 | 前端诚实降级 | 已核对 users.py 仅 GET/POST，静态能力声明禁止改密/停用；页面明确说明仅支持创建、其余需运维，无假接口。 |
| F11 | 已修 | 默认选第一门，刷新保留仍存在的选择；成员与授权标题始终显示；删除灰色降权，与重命名拉开。 |
| F12 | 前端诚实降级 | 红：检查失败/库不可用/模型 unavailable；黄：配置已填请在问答页实测；绿：库可用且双 Fake 可尝试 Fake 演示。当前接口无真实模型连通证据，因此 configured 不显示绿色。细节折叠。 |
| F13 | 已修 | 删除确认枚举成员、资料文件与入库记录、向量切片、提问日志，要求输入完整课程名；已有外部备份不受影响。依据现有课程删除处理与外键级联，未实际删除课程。 |
| F14 | 前端诚实降级 | staff 页面预期 401 不再弹额外 error；登出遇会话过期仍完成本地清理；内联 favicon 避免浏览器默认图标 404。Network/浏览器原生 HTTP 错误不可由前端消音，真实未知 404 仍需外层走查定位，不掩盖故障。 |
| F15 | 已修 | staff 书签缩小并改浅紫底深紫字，沿用纸白顶栏。 |
| F16 | 已修 | admin 路由越权提示为仅管理员可进入后台管理；普通课内越权仍用原授权说明。 |
| F17 | 已修 | 创建账号清空用户名/密码/角色；提交前确认全局角色；确认期间锁表单并提交确认时快照，取消不请求。 |
| F18 | 已修 | 重命名提示使用课程显示名称。 |
| F19 | 已修 | staff 导航可换行、长课名换行；表格保留 Element Plus 横向滚动，限制容器宽度；窄屏日期控件限宽。不改学生卡片。 |
| F20 | 已修 | 导航与维护页标高级，明示演示时勿当场删除。 |

复用：使用现有 Element Plus（声明 ^2.11.3）、Vue（^3.5.21）、原生 details、documentDisplay 与 api.js，不新增依赖，不复制第三方源码。只实现角色分支、短文案与样式适配，不另造通用框架。

自检：9 个受影响 Vue SFC 的 parse/compileScript/compileTemplate/compileStyle 静态检查通过（只读使用已有安装的 Vue 编译器）；git diff --check 通过。Node 内存桩定向检查通过：账号确认取消不请求/确认角色快照/清空恢复学生；成员双提交只请求一次且只报一次；课程默认选择/保留选择/失效回退；运行状态红黄绿及失败分支。检查未访问产品 API。

按本次指令未运行 npm run build、未启动产品或做 Playwright 点击验收；外层需完成构建及桌面/390px 三角色走查，尤其课程默认成员、账号确认/清空、PDF 页码、单次 Toast、系统红黄绿状态。未调用真实模型、未创建账号或删除资料/课程。

提交阻断：已按明确文件清单尝试 git add 与本地 Conventional Commit，但 Git 无法创建 D:/workspace/univ-course-rag/.git/worktrees/fix-staff-admin-f1-f20/index.lock（Permission denied）。该 Git 元数据目录在当前沙箱可写范围外；未绕过权限，未暂存、未产生新 commit，HEAD 仍为 9246139。外层需仅暂存本说明、两份交接/计划文件与本次 14 个前端文件（git diff --name-only 可核对），排除原有 .codex 日志/提示词，然后提交：fix(ui): staff/admin shell by role and F1-F20 audit fixes。

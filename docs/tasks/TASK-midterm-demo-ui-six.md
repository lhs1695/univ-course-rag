# TASK: 中期演示 UI 六点（lhs / 藏班级 / 去刷新 / 课序 / 去 eyebrow / 页内预览）

| 项 | 值 |
| --- | --- |
| 对应 PLAN | 无（中期演示拍板） |
| 状态 | doing（代码与定向测试完成；构建、浏览器点验、提交受环境阻断） |
| 须授权 | 前端预览依赖安装（用户已授权本批） |

## 目标

用户拍板全部落地（登录账号密码不变；不 push）：

1. 演示库学生 `username=student` 的 **显示名 `full_name` → `lhs`**；seed 侧新建学生时也写入 `full_name=lhs`（已有用户不靠 seed 改密码）。
2. 个人主页 **「所属课内名单班」整块只藏前端**；后端 `/auth/profile` classes 与班级 API 不动。
3. **去掉个人主页「刷新资料」按钮**（三角色共用 ProfileView）。
4. 课程列表展示时 **机器学习、智能移动机器人排前两位**（前端排序即可，不必改库 code）；线代/教育学跟后。序号仍按展示序 `01/02/...`。
5. 删掉各页 `eyebrow` 双行式「A / B」页眉标签（如「我的课程 / 课程书架」「我的 / 个人主页」「管理 / 账号」「教学 / …」「课程资料 / 阅读目录」「课程问答 / 证据阅读」等）；保留 `h1` 与说明文案。导航链接文案可保留。
6. **所有资料改为页内浏览**（PDF/PPTX/DOCX/MD/TXT）：滑动、缩放、翻页/列表；排版合适。PPTX 不得再因 `attachment` 强制下载。优先成熟薄封装（如 `@vue-office/*` 或 pdf.js + 现有 markdown-it）；后端 content 对可预览类型尽量 `inline`。下载入口可保留为独立「下载」。

## 非目标（禁止顺手做）

- push；恢复调查 Agent / Investigation 入口
- 改登录账号密码；大改班级/名单后端；重入库；改评测金标
- 通读全部 docs/、无关重构

## 验收标准

- [x] 学生 `full_name=lhs`，username/password 保持不变（数据库前后密码哈希一致）
- [x] Profile 无名单班表、无「刷新资料」
- [x] `/courses` 列表前两门为机器学习、智能移动机器人（学生/教师；代码与稳定排序测试通过，实点待补）
- [x] 相关页无 `eyebrow`「A / B」双标签
- [ ] 打开 PDF/PPTX/DOCX/MD/TXT 走页内预览（实现及行为测试完成；实际文件渲染、缩放/翻页待浏览器点验）
- [ ] `cd frontend; npm run build` 通过
- [x] 相关前端 node 测试与受影响 pytest（若有）通过
- [ ] 本地 Conventional Commit；不 push

## 约束

- 栈：现有 FastAPI + Vue3 + Element Plus；不引入第二套 RAG
- 密钥不读不输出；不覆盖无关未提交改动（仅 `?? backend/corpus/` 与 tmp log 勿 stage）
- Windows 路径 `D:\workspace\univ-course-rag`

## 禁止改动的路径

- `.env`、密钥明文
- 评测金标 / expected-outputs
- 用户未点名的 corpus 大规模重解析
- Agent investigation 产品面恢复

## 相关上下文（指针）

- `frontend/src/views/ProfileView.vue`（名单班 + 刷新资料 + eyebrow）
- `frontend/src/views/CoursesView.vue`（排序 + eyebrow）
- 各 Admin*/Ask/Documents/Members/Insights/StudentDocuments 的 `eyebrow`
- `frontend/src/documentDisplay.js`、`StudentDocuments.vue`、`DocumentsView.vue`、Ask 引用打开
- `backend/app/api/documents.py` content disposition（本轮 PPTX/DOCX 已改为 inline）
- `backend/app/seed.py`；演示库 `univ_course_rag_cn_v2` 用户 `student` 已更新为 `lhs`

## 本轮实现与证据（2026-10-27）

- 使用现有 `Settings().database_url`，先核对库名为 `univ_course_rag_cn_v2`，执行指定 UPDATE。原始摘要：`demo database: updated student full_name=lhs; rows=1; password hash unchanged`。未打印连接串、哈希或密码；未运行全量 seed。seed 新学生姓名为 lhs；已有 null/空串/验收学生甲可同步，保留自定义姓名与已有密码。
- Profile 保留 onMounted 请求；学生/教师 CoursesView 与 AdminCoursesView 共用稳定排序，序号继续 index+1 补零。只移除页面标题眉标，保留导航、登录页眉标与资料夹小标题。
- 新增受现有路由及资料权限约束的 `/courses/:courseId/documents/:documentId/preview?page=N`。管理员另有带 admin 角色门禁的 `/admin/documents/:previewCourseId/:documentId/preview`，保留既有跨课资料管理例外，不要求加入课程；对应行为测试已补。学生、教师、管理员打开与 Ask 引用均改为 RouterLink，返回时保留内存问答历史；原 content 链接仅用于同源内容读取和显式 download。
- PDF.js 使用真实页数与页码夹取、单页 canvas；worker、CMaps、标准字体、WASM 随 Vite 同源静态提供。DOCX/PPTX 复用 Vue Office v3 构建，ArrayBuffer 输入，依据渲染页/幻灯片生成导航。统一工具条、列表/翻页、50%–200% 缩放、内容滚动、全屏/Escape、下载。MD/markdown 使用 markdown-it，TXT 使用转义文本；按段落/显式分页拆分阅读区；Markdown 禁用 HTML 和远程图片加载。
- 依赖：`@vue-office/docx@1.6.3`、`@vue-office/pptx@1.0.1`、`vue-demi@0.14.10`、`pdfjs-dist@6.4.299`；开发依赖 `vite-plugin-static-copy@4.1.1`。markdown-it 安全补丁 15.0.2→15.0.3，source-map-js 更新修复版。默认 npm 缓存无写权限，使用工作区 `.tmp-npm-cache`；安装生命周期脚本因 spawn EPERM 未执行，安装加 `--ignore-scripts`，显式导入已发布的 Vue3 构建。
- 后端 `.pdf/.pptx/.docx/.md/.markdown/.txt` 均 inline，原授权和 nosniff 保留；storage 断言同步更新。没有第二套 RAG、迁移、模型调用或资料解析。

### 验证命令与原始输出摘要

- `node --test --test-isolation=none frontend/tests/*.test.mjs` → **tests 74 / pass 74 / fail 0**。新阅读器行为测试覆盖 PDF 页码落点/夹取、Office 列表导航、失败重试、离页丢弃迟到响应与 worker 销毁；模拟 PDF/Office 不代表真实文件版式或人工验收。
- `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_seed.py backend/tests/test_storage.py -q -p no:cacheprovider --basetemp .tmp-pytest-ui-six --tb=short` → seed 5 项通过；storage 16 项被 pytest 以 0700 创建临时目录后的 WinError 5 阻断，最终清理也报权限错误。使用相同测试、关闭内建 tmpdir 插件、仅提供工作区普通新建独立 UUID 的 tmp_path 后：**21 passed, 1 warning in 4.95s**（Starlette/anyio 既有弃用提示）。业务断言未改以绕过失败，复现：

```powershell
@'
from pathlib import Path
from uuid import uuid4
import pytest
class WorkspaceTemp:
    @pytest.fixture
    def tmp_path(self):
        path = Path.cwd() / '.tmp-ui-six-tests' / uuid4().hex
        path.mkdir(parents=True)
        return path
raise SystemExit(pytest.main(['backend/tests/test_seed.py', 'backend/tests/test_storage.py', '-q', '-p', 'no:cacheprovider', '-p', 'no:tmpdir', '--tb=short'], plugins=[WorkspaceTemp()]))
'@ | backend/.venv/Scripts/python.exe -
```

- `backend/.venv/Scripts/python.exe -m ruff check backend/app/seed.py backend/app/api/documents.py backend/tests/test_seed.py backend/tests/test_storage.py` → **All checks passed!**
- frontend 中 Node stdin + `@vue/compiler-sfc` 对本轮 13 个 view 执行 parse/compileScript/compileTemplate/compileStyle → **13 changed view SFC script/template/style checks passed; no heading eyebrows**。依赖入口 resolve 全部 true；不替代完整 build。
- frontend 中 `npm audit --omit=dev --cache ../.tmp-npm-cache --registry https://registry.npmjs.org` → **found 0 vulnerabilities**。
- frontend 中 `npm run build` → `failed to load config ... spawn EPERM`（esbuild 子进程）；`npm run build -- --configLoader native` → `commonjs--resolver spawn EPERM`。补充 `node --input-type=module -e "import { build } from 'vite'; await build({ configLoader: 'native', resolve: { preserveSymlinks: true }, esbuild: false, build: { target: 'esnext', minify: false, cssMinify: false } });"` 也在 Vite define 转换启动 esbuild 时被同一权限限制阻断。**完整 build 未通过**，未修改正常构建脚本规避。
- `git diff --check` → exit 0（仅 LF→CRLF 提示）。
- 精确 `git add -- <本任务代码/测试/依赖路径>` → `fatal: Unable to create 'D:/workspace/univ-course-rag/.git/index.lock': Permission denied`；`git diff --cached --name-only` 为空。**无本轮 commit，未 push**。权限恢复后建议 `feat(demo): simplify pages and add in-app document previews`，并精确加入本卡和 SESSION_STATE。
- Browser Use 访问已有 `http://127.0.0.1:5173` 标签被站点权限门拒绝（user declined permission），没有通过其他表面/协议绕过。DevSpace 因 approval policy=never 拒绝调用。

### 待点验清单（未宣称完成）

1. 学生/教师课程列表前两项、01/02；Profile 显示 lhs、无名单班/刷新；各角色页眉与导航。
2. PDF 从资料页指定第 N 页打开；问答引用第 N 页打开后按浏览器返回，回答仍在。
3. PPTX 逐张列表/上一张/下一张；DOCX 页列表；MD/TXT 阅读、滚动、缩放。
4. 全屏/Escape、窄屏工具条、下载按钮；三角色打开资料均不强制下载。
5. 权限变化或文件不可用后的错误与重新加载；正常环境补跑标准 build 后完成本地 commit。

未做：真实模型调用、重入库、密码修改、调查 Agent 恢复、push。未暂存 `.env`、corpus、临时日志/缓存/测试目录。

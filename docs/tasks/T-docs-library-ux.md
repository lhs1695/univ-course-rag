# TASK: 资料库交互与展示打磨（Docs Library UX）

| 项 | 值 |
| --- | --- |
| 对应 PLAN | 资料夹/资料页演示打磨（接 T-folders-ux-redesign） |
| 状态 | implemented（测试通过；构建 / 浏览器验收及本地提交受环境限制） |
| 须授权 | 无（前端为主；不改检索主路径） |

## 目标

1. **文案**：删除「目录仅用于整理资料，课程问答仍检索整课。」以及「按资料夹浏览 · 最多两层」类提示（`FolderLibrary.vue` 等）。
2. **检索启用展示**（两步启用语义不变：仅管理员可开检索）：
   - 学生：完全不展示「检索启用/停用」字样。
   - 教师资料表：不要每行秀启用开关；未启用可用低调灰标或「待启用」筛，教师可停用/移出检索能力保留但不做成每行开关秀场。
   - 管理员：`AdminDocumentsView` 保留清晰待启用/已启用与启用操作（可小打磨批量或筛选项）。
3. **资料夹重做（演示级，Codex 自设计实现）**：
   - 不要「未分组」三字（根级改叫「全部资料」或「资料」等自然文案）。
   - 不要「最多两层」提示。
   - 搜索 = **整课资料名**，不限当前夹；切换夹时搜索框可保留，列表按夹过滤，搜索命中应跨夹可见（设计上：搜索非空时展示整课匹配列表，或自动切到含命中的视图——自定但须整课搜）。
   - 师生均加 **下载**（可用现有 `/content`；下载用 `content_disposition=attachment` 或前端 `download` 属性；打开仍可 inline）。
   - 删除 **刷新资料** / **刷新资料列表** 按钮（依赖进入页加载与上传后自动刷新即可）。
   - 浅树 ≤2、换父、侧栏仍好用；跟现有 Element Plus / 「册」气质，不另起皮肤。
4. **baoyu-design**：仓库无独立 baoyu skill；按现有 frontend 视觉 token / Element Plus 主题对资料页、必要时主页/业务页做**局部排版完善**（间距、对齐、信息密度），气质不变，非整站换皮。可参考 `tools/ui-trial-skills/SHARED-BRIEF.md` 气质词，但不要推翻教师/管理信息架构。

## 非目标（禁止顺手做）

- 不按文件夹过滤 ask/search
- 不改入库/解析/启用权限语义（仅管理员启用）
- 不删调查 Agent（另卡）
- 不改 `.env`、不读密钥
- 不加深树

## 验收标准（可判定真假）

- [x] 前端无「目录仅用于整理…」「最多两层」「未分组」文案（git grep 无匹配）
- [x] 学生资料页不出现「检索启用/停用」；教师无每行启用开关秀；管理员仍能启用（组件渲染 / setup 操作测试）
- [x] 搜索整课文件名；有下载；无刷新按钮（源码与组件渲染验证；浏览器下载落盘未验收）
- [x] `documentFolders.js` / 相关前端测更新并通过；构建两种方式均遇环境 EPERM，见下方原始输出
- [x] 未改后端，无需 pytest / ruff

## 约束

- 复用 `FolderLibrary` / `documentFolders.js` / `documentDisplay.js`；可重构组件但保持 API
- 若下载需要 `?download=1` 查询参数以强制 attachment，可小改 `documents.py` content 端点，须测

## 禁止改动的路径

- `.env`、密钥
- RAG ask/search 主路径签名
- Agent 调查实现（另卡）
- `中期答辩材料/`

## 相关上下文（指针）

- @frontend/src/components/FolderLibrary.vue
- @frontend/src/components/StudentDocuments.vue
- @frontend/src/views/DocumentsView.vue
- @frontend/src/views/AdminDocumentsView.vue
- @frontend/src/documentFolders.js
- @backend/app/api/documents.py（content disposition）
- @docs/tasks/T-folders-ux-redesign.md

## 验证步骤（Agent 必须贴原始输出）

1. `node --test --test-isolation=none frontend/tests/documentFolders.test.mjs`（及新增测）
2. 若改 Python：定向 pytest + ruff
3. `cd frontend; npm run build`（或 `--configLoader native`）
4. git grep 确认禁用文案已消失

## 完成记录

- 实现日期：2026-10-27。
- 提交：**未生成 SHA**。精确暂存本卡前端文件时，`git add` 无法创建 `.git/index.lock`（Permission denied），因此未暂存、未提交、未 push；未覆盖会话开始时已有的无关删除和临时文件。
- 实现：
  - 复用 `FolderLibrary`，统一师生整课文件名搜索；搜索时显示全课匹配，夹选择保留，清空后回到所选夹。侧栏计数不受搜索影响。
  - 根浏览入口为「全部资料」，包含根文件与所有夹内文件；具体资料夹仍只显示直属文件。移动目标根入口单独标作「课程根目录」，避免与全课浏览混淆。
  - 保留浅树、空夹、新建 / 改名 / 换父 / 移动 / 删除空夹；保存夹和移动资料后清空搜索并定位目标。新增换父操作与移动后的定位测试。
  - 学生去除检索状态，仅显示资料夹路径、PDF 页数、打开与下载。教师只对未启用资料显示灰标，维护动作收进「更多」；移出检索沿用原 DELETE 和确认流程。管理员保留启停，增加状态筛选。
  - 师生下载复用同源 `/content` 和 `download` 文件名属性；预览继续保留 PDF 页码片段，无后端 / 权限 / 检索主路径改动。
  - 删除资料页刷新按钮和指定提示，调整侧栏宽度、搜索区、文件信息层级、表格密度和窄屏换行，沿用现有 Element Plus / 视觉 token。
  - 增加 `frontend/tests/documentFolders.test.mjs` 入口，沿用 `frontend/src/documentFolders.test.mjs`，兼容已有执行路径。
- 验证摘要：前端定向测试 **23 passed / 0 failed**；禁用文案和资料页刷新按钮 `git grep` 无匹配；`git diff --check` 通过（仅原有 LF→CRLF 提示）。未运行全量测试，未调用真实模型 / 解析 / 入库。
- 未做 / 风险：
  - 默认构建和 `--configLoader native` 均被 `spawn EPERM` 阻断，不能宣称生产构建通过。
  - Playwright CLI 本地调用因 npm 缓存目录 EPERM 不可用。随后尝试已运行的本地 Vite 浏览器页面，浏览器授权被拒，未继续访问或绕过；尚未完成真实浏览器点击、窄屏视觉和下载落盘验收。组件渲染与 setup 操作测试不能替代这些验收。
  - Git 索引不可写，本地 Conventional Commit 待具备写权限的环境完成。建议提交名：`feat(documents): library UX polish search download and retrieval badges`。

### 实际命令与原始输出摘要

仓库根执行：

```text
node --test --test-isolation=none frontend/tests/documentFolders.test.mjs
✔ folders preserve two-level order and distinguish matching child names (5.6807ms)
✔ all documents includes root files while each folder lists its direct files (1.2711ms)
✔ a list refresh race retains documents whose folder was not in the folder snapshot (0.8248ms)
✔ sidebar tree keeps two levels, direct counts, empty folders and refresh-race documents (1.3132ms)
✔ search matches filenames across the course regardless of selected folder (1.0174ms)
✔ move targets distinguish the course root from the all-documents browsing view (0.8804ms)
✔ parent targets exclude self and children; folders with children must stay at root (0.9465ms)
✔ upload uses the selected folder and an explicit retry retains its original target (163.5421ms)
✔ moving a document after polling updates the live list and opens the target folder (25.6499ms)
✔ teacher maintenance menu can remove enabled files from retrieval but cannot enable files (13.6626ms)
✔ changing a folder parent keeps its selection and does not touch document retrieval (31.3151ms)
✔ admin status filter retains explicit enable and disable operations (72.3559ms)
✔ student rendering hides retrieval state and provides same-origin named downloads (46.8167ms)
✔ shared library rendering searches the whole course and leaves folder selection intact (18.6006ms)
✔ views/DocumentsView.vue compiles its script and template (39.7427ms)
✔ components/StudentDocuments.vue compiles its script and template (12.3119ms)
✔ views/AdminDocumentsView.vue compiles its script and template (18.1177ms)
✔ components/FolderLibrary.vue compiles its script and template (13.9104ms)
ℹ tests 18
ℹ suites 0
ℹ pass 18
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 740.2731

node --test --test-isolation=none frontend/tests/documentDisplay.test.mjs
✔ page label only calls PDF source units pages (2.7761ms)
✔ coverage maps ingest state to student-friendly labels (3.8202ms)
✔ PDF content URL clamps page and non-PDF has no hash (0.6546ms)
✔ quality labels stay short regardless of file type or ingest statistics (0.6269ms)
✔ download URLs use same-origin content without a preview page fragment (0.5335ms)
ℹ tests 5
ℹ suites 0
ℹ pass 5
ℹ fail 0
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 72.3427
```

`frontend` 目录执行，以下保留错误首段和首个堆栈位置：

```text
npm run build
> univ-course-rag-frontend@0.0.0 build
> vite build
failed to load config from D:\workspace\univ-course-rag\frontend\vite.config.js
error during build:
Error: spawn EPERM
    at ChildProcess.spawn (node:internal/child_process:458:11)

npm run build -- --configLoader native
> univ-course-rag-frontend@0.0.0 build
> vite build --configLoader native
vite v7.3.6 building client environment for production...
✓ 0 modules transformed.
✗ Build failed in 271ms
error during build:
[commonjs--resolver] spawn EPERM
    at ChildProcess.spawn (node:internal/child_process:458:11)
```

仓库根执行（grep 退出码 1 表示无匹配）：

```powershell
git grep -n -E '目录仅用于整理|最多两层|未分组' -- frontend
Write-Output "banned-copy grep exit=$LASTEXITCODE"
# 原始输出：
banned-copy grep exit=1

git grep -n -E '刷新资料|刷新资料列表' -- frontend/src/components/FolderLibrary.vue frontend/src/components/StudentDocuments.vue frontend/src/views/DocumentsView.vue frontend/src/views/AdminDocumentsView.vue
Write-Output "refresh-buttons grep exit=$LASTEXITCODE"
# 原始输出：
refresh-buttons grep exit=1

git diff --check
# 无差异错误；仅 LF→CRLF 提示。
```

精确暂存尝试：

```text
git add -- frontend/src/api.js frontend/src/components/FolderLibrary.vue frontend/src/components/StudentDocuments.vue frontend/src/documentDisplay.js frontend/src/documentFolders.js frontend/src/documentFolders.test.mjs frontend/src/views/AdminDocumentsView.vue frontend/src/views/DocumentsView.vue frontend/tests/documentDisplay.test.mjs frontend/tests/documentFolders.test.mjs
fatal: Unable to create 'D:/workspace/univ-course-rag/.git/index.lock': Permission denied
```

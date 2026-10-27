# TASK: 资料库交互与展示打磨（Docs Library UX）

| 项 | 值 |
| --- | --- |
| 对应 PLAN | 资料夹/资料页演示打磨（接 T-folders-ux-redesign） |
| 状态 | ready |
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

- [ ] 前端无「目录仅用于整理…」「最多两层」「未分组」文案（可用 git grep / 测试断言）
- [ ] 学生资料页不出现「检索启用/停用」；教师无每行启用开关秀；管理员仍能启用
- [ ] 搜索整课文件名；有下载；无刷新按钮
- [ ] `documentFolders.js` / 相关前端测更新并通过；`npm run build` 通过（若环境 EPERM 记明）
- [ ] 相关 pytest（若动后端 download disposition）通过

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

- 提交：
- 验证摘要：
- 未做 / 风险：

# TASK: 资料夹交互重做（Folders UX）

| 项 | 值 |
| --- | --- |
| 对应 PLAN | 浅树资料夹增量（接 T-course-folders-shallow-tree） |
| 状态 | implemented；构建与浏览器验收受执行环境限制，待补 |
| 须授权 | 无（API 小扩展 + 前端；若仅补 parent PATCH 无新表） |

## 目标

- 在**能力边界不变**前提下，把教师/管理员资料页交互做到演示级：
  - 侧栏树或清晰树导航（根夹 / 子夹 / 未分组）
  - 建夹、改名、删空夹更顺手（Dialog/内联优于裸 `prompt`）
  - **支持换父级**（仍 depth≤2：根或一层子夹；非法深度 4xx）
  - 移动资料、空态、选夹上传体验明显好于行内 select + MessageBox.prompt
- 学生只读同树（`StudentDocuments.vue` 同步树导航，无写操作）
- 整课检索不变；**按夹限检索仍后置**

## 非目标（禁止顺手做）

- 不加深树（仍最多根+一层子）
- 不按文件夹过滤 ask/search
- 不改入库/解析/启用检索权限语义
- 不做拖拽若成本过高——可用树选目标+确认达到演示级；若实现拖拽须仍受 depth 约束
- 不做学院/主页（见另卡）

## 验收标准（可判定真假）

- [x] API：`PATCH .../folders/{id}` 支持可选 `parent_id`（含移到根 `null`）；深度与同父重名校验；有子夹的夹不能降为子夹导致第 3 层
- [x] 非空夹（含子夹或资料）删除仍 409
- [x] `DocumentsView.vue`（及必要共享组件）重做：侧栏/树 + 当前夹资料表；上传默认当前选中夹；空态友好（代码与无 DOM 行为测试；浏览器点击待补）
- [x] `StudentDocuments.vue` 只读树与资料列表一致（代码；浏览器点击待补）
- [x] 更新 `documentFolders.js` / `documentFolders.test.mjs`（及必要新测）
- [x] `backend/tests/test_course_folders.py` 覆盖换父级成功与非法深度
- [ ] ruff（若改 Python）+ `node --test --test-isolation=none` 相关测 + `npm run build` 通过

## 约束

- 跟现有 Element Plus / 教「册」token；不要另起一套皮肤
- 复用 `documentFolders.js` 分组逻辑，可扩展
- 保持 `folder_id` ON DELETE SET NULL / 拒删非空既有语义

## 禁止改动的路径

- `.env`、密钥
- RAG 检索主路径（ask/search 签名）
- Agent 合同
- 中期答辩材料/

## 相关上下文（指针）

- @docs/tasks/T-course-folders-shallow-tree.md（已落地能力；本卡只升交互 + 换父）
- @docs/结题已拍板规格.md §3 资料协作 / 资料夹交互
- 代码：`backend/app/api/folders.py`、`schemas.py`、`frontend/src/views/DocumentsView.vue`、`components/StudentDocuments.vue`、`documentFolders.js`

## 验证步骤（Agent 必须贴原始输出）

1. pytest `test_course_folders.py`
2. node documentFolders 测；npm run build
3. diff 越界检查

## 完成记录

- 提交：按本次用户要求不提交、不推送，由 bot 提交。
- 验证摘要（2026-10-27）：ruff `All checks passed!`；pytest `16 passed, 2 warnings`；node 资料夹测试 `11 pass, 0 fail`。实际命令与原始输出摘要见仓库根 `.codex-last-folders.txt`。
- 构建：`npm run build` 在 esbuild 启动子进程时报 `spawn EPERM`；补跑 `npm run build -- --configLoader native` 仍在 Vite Windows 路径探测启动子进程时报 `spawn EPERM`，未通过，未改依赖或构建配置。
- 浏览器：Playwright 工具返回 `MCP tool call requires approval, but approval policy is never`，无法完成新控件点击与视觉验收。保留此项待补，不将 SFC 编译或无 DOM 测试称为浏览器验收。
- 边界：未变更 ask/search、入库与检索权限；无迁移；树仍最多两层。共享 `FolderLibrary.vue` 与树/父级选项 helpers；失败上传保留原目标，移动完成后选中目标夹。

### PATCH 合同增量

- `name`、`parent_id` 均可独立更新；省略字段保持原值，`parent_id: null` 移至根；空请求、显式 `name: null`、非法名称/UUID 返回 422。
- 自身作父级、选择子夹作父级、含子夹的根夹降为子夹均返回 400；跨课/不存在父级返回 404；目标同父重名返回 409 并回滚。
- 资料移动只改 `folder_id`；根夹列表只展示直接资料，子夹需在目录中另选；不用于限定问答检索。

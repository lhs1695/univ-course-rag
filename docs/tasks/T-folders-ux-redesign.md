# TASK: 资料夹交互重做（Folders UX）

| 项 | 值 |
| --- | --- |
| 对应 PLAN | 浅树资料夹增量（接 T-course-folders-shallow-tree） |
| 状态 | ready |
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

- [ ] API：`PATCH .../folders/{id}` 支持可选 `parent_id`（含移到根 `null`）；深度与同父重名校验；有子夹的夹不能降为子夹导致第 3 层
- [ ] 非空夹（含子夹或资料）删除仍 409
- [ ] `DocumentsView.vue`（及必要共享组件）重做：侧栏/树 + 当前夹资料表；上传默认当前选中夹；空态友好
- [ ] `StudentDocuments.vue` 只读树与资料列表一致
- [ ] 更新 `documentFolders.js` / `documentFolders.test.mjs`（及必要新测）
- [ ] `backend/tests/test_course_folders.py` 覆盖换父级成功与非法深度
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

- 提交：
- 验证摘要：
- 未做 / 风险：

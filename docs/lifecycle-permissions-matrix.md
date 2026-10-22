# 资料生命周期与课程权限矩阵（PLAN-02）

> 更新：2026-10-22（Asia/Shanghai）
> 对应实现：`Document.retrieval_enabled`、PATCH 启停、检索过滤、删除清理；回归见 `backend/tests/test_plan02_lifecycle_permissions.py`。
> 设计借鉴：[opensource-reuse-decisions.md](opensource-reuse-decisions.md) §2.1 RAGFlow（状态分离，不迁平台）。

## 1. 资料状态约定

| 状态 | 业务记录 | chunks/向量 | 原文件 `/content` | 参与问答检索 |
| --- | --- | --- | --- | --- |
| 入库中 pending/running | 有 Document + IngestJob | 无或旧版保留至成功替换 | 视上传是否落盘 | 否（无可用新索引） |
| 成功 succeeded + enabled | 有 | 有 | 课内成员可读 | **是** |
| 成功 + **停用** `retrieval_enabled=false` | 有 | 保留 | 课内成员仍可预览 | **否**（retrieve/keyword/generate 过滤） |
| 失败 failed | 有；可 retry | 无完整新索引 | 可能仍有上传文件 | 否 |
| 已删除 | 无 | 无 | 404 | 否 |

硬删除：先清存储；存储清理失败时返回 503「Document storage cleanup unavailable」，**保留** DB 记录以便重试（不误删其他资料）。

## 2. 角色 × 课程权限（API）

| 动作 | 课内学生 | 课内教师 | 非成员 | 未登录 |
| --- | --- | --- | --- | --- |
| 列表/读资料元数据 | 允许 | 允许 | 403 | 401 |
| 读 `/content` | 允许（含停用） | 允许 | 403 | 401 |
| 上传 / retry / DELETE / PATCH 启停 | 403 | 允许 | 403 | 401 |
| 问答 ask / search | 允许（仅本课 enabled 资料） | 允许 | 403 | 401 |
| 管理成员 | 403 | 允许 | 403 | 401 |

跨课程：即使用户在 A 课是教师，访问 B 课未加入资源一律 403（成员身份非全局角色）。管理员需显式加入课程成员后才有课内权限（既有矩阵测试）。

## 3. 回归证据（本卡）

命令（仓库根）：

```text
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan02_lifecycle_permissions.py -q
```

2026-10-22 结果：`21 passed`。扩展相关套件（ask/ingest/retrieve/storage+plan02）：`194 passed, 2 skipped`。`ruff check` 通过。`frontend npm run build` 通过。

人工点检（Vite）：教师资料页「停用检索 / 启用检索」；学生库显示启停文案；未在本会话做真人浏览器点检时记为**待 PLAN-09 任务试用补证**，不以 Fake 代替。

## 4. 已知限制

- 正式库需执行 Alembic `0012` 后才有列；测试 SQLite `create_all` 已含字段。
- 停用不是版本化「历史引用快照」：旧问答日志仍可能含已停用文档的 chunk id 字符串；打开原页依赖文档仍存在。
- 并发入库压力测试未单独加压工具化；既有 lease/retry 测试覆盖误重试与兄弟资料不被误删。
# 资料生命周期与课程权限矩阵（PLAN-02）

> 更新：2026-10-26（Asia/Shanghai）
> 对应实现：`Document.retrieval_enabled`、管理员启用、教师停用、学生可见性、DELETE 软关检索；回归见 `backend/tests/test_plan02_lifecycle_permissions.py` 与 `backend/tests/test_course_business.py`。
> 设计借鉴：[opensource-reuse-decisions.md](opensource-reuse-decisions.md) §2.1 RAGFlow（状态分离，不迁平台）。

## 1. 资料状态约定

| 状态 | 业务记录 | chunks/向量 | 原文件 `/content` | 参与问答检索 |
| --- | --- | --- | --- | --- |
| 新上传 / 入库中 pending/running | 有 Document + IngestJob；默认 `retrieval_enabled=false` | 无或旧版保留至成功替换 | 已落盘时本课教师、管理员可读；学生 404 | 否（默认停用） |
| 成功 succeeded + enabled | 有 | 有 | 课内成员可读 | **是** |
| 成功 + **停用** `retrieval_enabled=false` | 有 | 保留 | 本课教师、管理员仍可预览；学生 404 | **否**（retrieve/keyword/generate 过滤） |
| 新上传失败 failed（未启用） | 有；本课教师可 retry | 无完整新索引 | 有文件时本课教师、管理员可预览；学生 404 | 否；retry 成功仍保持 false |
| DELETE 软关检索 | Document、IngestJob 保留；flag=false | 保留 | 本课教师、管理员仍可预览；学生 404 | 否；管理员可再启用 |

上传入口与 ORM 均默认停用，入库成功不会自动启用；仅管理员可 PATCH `retrieval_enabled=true`。DELETE 仅将 flag 置为 false，不触碰存储、不删除 Document/chunks/jobs/原文件，可重复调用。旧硬删除的「存储清理失败 503」已由软关替代，不再是 DELETE 路径。

## 2. 角色 × 课程权限（API）

| 动作 | 课内学生（非全局 admin） | 课内教师（非全局 admin） | 管理员（含未入课） | 非成员（非 admin） | 未登录 |
| --- | --- | --- | --- | --- | --- |
| 列表/读资料元数据 | 仅已启用；停用不列出、get 404 | 允许，含待启用/停用 | 允许，含跨课待启用/停用 | 403 | 401 |
| 读 `/content` | 仅已启用；停用 404 | 允许，含停用 | 允许，含跨课停用；无实际文件仍 404 | 403 | 401 |
| 上传 / retry | 403 | 允许；上传默认停用 | 须有真实本课 teacher 成员，否则 403 | 403 | 401 |
| PATCH 启用 true | 403 | 403 | 允许，无需入课 | 403 | 401 |
| PATCH 停用 false / DELETE 软关 | 403 | 允许，可重复停用 | 允许，无需入课 | 403 | 401 |
| 问答 ask / search | 允许，仅本课 enabled 资料 | 允许，仅本课 enabled 资料 | 仍须课程成员；未入课 403，仅 enabled 资料 | 403 | 401 |

课内角色与全局角色分别判定：课内为 student 时，全局 role 改成 teacher/admin 都不能上传或 retry；全局 admin 对资料 list/get/content/patch/delete 有例外，`require_document_access` 为其合成 teacher 成员。因此全局 admin 即使课内是 student，也可软关和启用资料；其 ask/search 可用是因为仍有真实课程成员身份。

跨课程：普通教师或学生未加入 B 课，上述资料与 ask/search 路由均 403。管理员无需入课可管理 B 课资料，但此例外**不扩散到 ask/search，也不改变 Agent 的课程教师授权**；未入课的管理员跨课 ask/search 仍 403。管理员以教师视角访问时可停用；启用始终检查全局 admin。

名单导入**不自动开户**：先由管理员建立学生账号，再导入课程名单；缺账号行返回 `student_account_missing`。业务合同与回归指针：PLAN-17（`backend/tests/test_course_business.py::test_roster_summary_idempotency_conflicts_profile`、`test_csv_partial_success_and_no_nonstudent_enrollment`）。

## 3. 回归证据（本卡）

命令（仓库根）：

```text
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan02_lifecycle_permissions.py backend/tests/test_course_business.py -q -p no:cacheprovider
backend/.venv/Scripts/python.exe -m ruff check backend/tests/test_plan02_lifecycle_permissions.py --output-format concise
git diff --check
```

证据类型：**自动化回归 2026-10-26**（M4 两步启用落地后；FakeEmbedder/FakeLLM、合成 PDF、conftest SQLite）。最终原始摘要：`44 passed, 1 warning in 24.95s`；ruff：`All checks passed!`，均退出 0。唯一 warning 为 Starlette 的 anyio `BlockingPortal` 弃用提示。本轮不修改业务代码或 `test_course_business.py`，不运行真实模型或正式库迁移。自动化通过不代表人工事实正确率。

运行环境说明：直接执行上述 pytest 命令首次得到 `20 passed, 1 warning, 24 errors in 15.05s`，PLAN-02 的 fixture 因 Windows 临时目录 `PermissionError [WinError 5]` 未执行；仅指定新的 `--basetemp` 仍被临时目录 mode=0700 的 ACL 阻断。最终使用下列进程内兼容入口，限本次临时目录采用普通目录创建模式，不改仓库配置、测试逻辑或业务权限。它执行相同两个测试文件及 `-q -p no:cacheprovider`，另指定独立临时目录；复跑时换一个全新的目录名：

```powershell
@'
import os
from pathlib import Path
import pytest

# Avoid Windows mode=0700 temporary-directory ACL failures in this process only.
temp_root = Path.cwd() / '.tmp-plan02-20261026-44d87eab'
original_mkdir = os.mkdir

def mkdir_for_test_temp(path, mode=0o777, *, dir_fd=None):
    if mode == 0o700 and Path(path).is_relative_to(temp_root):
        mode = 0o777
    return original_mkdir(path, mode, dir_fd=dir_fd)

os.mkdir = mkdir_for_test_temp
raise SystemExit(pytest.main([
    'backend/tests/test_plan02_lifecycle_permissions.py',
    'backend/tests/test_course_business.py', '-q', '-p', 'no:cacheprovider',
    '--basetemp', str(temp_root),
]))
'@ | backend/.venv/Scripts/python.exe -
```

本轮无新增 UI 控件，未做真人 Vite 点检；人工任务试用仍待 PLAN-09 补证。点检应按管理员启用、教师停用、学生仅见已启用资料的合同进行，不以 Fake 代替。

## 4. 已知限制

- 正式库 Alembic head 为 `0015`（当前已拍板口径；本轮未连接正式库核验）；`0012` 是 retrieval_enabled 的历史迁移，其已有记录回填和 server default 回归保留，不能用该历史默认值替代当前上传/ORM 默认 false 的合同。测试 SQLite `create_all` 已含字段。
- 停用不提供版本化「历史引用快照」：旧问答日志仍可能含已停用文档的 chunk id 字符串；软关后学生打开原页为 404，本课教师、管理员仍可读取保留文件。
- 并发入库压力测试未单独加压工具化；既有 lease/retry 测试覆盖误重试，本轮核对软关时兄弟资料文件与 chunks 不变。

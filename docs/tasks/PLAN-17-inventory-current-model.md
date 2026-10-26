# PLAN-17 现有数据模型与权限盘点

> 范围：只记录当前代码可见的数据字段、关联和服务端权限，用于 PLAN-17 首项验收。本文不是目标 schema，也未修改模型、迁移或 API。
> 核对日期：2026-10-26。

## 现有数据结构

| 对象 | 当前字段 | 关联 / 说明 |
| --- | --- | --- |
| `users` | `id`、`username`、`password_hash`、`role`、`created_at` | 角色值为 `student`、`teacher`、`admin`。ORM 明确声明 `sessions` 关系；课程成员、资料、问答日志通过外键关联用户，但 `User` 上没有对应 ORM 关系。没有姓名、学号或个人资料字段。 |
| `courses` | `id`、`title`、`created_at` | `Course.members` 与 `CourseMember.course` 建立双向关系。没有学期或班级字段，也没有学期关联。 |
| `course_members` | `id`、`course_id`、`user_id`、`role` | 外键分别指向 `courses.id`、`users.id`；同一课程与用户组合唯一。角色是课程内 `teacher` 或 `student`。这是直接的课程成员关系，没有班级关联或名单来源字段。 |
| `documents` | `id`、`course_id`、`uploaded_by`、`filename`、`storage_path`、`retrieval_enabled`、`source_unit_count`、`extracted_char_count`、`chunk_count`、`quality_warning`、`chunking_version`、`created_at` | 外键关联课程及上传用户。`retrieval_enabled` ORM 默认值和数据库默认值均为 `true`。无管理员启用者、启用时间或软删除字段。 |
| `ingest_jobs` | `id`、`document_id`、`status`、`run_token`、`error_message`、创建/更新时间 | 外键指向资料；记录解析任务状态。 |
| `query_logs` | `id`、`course_id`、`user_id`、`query`、`hit`、`outcome`、`member_role_at_ask`、`error_code`、`chunk_ids`、`duration_ms`、`created_at` | 外键关联课程和用户；存有原始问题及查询结果元数据。模型没有声明与 Course/User 的 ORM relationship。个人主页规格不得因此展示提问历史。 |

上表依据 [User 模型](../../backend/app/models/user.py)、[Course 与 CourseMember 模型](../../backend/app/models/course.py)、[Document 模型](../../backend/app/models/document.py)、[QueryLog 模型](../../backend/app/models/query_log.py)。

## 当前接口权限与业务行为

认证通过 HTTP-only Cookie Session；`/auth/me` 返回用户 ID、用户名和角色。`require_admin` 检查全局 `users.role == admin`；`require_course_member` 要求存在 `course_members` 记录，`require_course_teacher` 再要求该成员的课程角色为教师。全局管理员身份本身不会绕过课程成员检查。

| 操作 | 当前服务端规则 | 与拍板目标的差异 |
| --- | --- | --- |
| 全站账号 | 管理员可经 `/admin/users` 列出和创建账号；返回字段为 ID、用户名、角色。 | 目前无姓名、学号等资料字段；无管理员更新/删除账号接口可见于该 API。 |
| 课程与成员 | 管理员可创建、列出、修改、删除课程并管理成员；本课教师可查看成员、添加或移除本课学生。 | 添加成员依赖已有用户账号，未提供 CSV 学号/姓名/班级导入。 |
| 课程访问 | 登录用户只能列出自己已加入的课程；课程资料列表、详情、内容读取要求课程成员。教师能力按课程成员角色判定。 | 还没有课下行政班、班级成员或学生归属班级的表达。 |
| 资料上传/查看 | 本课教师可上传；课程成员可列出、查看资料及读取原文件。本课教师可重试解析、修改 `retrieval_enabled`、删除资料。 | 上传时即创建解析任务，资料 `retrieval_enabled` 默认为 `true`；PATCH 由课程教师控制启停。已有检索软禁用开关，但没有“教师上传 → 管理员可见 → 管理员启用检索”的分权两步流程，也没有独立软删除字段。 |
| 学期管理 | 当前没有学期模型或学期 API。 | 需增加名称、起止日期及课程到学期的关联。 |
| 个人主页 | `/auth/me` 仅返回 ID、用户名、角色。 | 需展示姓名、学号、角色、所属班级；不得展示查询历史。 |

权限核对依据：[认证与当前用户依赖](../../backend/app/api/auth.py)、[权限依赖](../../backend/app/security/deps.py)、[课程 API](../../backend/app/api/courses.py)、[管理员课程 API](../../backend/app/api/admin_courses.py)、[管理员用户 API](../../backend/app/api/users.py)、[资料 API](../../backend/app/api/documents.py)。

## 相对 PLAN-17 最小范围的缺口

- **学期：** 现有 Course 没有 semester 外键；缺少带名称与起止时间的学期数据对象及管理接口。
- **班级与名单：** 当前课程成员仅表示“用户加入课程”。缺少课下行政班、班级关联、学生学号/姓名，以及 CSV（学号/姓名/班级）校验、重复处理和导入摘要。
- **个人资料：** User 与 `/auth/me` 缺少姓名、学号；也没有所属班级查询结果。查询日志独立保存原始问题，不应纳入个人主页。
- **资料两步启用：** 当前上传即以可检索默认值创建资料并排队解析；管理员没有专属资料查看/启用接口，课程教师拥有启停权限。目标需明确管理员可见范围与启用动作，并保证启用前普通检索和 Agent 来源不可读作证据。
- **禁用与删除：** `retrieval_enabled=false` 已可软禁用检索；当前删除端点会删除资料记录、解析任务及 chunks，成功后清理上传文件，没有独立软删除状态。后续应复用检索禁用开关，并在设计阶段确定删除行为的兼容边界。

以上仅为代码现状与规格差异清单。后续应先确定复用 `users`、`courses`、`course_members` 的最小字段/关联及权限，再决定迁移；本文未执行迁移、代码改动、正式库操作或名单导入。

## M4 实现后的最小数据关系（2026-10-26）

上文保留为 M1 起始盘点；本节为 M3 提交 `4587421` 之后的 M4 实现，不能再把上文的缺口表当当前状态。迁移 revision `0015`，仅隔离验证。

| 对象 | M4 增量 / 关联 |
| --- | --- |
| users | 可空 `full_name`、唯一可空 `student_number`；管理员维护；旧账号仍用原用户名/密码/Session 登录。名单不另造身份。 |
| semesters | 名称唯一、starts_on/ends_on，DB 与 API 均检查起止；管理员维护。 |
| courses | 可空 `semester_id` 指向一个学期；保留旧课程无学期兼容。 |
| course_classes | course_id + 班级名课内唯一；同名班可存在于不同课程；无全站行政组织树。 |
| course_members | 可空 `class_id`；`(class_id, course_id)` 复合外键确保班级属于本课，CHECK 限 student 可归班。CSV 同时建立原有成员关系与班级关联；移出课程会清除班级归属。 |
| documents | ORM、DB、新上传默认 retrieval_enabled=false；旧值保留；仅管理员可置 true；教师可在本课置 false。DELETE 关闭检索、保留原文/chunks/jobs，不另建审批层。 |

| 操作 | 学生 | 教师 | 管理员 |
| --- | --- | --- | --- |
| 姓名/学号、全站账号维护 | 拒绝 | 拒绝 | 允许 |
| 学期 CRUD / 课程挂学期 | 拒绝 | 拒绝 | 允许；在用学期不可删除 |
| 班级 CRUD / CSV 名单 | 拒绝（含本课成员） | 仅课内 teacher 成员 | 指定课程可操作；班级仍不可跨课串用 |
| 个人主页 | 只读本人 | 只读本人 | 只读本人 |
| 资料待启用列表/详情/原文 | 不可见 | 仅本课 teacher | 跨课可见，无需加入课程 |
| 上传 / 重试入库 | 拒绝 | 仅本课 teacher | 沿用课内 teacher 授权要求 |
| 启用检索 | 拒绝 | 拒绝 | 允许 |
| 停用 / 软移出检索 | 拒绝 | 仅本课 teacher | 允许 |
| 普通检索 / 问答 / Agent | 原有成员权限；只读启用证据 | 原有成员/teacher 权限；只读启用证据 | 不因资料管理权限绕过课程成员 / Agent teacher 校验 |

管理员资料例外封装于 documents API，不改通用课程/Agent 依赖。名单只匹配已有学号及姓名：缺账号逐行拒绝，由管理员补建再导入；不自动修改身份、换班或创建可预测密码。已存在同班成员重导 unchanged；同 CSV 重复学号全部拒绝；有效行一起提交，约束并发冲突整体回滚 409。详见 [实现、验证与未做项](PLAN-17-course-business-foundation.md#m4-实现与复用2026-10-26)。

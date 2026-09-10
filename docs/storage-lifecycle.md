# 阶段 30 / 39：上传文件生命周期与读取合同

日期：2026-09-10

## 路径边界

上传文件统一由 `backend/app/services/storage.py` 管理，目标结构固定为：

```text
<upload_dir>/<course_uuid>/<document_uuid>/<safe_filename>
```

- 根目录、课程目录、资料目录和最终文件都先经过 `resolve()`。
- 删除单资料时，目标不仅必须位于 upload root，还必须位于请求对应的课程 UUID 与资料 UUID 目录；数据库中的越界或串课 `storage_path` 会被拒绝。
- 上传文件名必须等于其 basename，拒绝 `..` 等路径穿越形式。
- 删除课程时只递归清理 upload root 下该课程 UUID 对应的目录；符号链接若解析到根目录外会被边界检查拒绝。

## 受鉴权读取

阶段 39 新增 `GET /courses/{course_id}/documents/{document_id}/content`。请求必须先通过现有 Cookie Session 和课程成员权限检查；随后存储服务再次验证数据库中的 `storage_path` 位于请求对应的 upload root、课程 UUID 和资料 UUID 目录，且目标确实为文件。越界、串课、缺失或非文件目标统一返回不可用，不回显完整本机路径。

- PDF、Markdown、纯文本使用 `inline`，便于浏览器核对原文；PDF 引用可使用 chunk 的可信页码附加 `#page=`。
- PPTX、DOCX 使用 `attachment`，只下载原文件，不承诺浏览器预览或页内定位。
- 响应使用白名单 MIME、受控文件名和 `X-Content-Type-Options: nosniff`；上传根目录从未注册为公开静态目录。
- Vite 开发代理只对精确的 `/courses/.../content` 请求绕过课程 SPA fallback，使开发期同源 Cookie 仍由 FastAPI 鉴权。

## 数据库与文件的提交顺序

上传采用“先落盘、后提交数据库”。如果数据库提交失败，API 回滚数据库并补偿删除刚写入的文件及空目录；文件写入本身失败时，存储服务也会尝试删除部分文件。

删除采用“先提交数据库、后清理文件”。这样文件系统故障不会让已经删除的数据库对象假装仍可使用。清理失败时 API 保持删除成功语义，同时记录：

```text
storage_cleanup_failed scope=<document|course|upload_compensation> course_id=... document_id=... error_type=...
```

日志不记录文件内容，也不输出完整存储路径。当前本机原型依靠该错误进行人工补偿；若未来变成多实例正式部署，应改为持久化 outbox/清理任务，而不是在请求内无限重试。

## 清理范围

- 删除单资料：删除文件，再清理空的资料目录和课程目录；同课程其他资料不受影响。
- 删除课程：数据库提交成功后清理该课程完整上传树，包括此前遗留的孤儿文件；其他课程目录不受影响。
- 路径不可信：不执行越界删除，只记录可观测错误。

## 验证

Fake/SQLite 测试覆盖路径穿越、upload root 越界、课程内串路、单资料删除、课程级删除与课程隔离、上传数据库失败补偿，以及数据库删除成功后文件清理失败日志。阶段 39 追加同课教师/学生读取、未登录、非成员、跨课、越界/缺失路径、MIME/disposition 和引用 URL 测试；`test_storage.py` 与 `test_ask.py` 合计 30 passed，Ruff 和前端构建通过，没有调用云服务。

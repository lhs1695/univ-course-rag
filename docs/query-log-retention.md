# 提问日志留存与维护

`QueryLog` 含提问原文，只用于课程内的描述性学情聚合。学情 API 只读取当前留存窗口内的记录，即使管理员尚未运行清理，到期记录也不会继续出现在学情结果中。

本机通过 `.env` 配置：

- `QUERY_LOG_RETENTION_DAYS`：默认 90 天，允许 1–3650 天。
- `QUERY_LOG_CLEANUP_BATCH_SIZE`：默认 100 条，允许 1–1000 条。

仅管理员可调用 `POST /admin/query-logs/retention`。先发送 `{"mode":"dry_run"}` 查看本批命中数；确认后发送 `{"mode":"delete"}` 删除同样规则下按 `created_at, id` 排序的最旧一批。响应的 `has_more` 为 `true` 时，可继续逐批 dry-run 和删除。维护日志只写模式、数量和是否仍有下一批，不写提问、用户、Cookie 或 Session 内容。

该操作只删除当前应用数据库中的记录，不能立即从已有数据库备份、快照或其他外部副本中抹除。恢复备份时仍需按其独立生命周期和访问控制处理其中的历史日志。

# observation 2026-10-27 admin delete 概率论与统计学

- course_id: `0f1798bd-010b-45ac-b6ea-352e046c282c`
- title: 概率论与统计学
- before counts: `{"documents": 12, "chunks": 1512, "ingest_jobs": 12, "course_members": 2, "course_folders": 0, "query_logs": 78, "agent_tasks": 0, "insight_reviews": 0, "course_classes": 0}`
- upload_dir exists before: False files=0 path=`corpus\local\cn-replace-2026-10-18\rechunk\uploads_v2\0f1798bd-010b-45ac-b6ea-352e046c282c`
- admin list contains title before: True
- DELETE /admin/courses/{id} status: 204
- admin list contains title after: False
- remaining titles: ['人力资源管理', '教育学原理', '线性代数', '机器学习', '智能移动机器人']
- course row remains: 0
- after counts: `{"documents": 0, "chunks": 0, "ingest_jobs": 0, "course_members": 0, "course_folders": 0, "query_logs": 0, "agent_tasks": 0, "insight_reviews": 0, "course_classes": 0}`
- upload_dir exists after: False files=0
- wall_time_utc: 2026-10-27T01:29:48.360405+00:00
- PASS: True

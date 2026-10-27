# observation 2026-10-27 admin delete 人力资源管理

- course_id: `e7ba1d17-ec14-4a7c-ba2c-fe15015ee151`
- title: 人力资源管理
- before: documents=8, chunks=267
- DELETE `/admin/courses/{id}` status: **204**
- after titles: 教育学原理、智能移动机器人、机器学习、线性代数（**4**）
- after HR documents/chunks: **0 / 0**；course 行不存在
- demo totals after: **29 docs / 1506 chunks**
- student `/courses` titles: 教育学原理、线性代数、机器学习、智能移动机器人
- pedagogy content 6/6 = 200
- PASS: True
- note: 删课前曾因 Docker/Postgres 未起导致 API login 超时；已 `docker compose up -d postgres` 并重启 uvicorn:8000。未 push。

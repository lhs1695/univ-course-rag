# observation-2026-10-27-pedagogy-content-path

更新：2026-10-27（Asia/Shanghai）

## 现象

学生能列出「教育学原理」资料，但无法打开/查看原文（content 404）。

## 原因（非 retrieval_enabled）

- 课内成员、6 份资料、`retrieval_enabled=true`、ingest `succeeded`、chunks 均正常。
- `GET .../documents/{id}/content` 走 `get_document_upload`，要求 `storage_path` 落在 `upload_dir/<course>/<doc>/` 内。
- 旧三课（教育学原理 6、人力资源管理 8、线性代数 1）的 `storage_path` 仍指向仓库根 `D:\workspace\univ-course-rag\corpus\...`，而当前 `upload_dir` 解析为 `D:\workspace\univ-course-rag\backend\corpus\...`，触发 `StorageBoundaryError` → 404。
- 机器学习/智能移动机器人路径已在 backend corpus 下，不受影响。Ask/检索仍可读 chunk，故表现为「能问不能打开原文」。

## 处理

- 将 15 份文件 copy 到 `upload_dir/<course_id>/<doc_id>/<filename>`，并 UPDATE `documents.storage_path`。
- 学生登录复验教育学原理 6/6 content HTTP 200（PDF）。
- 本记录不提交密钥；未改产品边界校验语义。

## 未做

- 未改 `storage.py` 边界规则；未把绝对路径改为相对路径存储（可另卡）。

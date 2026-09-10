# 第五期交接：下一阶段 35

已完成：阶段 30 已集中实现受 upload root、课程 UUID 和资料 UUID 共同约束的存储服务；上传提交失败会补偿清理，单资料与课程删除覆盖文件生命周期，清理失败写入不含完整路径的可观测日志。合同见 `docs/storage-lifecycle.md`。

阶段 31 已实现：显式真评测每题经原子替换保存安全 checkpoint，`--resume` 仅接受题集 SHA-256、课程 ID、embedding backend/model 与 LLM backend/model 都相同的未完成 checkpoint。异常题只保留 `evaluation_error`、异常类别和固定安全摘要；恢复跳过完成题、重试异常题；最终成功输出仍是原有 `summary`、`failures`、`metadata`。

维护者确认当前没有非开发者试用者，因此第五期已立项，不再让阶段 25 阻塞独立技术改进。阶段 32 已完成：后端在落盘/建库前稳定拒绝旧二进制 PPT/DOC；解析分派、文件选择器、README、demo、intent 与中期材料均收敛为 PDF、PPTX、DOCX、Markdown、纯文本。`test_ingest.py`（18 passed）、Ruff 和前端构建已通过；教师资料页的格式提示与上传控件已实际点击一次。

阶段 33 已完成：Alembic 0007 为 `sessions.expires_at` 增加索引；登录仅创建新 Session 时执行一次按到期时间排序、受 `SESSION_CLEANUP_BATCH_SIZE`（默认 100、范围 1–1000）限制的过期 Session 清理，并与新 Session 同次提交。受保护请求仍仅校验自身 Session，过期和畸形 Cookie 都稳定返回未认证；清理日志只记录删除数量。`test_auth.py`、Ruff，以及本机 Postgres 的 0007 upgrade → downgrade → upgrade 已通过，最终为 head。

阶段 34 已完成：SiliconFlow 与 DeepSeek 客户端都使用受 `UPSTREAM_TIMEOUT_SECONDS`（默认 20 秒、范围 1–60）和 `UPSTREAM_MAX_RETRIES`（默认 2、范围 0–3）限制的超时/重试配置；供应商异常统一收敛为不含原始响应、query、prompt 或 key 的 `UPSTREAM_UNAVAILABLE`。问答遇到该异常会记录稳定分类并返回 503，不会伪装成 `NO_EVIDENCE`；入库任务安全失败、不产生半套新 chunk，仍可通过既有受控入口重试。`test_ask.py`、`test_ingest.py`（33 passed）与 Ruff 已通过。下一会话只做 `docs/plan-5.md` 阶段 35，不提前做请求关联/readiness 或 CI。

待显式授权：阶段 24 的旧真评测结果基于修复前删除仿真，仍保留为历史证据。只有再次明确允许联网和计费时才重跑，不把云调用并入普通测试。

并行等待：阶段 25 仍缺至少一名未参与开发的试用者。获得匿名记录后，再整理七类问题并判断阶段 18/19；在此之前不能宣称第四期真人试用收口。

留存：阶段 20–24、26–31 已完成；阶段 25 等待外部；第五期阶段 32–37 已获计划授权但仍须一次会话只做一个阶段；不提前实施阶段 18/19，不默认 push。

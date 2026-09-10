# 第六期启动交接

第六期计划见 [`plan-6.md`](plan-6.md)，主线是本机产品可解释性、数据边界与效果证据。阶段 38 已完成：Alembic 0008 为资料增加含文本来源单元数、抽取字符数、切片数和稳定质量警告码；三个计数仅在新切片事务成功替换时一起更新，失败会保留旧索引和旧指标。`INGEST_LOW_TEXT_CHARS` 默认 200、范围 1–5000；成功但偏短只提示“问答依据可能不完整”，完全无可抽取文本仍明确失败。资料 API 不返回正文、切片或存储路径；教师资料页显示质量信号，并为失败任务接入已有受权限和租约约束的重试入口。

阶段 38 的 `test_ingest.py`（32 passed）、Ruff、Vite 构建和本机 Postgres 的 0008 upgrade → downgrade → upgrade 已通过，最终为 head。已用专用临时数据库与安全夹具实际点击一次“重试”：页面从失败变为成功，显示 1 个含文本单元、140 个抽取字符、3 个切片和低文本提示；临时数据库与 Playwright 产物已删除。下一阶段为 **39 引用到原资料的受鉴权追溯**。第六期不做部署、云资源、OCR 或模型调参。阶段 25 继续等待非开发者试用，阶段 18/19 保持未触发。

阶段 39 已完成：新增 `GET /courses/{course_id}/documents/{document_id}/content`，必须先通过课程成员鉴权，再按 upload root、课程 UUID、资料 UUID 验证数据库存储路径。PDF、Markdown 和纯文本以内联方式返回，PPTX/DOCX 只作为附件下载；响应使用明确 MIME、受控文件名、`Content-Disposition` 和 `X-Content-Type-Options: nosniff`。越界、串课、缺失或非文件路径统一安全失败，不公开上传目录。引用响应携带当前课程内的相对资料 URL；PDF 链接附加可信 chunk 页码的 `#page=`，其他格式不伪造页内定位。Vite 对 `/courses/.../content` 不再走 SPA fallback，而是代理到 FastAPI。

阶段 39 的 `test_storage.py`、`test_ask.py`（合计 30 passed）、Ruff 和 Vite 构建已通过。已用专用临时数据库、安全 PDF 夹具和 FakeEmbedder/FakeLLM 实际点击一次“查看原资料”，同一 Cookie 会话在新标签进入受鉴权 PDF URL，并保留 `#page=1`；未登录直接访问返回 401。临时数据库、测试上传目录和 Playwright 产物已删除。下一阶段为 **40 提问日志留存与有界维护**。

## 已收口的第五期

已完成：阶段 30 已集中实现受 upload root、课程 UUID 和资料 UUID 共同约束的存储服务；上传提交失败会补偿清理，单资料与课程删除覆盖文件生命周期，清理失败写入不含完整路径的可观测日志。合同见 `docs/storage-lifecycle.md`。

阶段 31 已实现：显式真评测每题经原子替换保存安全 checkpoint，`--resume` 仅接受题集 SHA-256、课程 ID、embedding backend/model 与 LLM backend/model 都相同的未完成 checkpoint。异常题只保留 `evaluation_error`、异常类别和固定安全摘要；恢复跳过完成题、重试异常题；最终成功输出仍是原有 `summary`、`failures`、`metadata`。

维护者确认当前没有非开发者试用者，因此第五期已立项，不再让阶段 25 阻塞独立技术改进。阶段 32 已完成：后端在落盘/建库前稳定拒绝旧二进制 PPT/DOC；解析分派、文件选择器、README、demo、intent 与中期材料均收敛为 PDF、PPTX、DOCX、Markdown、纯文本。`test_ingest.py`（18 passed）、Ruff 和前端构建已通过；教师资料页的格式提示与上传控件已实际点击一次。

阶段 33 已完成：Alembic 0007 为 `sessions.expires_at` 增加索引；登录仅创建新 Session 时执行一次按到期时间排序、受 `SESSION_CLEANUP_BATCH_SIZE`（默认 100、范围 1–1000）限制的过期 Session 清理，并与新 Session 同次提交。受保护请求仍仅校验自身 Session，过期和畸形 Cookie 都稳定返回未认证；清理日志只记录删除数量。`test_auth.py`、Ruff，以及本机 Postgres 的 0007 upgrade → downgrade → upgrade 已通过，最终为 head。

阶段 34 已完成：SiliconFlow 与 DeepSeek 客户端都使用受 `UPSTREAM_TIMEOUT_SECONDS`（默认 20 秒、范围 1–60）和 `UPSTREAM_MAX_RETRIES`（默认 2、范围 0–3）限制的超时/重试配置；供应商异常统一收敛为不含原始响应、query、prompt 或 key 的 `UPSTREAM_UNAVAILABLE`。问答遇到该异常会记录稳定分类并返回 503，不会伪装成 `NO_EVIDENCE`；入库任务安全失败、不产生半套新 chunk，仍可通过既有受控入口重试。`test_ask.py`、`test_ingest.py`（33 passed）与 Ruff 已通过。

阶段 35 已完成：PPTX/DOCX 在打开前按可配置的 ZIP 条目数、总解压大小、单条目大小和压缩比做资源预算；PDF/幻灯片解析受页/幻灯片上限与累计抽取字符上限约束。所有阈值均有本机环境配置的合理上下界；超限以稳定、不含课件正文的失败摘要结束，不写入新 chunk，原有完整索引继续保留。`test_ingest.py` 用程序生成 ZIP/PPTX/DOCX 覆盖所有限制、旧索引保持和正常 PDF/PPTX/DOCX 成功（28 passed），Ruff 已通过。

阶段 36 已完成：每个 HTTP 请求生成或校验最多 64 字符的 `X-Request-ID`，在响应头回传并写入应用日志记录/完成日志；非法外部值会替换，日志不记录 query、课件正文、Cookie 或 key。`/health` 保持不访问数据库的 liveness；新增 `/ready` 仅执行 `SELECT 1`，数据库异常时稳定返回 `503 {"status":"unavailable"}`，不调用 embedding/LLM。`test_health.py`、`test_auth.py`（16 passed）与 Ruff 已通过。

阶段 37 已完成：新增 [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)，以 Python 3.12、FakeEmbedder/FakeLLM、pgvector/Postgres 迁移与显式检索证明、以及前端 lockfile 构建为门禁；不读云 key、不调真模型、不上传语料或数据库。已本地完成 Alembic upgrade/seed 和 `RUN_POSTGRES_TESTS=1` 证明、全量 Fake pytest（92 passed、2 skipped）、Ruff 与 Vite 构建；Docker Desktop 已成功启动 compose Postgres，并再次完成迁移/seed 与检索证明。提交 `4b805e9` 已推送，远端 GitHub Actions CI 已成功完成。

待显式授权：阶段 24 的旧真评测结果基于修复前删除仿真，仍保留为历史证据。只有再次明确允许联网和计费时才重跑，不把云调用并入普通测试。

并行等待：阶段 25 仍缺至少一名未参与开发的试用者。获得匿名记录后，再整理七类问题并判断阶段 18/19；在此之前不能宣称第四期真人试用收口。

留存：阶段 20–24、26–31、第五期阶段 32–37 与第六期阶段 38、39 已完成；阶段 25 继续等待外部。不要提前实施阶段 18/19，不默认 push；下一阶段只按 `plan-6.md` 实施阶段 40。

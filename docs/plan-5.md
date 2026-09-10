# Plan：univ-course-rag 第五期

状态：阶段 36 已完成；下一阶段为 37；主线 **单机可运维性与失败边界**
日期：2026-09-09
对照：第四期阶段 20–24、26–31 已完成；阶段 25 因没有非开发者试用者继续等待，但不阻塞第五期独立技术工作。

**施工纪律：** 一次会话只做一个阶段。当前阶段证明优先于惯例；不默认全量测试、不默认调用云服务、不默认 push。课件、问题和切片仍是不可信文本；key、真课件、本地数据库和逐题真评测结果不得进 Git。

权威顺序：本计划 > `docs/decisions/` > `docs/intent.md`。Cookie session、Postgres + pgvector、FakeEmbedder/FakeLLM、单次检索 + 单次生成以及无 LangChain/RAGFlow 骨架均为冻结事实，不重开选型。

---

## 1. 为什么继续做

现有系统已经能完成课程权限、多格式资料入库、课内检索、带引用回答、拒答、教师学情和真模型评测；继续堆 RAG 功能的边际价值较低。当前更值得补的是后端工程边界：格式承诺必须真实、Session 表不能无限增长、云依赖失败不能直接变成不透明 500、压缩文档解析必须有资源预算、运行状态应可诊断，且仓库需要可重复的自动化门禁。

第五期仍是本机/单实例项目加固，不宣称已经满足校园网生产部署。目标是形成可解释、可测试、可恢复的 Python 后端实践证据。

## 2. 本期目标

1. 让上传格式白名单与解析器真实能力一致，不再把旧二进制 `.ppt` / `.doc` 宣称为已支持。
2. 有界回收过期 Session，并为到期查询建立数据库索引。
3. 为 embedding/LLM 配置显式超时与有限重试；供应商异常转换为稳定、脱敏、可记录的失败契约。
4. 限制 OOXML 压缩包和解析后文本的资源消耗，阻止小文件解压为超大内容。
5. 增加不泄露用户内容的请求关联标识与数据库 readiness，区分“进程活着”和“依赖可用”。
6. 建立包含 Python、迁移、Postgres 检索证明和前端构建的 CI 门禁。

## 3. 分阶段

### 阶段 32 — 上传格式合同校正（已完成）

- **做：** 后端上传白名单与解析分派只接受真实支持的 `.pdf`、`.pptx`、`.docx`、`.md`、`.markdown`、`.txt`；明确拒绝 python-pptx/python-docx 无法解析的旧二进制 `.ppt` / `.doc`。同步前端 accept、页面文案、README、demo 与 intent 中的格式描述。错误保持短、稳定且不回显文件内容。
- **不做：** 不调用 LibreOffice 做隐式转换；不新增系统级依赖；不把扩展名检查夸大为完整恶意文件检测；不做阶段 35 的压缩资源预算。
- **证明：** `test_ingest.py` 覆盖 `.ppt` / `.doc` 在落盘和创建数据库记录前返回 400，现有 PDF/PPTX/DOCX/文本测试保持通过。运行 `pytest backend/tests/test_ingest.py`、仓库根 `python -m ruff check`、前端 `npm run build`，并只点击一次更新后的上传控件。

### 阶段 33 — Session 生命周期与有界回收（已完成）

- **做：** 迁移 0007 为 `sessions.expires_at` 增加索引；实现按到期时间排序、单次有上限的清理函数。登录创建新 Session 时执行一批清理，批量上限由有界配置控制；当前请求发现自身 Session 过期时仍只判未认证，不在每个受保护请求上扫描全表。日志只记录删除数量，不记录 Cookie 或 Session ID。
- **不做：** 不改成 JWT；不把 session 放入 `localStorage`；不引入 Redis 或定时任务平台；不做全表无界删除。
- **证明：** `test_auth.py` 覆盖有效 Session 不受影响、过期 Session 被分批删除、超过上限留待后续批次、畸形 Cookie 不触发异常。0007 在本机 Postgres 完成 upgrade、downgrade、再次 upgrade，最终为 head；运行 `pytest backend/tests/test_auth.py` 与 Ruff。

### 阶段 34 — 云依赖超时与稳定失败契约（已完成）

- **做：** 为 SiliconFlow 与 DeepSeek 客户端增加显式超时和有限重试配置，配置值有合理上下界；适配器将供应商特定异常收敛为不含原始响应、query、prompt 或 key 的内部异常。在线问答遇到 embedding/LLM 不可用时记录稳定的 `UPSTREAM_UNAVAILABLE` 遥测并返回 503；不得伪装成 `NO_EVIDENCE`。入库沿用 failed 状态与安全摘要，重试仍由阶段 29 的受控入口触发。
- **不做：** 不无限重试；不自动切换 Fake 或其他供应商；不把云错误正文返回浏览器；不在 pytest 调真 API。
- **证明：** `test_ask.py` 用 Fake 故障对象覆盖 embedding 与 LLM 异常、503 契约、QueryLog 分类和日志脱敏；`test_ingest.py` 覆盖供应商异常后任务 failed、无半套新切片且可显式重试。运行这两个测试与 Ruff。

### 阶段 35 — 解析资源预算与压缩炸弹防护（已完成）

- **做：** 在打开 PPTX/DOCX 前检查 ZIP 条目数、总解压大小、单条目大小和异常压缩比；解析过程限制页/幻灯片数量与累计抽取字符数，阈值进入有界配置。超限统一进入可识别的解析失败，不产生 chunk；现有 15 MiB 上传上限继续保留。
- **不做：** 不做杀毒扫描、OCR、宏执行或沙箱转换；不承诺同进程 Python 能强制终止所有第三方解析器；真正的进程级解析超时留待部署范围确定后评估独立 worker。
- **证明：** `test_ingest.py` 使用程序生成的安全小夹具覆盖条目数、解压总量、压缩比和抽取字符上限；断言失败无 chunk、旧完整索引不被破坏、正常 PPTX/DOCX/PDF 继续成功。运行 `pytest backend/tests/test_ingest.py` 与 Ruff。

### 阶段 36 — 请求关联与 readiness（已完成）

- **做：** 为每个 HTTP 请求生成或校验长度受限的 request ID，响应头回传，并让应用日志携带该 ID；日志继续禁止 query、课件正文、Cookie 和 key。保留 `/health` 作为纯进程 liveness，新增只检查数据库轻量查询的 `/ready`；readiness 不调用收费云服务，数据库不可用时返回 503 与稳定响应。
- **不做：** 不接入第三方 APM、Prometheus 集群或日志平台；不在健康检查里调用 embedding/LLM；不输出用户身份或完整路径。
- **证明：** `test_health.py` 覆盖 liveness 不访问数据库、readiness 成功/失败、请求 ID 生成与非法外部值替换；`test_auth.py` 抽查受保护请求也回传关联 ID。运行这两个测试与 Ruff。

### 阶段 37 — 可重复 CI 门禁与第五期收口

- **做：** 新增 GitHub Actions：Python 3.12 安装 `backend/.venv` 等价依赖，运行 Ruff 和全部 Fake pytest；启动 pgvector/Postgres，执行 Alembic upgrade head 并显式运行 Postgres 检索测试；Node 安装使用 lockfile，运行前端构建。更新 README、INDEX、NEXT-SESSION 与第五期结果，明确阶段 25 仍未被开发者测试替代。
- **不做：** CI 不读取云 key、不运行真模型评测、不上传本地语料或数据库、不自动部署、不自动 push/tag。
- **证明：** 本地先运行工作流对应命令；GitHub Actions 在干净提交上全部通过，日志不含密钥或真实内容。若当前环境没有远端或未授权 push，只提交工作流并记录“远端未执行”，不能伪称 CI 已绿。

## 4. 开工顺序与停止条件

**32 格式合同（已完成）→ 33 Session 回收（已完成）→ 34 云失败边界（已完成）→ 35 解析资源预算（已完成）→ 36 可观测性/readiness（已完成）→ 37 CI 收口**。

每个阶段通过自己的证明后本地提交并停止，不跨阶段施工。阶段 25 继续等待外部试用者；在没有真实反馈时，阶段 18、19 仍不触发。真评测只有维护者再次明确允许联网和计费时才运行。

第五期完成后不自动进入生产部署。Cookie Secure/HTTPS、数据库备份恢复、持久化任务队列、多实例文件存储和进程级解析隔离，只有部署目标、主机和运维责任明确后才能另立第六期。

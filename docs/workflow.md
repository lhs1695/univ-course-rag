# 开发与运行工作流

更新：2026-10-19。任务以 [施工计划](implementation-plan.md) 为准，下一步见 [当前交接](当前交接.md)。本文件只保留有效操作规则。

> **口径说明（2026-10-19）：** 正式演示库为 `univ_course_rag_cn_v2`（中文四课 27 份 PDF / 2,501 chunks）；下文若出现 17 份 / `r7b6_real` / `univ_course_rag`，均为 R7B 历史口径。

## 会话与变更

1. 先检查 Git 状态，保护已有未提交修改；只读当前项直接相关代码、合同和测试。禁止 reset/checkout/restore 覆盖用户未提交工作；禁止把无关文件批量 add；禁止默认 push、部署或创建外部任务。
2. **任务卡验收通过后本地 Conventional Commit**；纯报告且无文档/代码改动可不提交。仍须用户明确点名才 push。
3. 一次完成一个实现项；文档清理单独执行。小改由本项目 coding bot 直接做；其余走 Codex CLI（实现 6.1sol / 子代理 6.1luna，思考中）。开源选型由维护者决定；只有真实云调用、较大依赖/模型下载、数据库迁移等有实际成本时再向用户确认。
4. 实现前完成复用决策；实现后只运行当前项和 diff 直接影响的检查，更新受影响合同、计划与交接。
5. Python 使用 backend/.venv；UI 改动运行 frontend 的 npm run build，新增控件实际点击一次。已有 pytest 行为不在浏览器重复。
6. 纯文档只核对事实、引用/锚点与 git diff --check，不运行产品测试。汇报区分本次验证与尚未验证事项。

<a id="reuse-gate"></a>

## 复用决策

默认顺序：直接调用成熟 API/组件 → 合法源码复用改造 → 必要本地实现。允许独立框架组件进入运行时，不为几个函数机械引入整个平台，也不为复制比例重写短小已验证适配。

每项在现有 engineering 或施工计划记录：具体对象与版本/commit、许可、实际采用方式、接入/迁移/维护成本、剩余本地工作和验收。只有参考链接不能算接入；自写须比较现成对象的实际不适配之处。

分词、BM25、重排、解析等算法优先直接复用；本地保留课程授权、ID/索引映射、生命周期、上限与错误适配。**PDF 生产默认路径已是 PyMuPDF 原生文字提取与页级质量门禁；Docling 全量主解析路线已停止。** R7B-L1…L3、R7B-5、R7B-6B/6C、R7B-7、R8 与 P7-3 恢复子项均已完成；R9 已收口（final-v5 + 彩排 PASS + 中期答辩材料）。正式演示库 `univ_course_rag_cn_v2`；具体步骤见 [中期演示运行卡](中期演示运行卡.md)。不再启动新的解析器选型循环。OCR/公式/视觉仅针对确认的具体页面另立任务。R7B 历史实施步骤与门槛见 [轻量解析计划](implementation-plan.md#r7b-lightweight-plan) 和 [validation](validation.md#r7b-parser-selection)。复制源码保留原声明；不扩大为通用检索、模型或插件框架。

开源“抄作业”以最小复用单元为准：优先调用成熟 API/CLI，其次参考稳定的数据结构或适配代码，最后才复制短小且许可证明确的必要源码。每次复制必须保留原版权/许可证声明并记录来源 commit。不要复制整仓库、默认配置、模型权重或第三方素材；模型和权重的许可单独核对。

<a id="environment-preflight"></a>

## 分层前检

| 层 | 按当前项检查 | 不能据此宣称 |
| --- | --- | --- |
| Fake 开发 | 项目解释器、直接依赖、dotenv 禁用、SQLite/Fake/受控夹具；必要时 --version、pip check | 真实语义效果或云服务可用 |
| 本机联调 | Docker 引擎、目标库、迁移、端口、上传目录及 Vite 代理 | 供应商连通、真实索引正确或答案正确 |
| 真实调用 | 当次授权与预算、供应商/模型、兼容索引、有限样例、超时/重试/停止条件 | 通用课程效果、独立用户试用已完成 |

不为 Fake 工作默认启动全栈、读取 .env 或索取 key。后端多数依赖尚未完整锁定；正式实验前记录可恢复的依赖约束，不把未经筛选的整机 pip freeze 当项目依赖。

## 环境与启动

**中期演示：** 目标库必须是 `univ_course_rag_cn_v2`（默认 `.env.example` 已对齐）；课件 `UPLOAD_DIR=corpus/local/cn-replace-2026-10-18/rechunk/uploads_v2`。完整步骤与固定问句见 [中期演示运行卡](中期演示运行卡.md)。勿再切 `r7b6_real` / 旧 `univ_course_rag` 做答辩演示。

后端只用 backend/.venv，禁止系统 Python/默认 Conda。已有环境不重复创建；新环境使用 Python 3.12：

```powershell
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e "./backend[dev]"
```

只有需要本机数据库时才启动 Docker。先在仓库根执行：

```powershell
docker compose up -d
```

核对目标实例、配置来源和恢复点后，在 backend 目录执行迁移与 seed：

```powershell
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m app
```

当前代码需要迁移至0011（新增问答结果/课内角色快照；旧行不回填）。R7 新隔离库已现场应用并保存恢复包；其他目标库是否已应用仍须分别核验。seed 只补不存在账号，不重置密码；不使用 down -v 或删卷重建环境。

仓库根启动后端：

```powershell
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

frontend 使用 npm ci（新锁文件环境）和 npm run dev；正常运行不升级全部依赖。浏览器登录使用 Vite 实际地址，经代理访问后端，保持 localhost/127.0.0.1 一致，不直连后端端口登录。/health 仅进程存活，/ready 仅 SELECT 1，/runtime 仅本地配置/数据库状态；configured 不代表连通。

## AI 编程与环境

本机工作区 D:\workspace\univ-course-rag 是项目权威工作区；最终 Git 状态、测试、资料、结果和验收均以本机工作区为准。一个工作树同一时刻只允许一个写入型 coding agent 施工，其他 Agent 只能研究、只读检查或 review。

Codex CLI、Cursor 等本机 coding agent 可在 Windows 原生或 WSL2 使用；默认优先与最终中期演示一致的本机 Windows 环境。只有已选工具出现明确兼容 blocker 时才考虑 WSL2，不因 Docling 的性能问题迁移环境或重跑任务。WSL2 中的 venv、node_modules 与 Windows 原生环境分开，不跨环境直接复用二进制环境目录。

Grok Bot 的 hosted computer 是独立的云 Linux 工作区，不是本机 D:\workspace。若用 Grok Bot 做辅助开发，只允许把它当可恢复的远程副本/研究环境：优先同步代码与合成/公开测试资料，真实四课资料、数据库恢复包、.env、Cookie 和其他本机受控数据默认不上传；远程改动必须回到本机工作区通过 Git diff、测试和实际验收后才算项目事实。不要让 Grok Bot 与本机 Cursor/Codex 同时修改同一工作树。

## 配置与数据

| 用途 | 当前字段/约束 |
| --- | --- |
| 向量 | EMBEDDER_BACKEND、EMBEDDING_MODEL、EMBEDDING_BASE_URL、SILICONFLOW_API_KEY；索引身份必须兼容 |
| 生成 | LLM_BACKEND、DEEPSEEK_MODEL、DEEPSEEK_BASE_URL、DEEPSEEK_API_KEY；显式选择 Fake 或真实，不缺配置回落 |
| 重排 | RERANKER_BACKEND 默认 disabled；siliconflow 只与 hybrid 组合，使用现有 SiliconFlow key；model/base_url 决定模型与发送目的地 |
| 候选问题组 | QUESTION_GROUPING_BACKEND默认disabled；embedding仅复用已配置SiliconFlow嵌入；独立POST须明确阈值和本次外发确认。页面加载、刷新和时间筛选只请求GET；教师填写阈值并勾选确认后才POST。普通统计不调用模型，不使用Fake词项哈希作语义 |
| Session | HTTP-only session_id 与服务端 Session；本机 HTTP 的 Secure Cookie 配置须相容 |
| 资源 | 上游超时/有限 SDK 重试、嵌入批次、解析与日志留存上限；具体合同见 engineering |

当前配置读取根 .env 与 backend/.env，进程环境也可能覆盖。默认不读取它们；确需维护时不输出 key 前后缀、Cookie、URL 认证信息、Settings dump 或环境列表，不擅自删除配置。修改后重启后端；模板 .env.example 不是实际配置已就绪的证明。

课件、问题和切片均为不可信数据。真实资料、原题/答案、原始输出、结构化解析产物、隔离数据库与恢复副本留受控忽略区。用户已确认当前受控四课资料中的第三方内容可用于本项目，版权提示不作为 R7B 排除或入库阻断条件；来源、文件哈希和页码仍须记录以支持复现。依赖或开源模型下载、公开资料核对不等于计费模型调用授权。真实 embedding/LLM/视觉/reranker 调用需当次明确联网/计费授权，限定数据、次数、重试和停止条件，不循环试 key；浏览器取消不能保证云调用或计费停止。

代码、数据库、上传文件和配置分别恢复。受控迁移或正式评测前保存必要恢复副本，明确来源映射与访问权限。旧索引不会自动获得新来源元数据；选定资料受控重新入库，成功才原子替换，失败保留旧索引。HTTP retry 不支持已成功资料重建，不自动放宽状态或删除重传。维护者可为明确选中文档创建 pending 任务并调用现有 process_ingest_job，实际云嵌入仍需当次授权。

## 文档与删除

固定六份：workflow 管操作，implementation-plan 管施工（含 R7B 唯一步骤叙述），当前交接 管当前交接，engineering 管现行合同/复用许可，validation 管验收方法，evaluation-results 管已跑数字与运行日志。README 只导航，AGENTS 管协作，新开题资料管研究目标。

文档不再累积旧阶段报告、旧评测数字、逐次测试流水或过时汇报。中期前按改进后的版本重新建基线、跑数据；旧数字不补作新结果。保留仍有效的许可与现行合同，修复引用；过时说明可迁入 `docs/archive/`，不另写阶段报告冒充现行口径。

删除文件须使用明确工作区清单，核对绝对路径与重解析点；Windows 使用 Remove-Item -LiteralPath，不递归清空。文档清理不触碰 .git、.env、依赖环境、测试夹具、corpus/local 或数据库。搜索限定当前项路径，排除 .venv/node_modules、构建产物和真实资料。

## 实验与交付

PyMuPDF 轻量入口、页级质量门禁、固定代表页核对、历史 17 份离线冻结与 R7B-7 英文四课基线均已完成（历史）；**当前正式演示**为中文四课 `univ_course_rag_cn_v2`（4/27/2501）+ PPT **final-v5** + 彩排 PASS，见 [evaluation-results](evaluation-results.md)、[当前交接](当前交接.md)、[中期答辩材料](../中期答辩材料/README.md)。Docling 全量冻结停在 8/17，不续跑。弱规则 / AI 预标**不能**冒充人工事实正确率。R8 / P7-3 / R9 已通过或收口；产品下一阶段待用户定。若另称独立试用，仍须非开发者实际独立完成。



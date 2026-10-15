# 开发与运行工作流

更新：2026-10-15。任务以 [施工计划](implementation-plan.md) 为准，下一步见 [当前交接](NEXT-SESSION.md)。本文件只保留有效操作规则。

## 会话与变更

1. 先检查 Git 状态，保护已有未提交修改；只读当前项直接相关代码、合同和测试。不 reset、不批量 add/commit，不默认 push、部署或创建外部任务。
2. 一次完成一个实现项；文档清理单独执行。已授权的常规工作直接完成，需要关键选择时带具体方案与取舍询问。
3. 实现前完成复用决策；实现后只运行当前项和 diff 直接影响的检查，更新受影响合同、计划与交接。
4. Python 使用 backend/.venv；UI 改动运行 frontend 的 npm run build，新增控件实际点击一次。已有 pytest 行为不在浏览器重复。
5. 纯文档只核对事实、引用/锚点与 git diff --check，不运行产品测试。汇报区分本次验证与尚未验证事项。

<a id="reuse-gate"></a>

## 复用决策

默认顺序：直接调用成熟 API/组件 → 合法源码复用改造 → 必要本地实现。允许独立框架组件进入运行时，不为几个函数机械引入整个平台，也不为复制比例重写短小已验证适配。

每项在现有 engineering 或施工计划记录：具体对象与版本/commit、许可、实际采用方式、接入/迁移/维护成本、剩余本地工作和验收。只有参考链接不能算接入；自写须比较现成对象的实际不适配之处，“方便控制/以后扩展”不足以单独证明必要。

分词、BM25、重排、解析等算法优先直接复用；本地保留课程授权、ID/索引映射、生命周期、上限与错误适配。复制源码保留原声明；材料如实区分直接调用、源码改造、设计参考与本地实现。不扩大为通用检索、模型或插件框架。

<a id="environment-preflight"></a>

## 分层前检

| 层 | 按当前项检查 | 不能据此宣称 |
| --- | --- | --- |
| Fake 开发 | 项目解释器、直接依赖、dotenv 禁用、SQLite/Fake/受控夹具；必要时 --version、pip check | 真实语义效果或云服务可用 |
| 本机联调 | Docker 引擎、目标库、迁移、端口、上传目录及 Vite 代理 | 供应商连通、真实索引正确或答案正确 |
| 真实调用 | 当次授权与预算、供应商/模型、兼容索引、有限样例、超时/重试/停止条件 | 通用课程效果、独立用户试用已完成 |

不为 Fake 工作默认启动全栈、读取 .env 或索取 key。后端多数依赖尚未完整锁定；正式实验前记录可恢复的依赖约束，不把未经筛选的整机 pip freeze 当项目依赖。

## 环境与启动

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

当前代码需要迁移至0011（新增问答结果/课内角色快照；旧行不回填），实际目标库是否已应用须现场核验。seed 只补不存在账号，不重置密码；不使用 down -v 或删卷重建环境。

仓库根启动后端：

```powershell
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

frontend 使用 npm ci（新锁文件环境）和 npm run dev；正常运行不升级全部依赖。浏览器登录使用 Vite 实际地址，经代理访问后端，保持 localhost/127.0.0.1 一致，不直连后端端口登录。/health 仅进程存活，/ready 仅 SELECT 1，/runtime 仅本地配置/数据库状态；configured 不代表连通。

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

课件、问题和切片均为不可信数据。真实资料、原题/答案、原始输出、隔离数据库与恢复副本留受控忽略区；依赖安装/公开资料核对不等于计费模型调用授权。真实 embedding/LLM/reranker 调用需当次明确联网/计费授权，限定数据、次数、重试和停止条件，不循环试 key；浏览器取消不能保证云调用或计费停止。

代码、数据库、上传文件和配置分别恢复。受控迁移或正式评测前保存必要恢复副本，明确来源映射与访问权限。旧索引不会自动获得新来源元数据；选定资料受控重新入库，成功才原子替换，失败保留旧索引。HTTP retry 不支持已成功资料重建，不自动放宽状态或删除重传。维护者可为明确选中文档创建 pending 任务并调用现有 process_ingest_job，实际云嵌入仍需当次授权。

## 文档与删除

固定六份：workflow 管操作，implementation-plan 管施工，NEXT-SESSION 管当前交接，engineering 管现行合同/复用许可，validation 管验收方法，evaluation-results 管重新评测的来源与结果登记。README 只导航，AGENTS 管协作，新开题资料管研究目标。

文档不再累积旧阶段报告、旧评测数字、逐次测试流水或过时汇报。中期前按改进后的版本重新建基线、跑数据；旧数字不补作新结果。保留仍有效的许可与现行合同，修复引用，不新增历史归档目录或阶段报告。

删除文件须使用明确工作区清单，核对绝对路径与重解析点；Windows 使用 Remove-Item -LiteralPath，不递归清空。文档清理不触碰 .git、.env、依赖环境、测试夹具、corpus/local 或数据库。搜索限定当前项路径，排除 .venv/node_modules、构建产物和真实资料。

## 实验与交付

中期前以改进后的实际工作区和固定配置重新入库/评测，保存可恢复基线；HEAD 不等于含未提交修改的当前版本。开发集选参数，测试集封存，模型/切分/检索/回答机制分别比较，失败和降级不删。独立试用由非开发者实际完成，不代操作；材料在版本和新结果冻结后制作。当前文档清理本身不执行任何真实重跑或部署。

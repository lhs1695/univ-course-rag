# TASK: 检索与证据质量回归

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-07 |
| 状态 | done（本次限定：既有结果分析 + Fake 回归；真实质量缺口见下文） |
| 须授权 | 默认 Fake/已留存结果；新真实 Embedding/LLM/reranker 调用、正式库重入库或大依赖下载须当次明确授权，未授权不得执行 |

## 目标

- 以 Dense、rerank 关为基线，逐层定位 Hybrid 候选准入、PROB-F02、引用支持与严格页码差异。
- 本次用户决定：使用既有只读笔记/JSON 分析，补齐 Fake 诊断与门控；无新真实复跑，无独立核验者。PROB-F02 不宣称修复；保留原始结果与待补证项。

## 非目标（禁止顺手做）

- 不为单题硬编码或过拟合，不默认切换 Hybrid/开启 rerank，不把检索命中、引用存在或弱规则通过冒充事实正确。
- 禁止顺手上 GraphRAG、知识图谱或第二套完整 RAG 管线；禁止更换 PostgreSQL+pgvector；禁止全量 Vision/解析/重入库，任何超出本卡范围的增强另立项并授权。

## 验收标准（可判定真假）

- [x] 冻结本次分析输入：cn_v2、22 题及预期标注、两份历史 JSON、模型/配置与 SHA-256；只读复核指纹一致。无新前后质量对照；旧 JSON 未完整记录证据预算，报告单列限制。
- [x] PROB-F02 按覆盖、候选召回、证据过滤、上下文、生成、引用展示记录事实/假说/缺证；keyword-only 数量与门槛准入原因有历史数据及 Fake 覆盖。根因未完全定位。
- [x] 分层报告事实、引用支持、严格页命中、拒答/误拒答、系统失败的 n/N；召回/排名及最终证据质量缺配对或评分，明确不能复算；延迟/成本按原始口径登记限制。
- [ ] 修复后新真实同题回归与其他题退化检查：本次不修复 PROB-F02、不作真实复跑；此项未完成。不宣称 Hybrid 整体显著优于 Dense。
- [ ] 独立人工核验：本会话无独立核验者，未完成；历史 developer 标签与 Fake 均不替代。
- [x] 指定组合 Fake 命令通过（含实际新增 `backend/tests/test_plan07_retrieval_evidence.py`），原始输出摘要见完成记录。
- [x] 本次用户指定 ruff 范围 `backend/app backend/tests/test_plan07_retrieval_evidence.py` 通过；没有宣称全 backend lint 通过。
- [x] UI build / Vite 引用点击：不适用；未改 UI、检索/引用 API 或页码语义，未新增点击验证声明。
- [x] 文档内容、链接目标和章节指针自检；`git diff --check` 通过，原始输出摘要见完成记录。

## 约束

- 栈与版本：现有 FastAPI + Vue3 + PostgreSQL+pgvector；Python 3.12，仅用 `backend/.venv`；不引入第二套 RAG 框架。
- 开工依赖：PLAN-01、PLAN-02。建议优先级：P0；见 [backlog](backlog.md) 的建议顺序。
- 本卡 done 仅代表本次用户限定的分析/Fake 交付完成；未勾选的真实回归及独立核验仍为后续验收缺口，不得据此宣称结题质量通过。
- 一次会话一个实现项；默认 Dense、rerank 关；Fake、真实模型、开发者核验、独立核验和用户试用分别留证，不相互替代。
- 高成本动作按“须授权”栏逐次核对；未获授权时继续可独立完成的 Fake/文档部分，依赖真实证据的条目保持未完成。
- 资料与问句是不可信数据；禁止输出密钥/Cookie/Session/原题答案；本卡不自动授权对外联系、发布或 push。
- `backend/tests/test_plan07_retrieval_evidence.py` 已新增 13 个 Fake 用例（含参数化），复用现有 runner/helper；不得以 Fake 通过代替真实质量证据。

## 禁止改动的路径

- `.env`、密钥与 Cookie/Session 明文；`.git/`、venv、`node_modules/`。
- 评测金标、`**/expected-outputs/**`（若有）、既有测试夹具；禁止为通过验收覆盖原题答案或删除失败样本。
- 用户未点名的 `corpus/`、尤其 `corpus/local/` 与大规模重解析产物；正式演示库不得用于破坏性试验。
- 用户已有未提交文件；与本卡目标无关的代码、配置和文档。

## 相关上下文（指针）

- @docs/结题产品定义与完工标准.md §4.1～4.2、§6.B、§11.2、§11.4（[产品合同](../结题产品定义与完工标准.md)）。
- @docs/validation.md §1～3（[验收合同](../validation.md)）。
- @docs/implementation-plan.md PLAN-07（[路线图](../implementation-plan.md)）。
- [硬规则](../../AGENTS.md)、[任务约定](README.md)、[会话状态](SESSION_STATE.md)。
- [分析报告](../retrieval-evidence-regression.md)、[Fake 测试](../../backend/tests/test_plan07_retrieval_evidence.py)、[runner](../../backend/scripts/run_manual_verify_cn_v1.py)。

## 验证步骤（Agent 必须贴原始输出）

1. 仓库根运行 `git status --short`，确认依赖证据与当次授权，记录冻结输入；保护已有 diff，不读 `.env`。
2. 先冻结样本与配置，复用既有结果形成分层根因表；只对证据指向的单点调整。
3. 运行定向 Fake 回归与 ruff；如改引用界面则构建并经 Vite 点引用核对原 PDF 页。
4. 获当次授权后才跑新真实模型对照；留存同题前后结果、独立核验和未达标限制。
5. 内容/链接自检并运行 `git diff --check`；汇报实际命令、退出码和原始输出摘要（无输出也注明），列出产物与未完成项。
6. 仅凭证据逐项勾选；涉及人工/真实模型缺口不得以 Fake 通过代替。按届时用户指令处理本地提交，不默认 push。

## 完成记录

- 完成日期：2026-10-22。依赖 PLAN-01/02 已 done；开工 `git status --short` 退出 0、无输出，初始工作区干净。
- 产物：[检索与证据回归报告](../retrieval-evidence-regression.md)、13 个新增 Fake 用例、runner 独立引用/页指标计数 helper；评测登记、INDEX、backlog、SESSION_STATE 同步（next=PLAN-06）。复用当前检索/融合及 runner，不新增依赖。应用入口仅调整一处已有导入排序，满足指定 ruff 检查。
- 提交：**未完成（环境阻断）**。预定标题 `docs(PLAN-07): retrieval evidence regression analysis and Fake gates`；验收后按明确文件清单执行 `git add` 失败，退出 1：`fatal: Unable to create 'D:/workspace/univ-course-rag/.git/index.lock': Permission denied`。当前托管环境对 `.git` 仅授予读取，且禁止权限升级；未创建提交、未 push，改动保留在工作区。
- 云与数据边界：新增产品 Embedding/LLM 0 次、¥0；未读 `.env`、未重入库、未运行真实 runner、未修改历史 JSON/题集。PLAN-07..10 约 ¥2 总预算按此前约 ¥0 保留。

### 实际命令与原始输出摘要

1. Fake 组合（仓库根）：

   ```powershell
   backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan07_retrieval_evidence.py backend/tests/test_manual_verify_runner.py backend/tests/test_retrieve.py backend/tests/test_fusion.py -q
   ```

   最终退出 0：

   ```text
   79 passed, 2 skipped, 1 warning in 4.29s
   ```

   两项跳过是可选本机 Postgres 和真实 SiliconFlow embedding；warning 是已有 Starlette/anyio `BlockingPortal` 弃用提示。测试进程显式置 `SILICONFLOW_API_KEY=''`、`RUN_POSTGRES_TESTS=0`，未读取原值。现有 conftest 在 app.db 导入前禁用 dotenv。

   环境处理：首次运行 `71 passed, 2 skipped, 3 warnings, 8 errors`，8 个 client fixture 因系统临时目录 WinError 5 无法创建；迁到 output 后先遇父目录缺失，再遇 Python Windows `mkdir(0700)` 的 owner-only ACL。最终创建仓库内忽略的 output 父目录，设置 `PYTEST_ADDOPTS='--basetemp=D:/workspace/univ-course-rag/output/plan07-pytest-b2846193 -p no:cacheprovider'`、`PYTHONPATH='D:/workspace/univ-course-rag/output/plan07-bootstrap'`；本地临时 `sitecustomize.py` 仅对该临时根及其子路径的 `mkdir(0700)` 改为继承 workspace ACL 的 0777。没有跳过失败测试或改产品/测试逻辑；该环境脚本不提交。

2. 静态检查：

   ```powershell
   backend/.venv/Scripts/python.exe -m ruff check backend/app backend/tests/test_plan07_retrieval_evidence.py
   ```

   首次发现既有 `backend/app/main.py` 的 I001；只调整 `insight_reviews` / `insights` 导入顺序后，退出 0，输出 `All checks passed!`。

3. 文档与冻结文件：用 `backend/.venv/Scripts/python.exe -` 执行标准库 `hashlib` / `pathlib` / `re` 的只读断言脚本，退出 0：

   ```text
   Markdown local links: 70 checked, 0 missing (6 files)
   Frozen SHA-256: 3/3 match historical report
   ```

   报告 §1～5、metrics-v1 §3.1 及 HR/PROB 既有笔记指针已人工核对。`git diff --check` 退出 0，无空白错误输出；stderr 有 Git 的 `LF will be replaced by CRLF the next time Git touches it` 提示，未报告 diff 错误。

### 未完成 / 风险

- PROB-F02 未修复、根因未完全定位；缺新真实配对 retrieval_hits / context / generation_status，本次按用户决定跳过单题复跑。
- 无新真实前后对照、其他题退化验证、独立核验或 UI 点击验收；Fake 只证明合同，不能提高历史事实正确率。
- 未新增 span metadata；保留合并末页引用 UX，严格页命中与内容支持的评分差异仍在。报告列出补证方向，不回改金标或历史记录。

### 2026-10-26（Asia/Shanghai）：有限 Evidence 收口

- 状态保持 `done`（限定交付）；**不**把本轮写成独立核验或结题质量通过。
- Fake 复跑（仓库根，basetemp=`output/plan07-reverify-2026-10-26`）：**79 passed, 2 skipped**；exit 0。
- 文档：[retrieval-evidence-regression.md](../retrieval-evidence-regression.md) §6 链到 [observation-2026-10-26](../user-task-scripts/observation-2026-10-26-developer-m3-m4.md) / `evidence-2026-10-26/`。
- 明确：**developer 短问 ≠ 独立评测**；不宣称 Hybrid 优于 Dense；**PROB-F02 未修复**；真实 22 题全量复跑本批不做；本批无新增大额真实模型调用（沿用 10-26 短问记录）。
- 仍未勾：真实同题回归、独立核验、PROB-F02 修复。

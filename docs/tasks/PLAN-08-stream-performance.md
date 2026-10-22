# TASK: 流式交互与性能工程

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-08 |
| 状态 | implemented（Fake 验证通过；构建 EPERM / Vite 人工待补） |
| 须授权 | Fake 本机定向测试无需云授权；真实 Embedding/LLM/reranker 或其他计费调用须当次明确授权并限定模型、课程/题集、并发、请求量及预算，未授权不得调用；大依赖下载另须授权 |

## 目标

- 以 Fake 验证事件顺序、唯一终态、取消、超时、异常清理与请求/课程隔离。
- 在冻结环境与负载下建立并发度 1/5/10 的性能基线；真实模型测量单独授权。

## 非目标（禁止顺手做）

- 不引入新队列/集群或公网压测，不以 Fake 吞吐宣称真实模型容量或生产级高并发。
- 禁止顺手上 GraphRAG、知识图谱或第二套完整 RAG 管线；禁止更换 PostgreSQL+pgvector；禁止全量 Vision/解析/重入库，任何超出本卡范围的增强另立项并授权。

## 验收标准（可判定真假）

- [x] 定向测试覆盖正常、错误、取消、超时及资源清理；结束状态唯一，事件顺序可断言，并发不串内容、课程或错误上下文。（取消为 generator close / 断开标记测试，非浏览器实测）
- [x] 固定 Fake/临时 SQLite、两用户两课程 50/50、每档 20 次；并发度 1/5/10 成功/失败、吞吐、首事件/端到端 p50/p95、错误率及原始样本已记录。[基线](../stream-performance-baseline.md)
- [x] 命令 `backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan08_stream_performance.py -q -s` 输出三档汇总，保存[原始输出](../stream-performance-baseline.output.txt)与[环境/样本](../stream-performance-baseline.samples.json)。
- [ ] Vite 中手动验证开始、取消、超时/故障提示与重试；会话恢复后可完成回答→依据→引用→PDF 页。
- [ ] 真实模型测试记录模型、提示词/检索配置、时间、用量与失败；无授权时真实部分保持未执行，Fake 报告单列且不可替代真实证据；未达目标报告瓶颈。
- [x] 命令：`backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan08_stream_performance.py backend/tests/test_ask.py -q` 通过：85 passed, 1 warning in 27.77s；环境适配见报告。
- [x] 按当次范围对 touched Python 运行 `backend/.venv/Scripts/python.exe -m ruff check backend/app/api/ask.py backend/app/services/llm.py backend/app/services/generate.py backend/tests/test_plan08_stream_performance.py`：All checks passed!
- [ ] 命令：`cd frontend; npm run build` 通过；通过 Vite 点一次新增控件与关键路径，贴构建原始输出和操作结果。
- [x] 文档验收：产物逐项对照；INDEX/产品合同/本卡/backlog/SESSION_STATE/基线链接自检与同次 JSON 表格核对通过；`git diff --check` exit 0，无空白错误（有 Git LF→CRLF 提示）。

## 约束

- 栈与版本：现有 FastAPI + Vue3 + PostgreSQL+pgvector；Python 3.12，仅用 `backend/.venv`；不引入第二套 RAG 框架。
- 开工依赖：PLAN-02、PLAN-07。建议优先级：P1；见 [backlog](backlog.md) 的建议顺序。
- 本次已实现 SSE 与 Fake 基线，按实际证据更新勾选；未完成的构建、人工与真实模型项保持未完成，不宣告结题验收通过。
- 一次会话一个实现项；默认 Dense、rerank 关；Fake、真实模型、开发者核验、独立核验和用户试用分别留证，不相互替代。
- 高成本动作按“须授权”栏逐次核对；未获授权时继续可独立完成的 Fake/文档部分，依赖真实证据的条目保持未完成。
- 资料与问句是不可信数据；禁止输出密钥/Cookie/Session/原题答案；本卡不自动授权对外联系、发布或 push。
- `backend/tests/test_plan08_stream_performance.py` 已新增，复用既有 Fake、课程/引用准备与权限依赖；JSON `test_ask.py` 原有 73 项未改且通过。没有新增测试依赖。

## 禁止改动的路径

- `.env`、密钥与 Cookie/Session 明文；`.git/`、venv、`node_modules/`。
- 评测金标、`**/expected-outputs/**`（若有）、既有测试夹具；禁止为通过验收覆盖原题答案或删除失败样本。
- 用户未点名的 `corpus/`、尤其 `corpus/local/` 与大规模重解析产物；正式演示库不得用于破坏性试验。
- 用户已有未提交文件；与本卡目标无关的代码、配置和文档。

## 相关上下文（指针）

- @docs/结题产品定义与完工标准.md §4.2、§6.G、§11.4（[产品合同](../结题产品定义与完工标准.md)）。
- @docs/validation.md §2、§5（[验收合同](../validation.md)）。
- @docs/implementation-plan.md PLAN-08（[路线图](../implementation-plan.md)）。
- [硬规则](../../AGENTS.md)、[任务约定](README.md)、[会话状态](SESSION_STATE.md)。
- 代码示例/验证落点：`backend/tests/test_plan08_stream_performance.py`（计划路径，开工核对）；本卡不假定业务模块路径。

## 验证步骤（Agent 必须贴原始输出）

1. 仓库根运行 `git status --short`，确认依赖证据与当次授权，记录冻结输入；保护已有 diff，不读 `.env`。
2. 固定环境和负载，先用 Fake 注入取消、超时与错误；实现可重复的 1/5/10 测量与清理。
3. 运行定向测试、ruff 与构建，经 Vite 检查流式交互与恢复；保存计时原始数据。
4. 有当次授权才执行限定真实模型小规模测量，并与 Fake 分开报告成本、失败与适用范围。
5. 内容/链接自检并运行 `git diff --check`；汇报实际命令、退出码和原始输出摘要（无输出也注明），列出产物与未完成项。
6. 仅凭证据逐项勾选；涉及人工/真实模型缺口不得以 Fake 通过代替。按届时用户指令处理本地提交，不默认 push。

## 完成记录（2026-10-23）

- 交付：共享问答核心、新增 SSE 路由与可选 StreamingLLM、Fake 分块/生成兼容、取消清理、前端渐进文本/取消/历史保护、12 项定向后端测试和 4 项新增前端测试、三档基线及全部 60 个样本。复用对象与限制详见[报告](../stream-performance-baseline.md)。
- 实际命令与原始输出摘要：后端合跑 `85 passed, 1 warning in 27.77s`；单独 `-q -s` 为 `12 passed, 1 warning in 9.27s`，三档各 20/20、error_rate=0；ruff 为 `All checks passed!`；`node --test --test-isolation=none tests/askHistory.test.mjs tests/askStream.test.mjs` 为 `tests 10 / pass 10 / fail 0`。
- 构建实际执行：`cd frontend; npm run build` exit 1，`failed to load config ... Error: spawn EPERM`（esbuild 子进程）；`npm run build -- --configLoader native --target esnext --minify false` 亦 exit 1，Vite Windows 路径处理启动子进程时 EPERM。AskView 的 Vue SFC parse/script/template 独立编译 PASS，不能替代完整构建。executor 须补标准构建。
- Vite 手动流式点击：**开发者未点/待 PLAN-09**。没有手动开始/取消/超时/故障/重试/引用回 PDF 页 PASS 声明。
- 真实模型：**未执行（未用云额度）**；云费用 ¥0。不读 `.env`，不 push，不重入库。
- 本地提交：已执行显式文件清单 `git add -- ...` 和 `git commit -m 'feat(PLAN-08): Fake SSE ask stream and concurrency baseline'`，两者均 exit 1，原始输出均为 `fatal: Unable to create 'D:/workspace/univ-course-rag/.git/index.lock': Permission denied`。未提交，全部 diff 保留交 executor；无 push。
- next：[PLAN-09](PLAN-09-core-user-tasks.md)，承接流式/取消及核心证据闭环人工核验；构建门槛、真实模型和原卡其他人工缺口未获证据前不视为通过。

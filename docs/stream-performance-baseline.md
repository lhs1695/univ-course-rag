# PLAN-08：Fake 流式问答与并发基线

执行：2026-10-23 00:12（Asia/Shanghai）；原始时间戳见 [逐请求样本与环境](stream-performance-baseline.samples.json)，[pytest -s 原始输出](stream-performance-baseline.output.txt)。云调用与费用：0 / ¥0。

## 接口与实现边界

- 后端实际 router 前缀为 `/courses`，没有 `/api` 挂载前缀；新增 `POST /courses/{course_id}/ask/stream`，Vite 使用相同地址代理。既有 JSON `POST /courses/{course_id}/ask`、权限依赖、检索规则、引用准入和 QueryLog 合同共用原有问答核心。
- SSE 的 `data:` 均为 JSON：`phase`（retrieve/generate）、`delta`（text）、`final`（完整 AskResponse）或 `error`（error_code/message）。正常流只有一个终态；无依据为唯一 `final`，上游超时/故障为唯一 `error`。鉴权/参数校验在流开始前返回既有 HTTP 错误。客户端主动取消没有终态承诺。
- `StreamingLLM` 是可选 Protocol，FakeLLM 实现 12 字符分块，拼接等于 `generate()`。现有真实 LLM 适配器只有 `generate()`，走一次生成后分块的兼容路径；本卡没有增加真实调用。
- 为保留既有引用校验与有限重试语义，生成内容先保存在**请求局部**，通过校验并确定最终采用回答后才发送 delta；不会向浏览器展示未采纳的重试文本或 NO_EVIDENCE 字样。阶段事件即时发送，但本实现不承诺模型 token 到达即展示，也未证明首字延迟改善。
- 复用现有 FastAPI/Starlette `StreamingResponse`、AnyIO 线程池与 fetch/ReadableStream，无新增依赖或队列。线程池逐步推进同步迭代器，provider chunk 间检查断开；关闭流会关闭 provider 迭代器、清空局部片段并 rollback 未提交事务。同步检索或 generate 调用中途无法强制中断，当前调用按既有上游超时/重试设置结束后清理。已提交日志不会因随后取消而撤销。
- 前端 askHistory 保持课程内 pending/重复提交保护与跨页面请求归属；delta 渐进显示，final 接入既有引用卡片。取消按钮 abort controller；取消/故障释放 pending，可显式重试。切换身份/退出清理时 abort 所有旧请求并丢弃晚到事件。

## 冻结负载与计时定义

| 项 | 本次定义 |
| --- | --- |
| 环境 | Windows 11 / 10.0.26300，16 逻辑 CPU；Python 3.12.10（backend/.venv） |
| 依赖 | FastAPI 0.141.1 / Starlette 1.6.0 / Uvicorn 0.52.4 / httpx 0.28.1 / SQLAlchemy 2.0.52 |
| 运行 | 同一主机，单 Uvicorn 服务线程，127.0.0.1 临时端口，HTTP/1.1；未启动生产服务 |
| 数据 | 临时 SQLite 文件，每请求独立 Session；2 合成学生、2 合成课程，每课 1 个 chunk；不使用正式库/PDF |
| 模型与检索 | FakeEmbedder + 每请求 CourseLLM(FakeLLM)，dense、rerank disabled、query expansion disabled |
| 请求 | POST stream，query=`请说明本课的事务隔离级别`；两个已登录用户各问自己的课，各占 50%；cookie 仅内存使用，不输出 |
| 请求数 | 并发 1/5/10，各 20 次，共 60 个测量请求；每档另有 1 次不计时预热；登录、建库、预热不计入测量 |
| 调度 | ThreadPoolExecutor 最大工作线程数为并发档位，提交 20 个任务；没有 think time 或人为模型延时 |
| 成功 | HTTP 200、完整 SSE、唯一 final、error_code 为空、引用等于对应课程 chunk；其他结果均失败 |
| 首事件 | worker 发请求前 perf_counter 至收到首个**完整 SSE 事件**（通常 retrieve）；含 HTTP/鉴权，不是首 delta/token；不是 TestClient 缓冲后的伪计时 |
| 端到端 | 同一起点至完整读完 HTTP stream；单请求延迟不含 executor 排队时间 |
| 吞吐 | 成功数 / 整档 wall time；wall time 包含 executor 创建、排队和全部请求完成 |
| 分位数/错误率 | nearest rank（排序后 ceil(n×p)）；延迟仅成功样本；错误率=失败/20，不丢弃失败 |
| 验收目标 | 确认事件/清理/隔离合同，60/60 成功并保留全部样本；仅建立延迟基线，没有生产容量或毫秒级 SLA 门槛 |

## 同次运行结果

所有耗时单位为 ms，吞吐为成功请求/s。完整精度及 60 个原始样本保存在同次测试生成的 JSON；本表四舍五入到两位。

| 并发 | 成功/失败 | 吞吐 | 首事件 p50 | 首事件 p95 | 端到端 p50 | 端到端 p95 | 错误率 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 20/0 | 21.76 | 13.93 | 21.31 | 42.60 | 62.95 | 0% |
| 5 | 20/0 | 23.66 | 71.66 | 109.79 | 194.75 | 264.65 | 0% |
| 10 | 20/0 | 25.54 | 131.20 | 184.81 | 341.07 | 468.27 | 0% |

并发上升时延迟增加、吞吐增长有限。此负载包含同步数据库访问、线程池切换和 SSE 小事件发送；未做分阶段 profile，不能断言单一瓶颈。小数据 SQLite/Fake 结果不能代表 PostgreSQL 检索、真实模型延迟、事实正确率或生产容量，20 样本 p95 也不是稳定的容量估计。

## 实际验证与未完成项

仓库根执行（本机 sandbox 的 pytest 0700 临时目录 ACL 不可访问；本次用忽略目录 `output/plan08-env/sitecustomize.py` 仅将该目录下的 mkdir 0700 调整为默认权限，未改业务/测试夹具）：

```powershell
$env:PYTHONPATH='D:/workspace/univ-course-rag/output/plan08-env'
$env:PYTEST_ADDOPTS='--basetemp=D:/workspace/univ-course-rag/output/plan08-env/accept-q -p no:cacheprovider'
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan08_stream_performance.py backend/tests/test_ask.py -q
# 85 passed, 1 warning in 27.77s

$env:PYTEST_ADDOPTS='--basetemp=D:/workspace/univ-course-rag/output/plan08-env/measurement-final -p no:cacheprovider'
$env:PLAN08_BASELINE_OUTPUT='D:/workspace/univ-course-rag/docs/stream-performance-baseline.samples.json'
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan08_stream_performance.py -q -s 2>&1 | Tee-Object -FilePath docs/stream-performance-baseline.output.txt
# 12 passed, 1 warning in 9.27s；三档 PLAN08_BASELINE 原始行见 output.txt

backend/.venv/Scripts/python.exe -m ruff check backend/app/api/ask.py backend/app/services/llm.py backend/app/services/generate.py backend/tests/test_plan08_stream_performance.py
# All checks passed!

cd frontend
node --test --test-isolation=none tests/askHistory.test.mjs tests/askStream.test.mjs
# tests 10 / pass 10 / fail 0
npm run build
# exit 1: failed to load config ... Error: spawn EPERM (esbuild child process)
npm run build -- --configLoader native --target esnext --minify false
# exit 1: [commonjs--resolver] spawn EPERM (Vite Windows net use child process)
```

原始测试警告为既有 Starlette BlockingPortal deprecated；并非测试失败。最初无环境适配的测试因 pytest 临时目录 WinError 5 在 setup 失败，未将其当作业务失败；随后上述实际 `-m pytest` 命令通过。正常本机可直接运行 pytest，无需这个 sandbox 目录权限适配；复测须使用新的 basetemp 目录。

测试覆盖：事件顺序、delta 拼接与 JSON 等价、空召回/生成拒答、上游故障/注入慢超时/未知异常、generate-only 兼容路径、provider close 与断开标记的清理、两用户/两课程回答/引用/错误/日志归属，以及三档实 HTTP 测量。取消采用 generator close / 模拟断开检查；未把 TestClient 缓冲行为冒充真实浏览器断线证据。

前端新增测试验证任意 UTF-8/CRLF 分片、渐进文本、final 引用、缺失终态、超时错误、取消释放与重试、身份清理。另用 `@vue/compiler-sfc` 对 AskView 的 parse/compileScript/compileTemplate 验证，输出 `AskView.vue SFC parse/script/template: PASS`；这不替代完整 Vite 构建。

**构建未绿**：标准命令及 native 配置替代命令均被本执行环境的 Node `spawn EPERM` 阻断；需要 executor 在可启动子进程的环境运行 `cd frontend; npm run build`。**Vite 手动流式点击：开发者未点/待 PLAN-09**，包括开始、取消、故障/超时、重试、恢复后的回答→依据→引用→PDF 页，均未宣称 PASS。

`backend/.venv/Scripts/python.exe output/plan08-env/verify_docs.py` 输出 `Local relative links: 63 PASS; baseline table matches same-run JSON; raw samples: 60 PASS`。`git diff --check` exit 0，无空白错误（Git 提示部分 Markdown 下次写入会 LF→CRLF）。显式 `git add -- <本卡16个文件>` 与指定 `git commit -m 'feat(PLAN-08): Fake SSE ask stream and concurrency baseline'` 均 exit 1：`fatal: Unable to create 'D:/workspace/univ-course-rag/.git/index.lock': Permission denied`。保留 diff 交 executor，无 push。

## 真实模型

未执行（未用云额度）。本报告没有真实模型吞吐、延迟或容量结论。

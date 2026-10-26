# TASK: 学情分析质量与使用验证

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-06 |
| 状态 | framework done；正式人工评价 / 独立教师试用未完成 |
| 须授权 | 真实问句样本使用/外发须有明确范围与用途；真实 Embedding/LLM 调用须当次明确授权；邀请试用者、发送消息须用户明确指示，本卡不自动对外联系 |

## 目标

- 按预先冻结规则评价分组/主题质量，保留人工标注、误合并/误拆分、未分组与教师修正证据。
- 安排教师分析任务试用，明确质量不足时继续保留候选模式的产品结论。

## 非目标（禁止顺手做）

- 不通过调金标/事后改阈值刷分，不用教师接受率替代人工指标；通用学生/教师体验由 PLAN-09 汇总。
- 禁止顺手上 GraphRAG、知识图谱或第二套完整 RAG 管线；禁止更换 PostgreSQL+pgvector；禁止全量 Vision/解析/重入库，任何超出本卡范围的增强另立项并授权。

## 验收标准（可判定真假）

- [ ] 评价开始前已留存 PLAN-01 规则/数值阈值、样本版本与冻结时间；标注者、核验者、争议处理与数据来源可追溯。
- [ ] 报告成对精确率/召回率或适用聚类指标、覆盖率、单例比例、误合并/误拆分/未分组、n/N 与配置，并对知识点/主题标签单列人工核验结果。
- [ ] 教师接受/修正情况仅作辅助信号；合成、真实日志、开发者与独立核验分开报告；不足以达门槛时保留候选并记录限制。
- [ ] 完成教师查看候选→确认/修正→记录行动→代表问题回归的任务观察，记录完成情况、耗时、困惑和修正；招募不足时写“未完成”，不得勾为试用通过。
- [ ] 评价报告与原始统计可复算；若新增评价脚本，补定向测试与 ruff 原始输出，不能以脚本绿测替代人工核验。
- [x] 新增评估工具：指定 PLAN-06 pytest 与触及 Python 路径的 ruff 通过（按当次用户限定范围，不全量检查 backend）。
- [x] 文档验收：产物内容逐项对照本卡；本地相对链接目标存在、章节指针正确；`git diff --check` 通过，贴原始输出与链接自检结果。

### 当次授权的框架交付（不替代上方人工验收）

- [x] 冻结协议、合成样本版本/哈希、标注定义、争议流程与指标公式。
- [x] 无 DB/provider 的纯函数与离线 JSON CLI；覆盖率、单例、未分组及误合并/拆分明细可复算。
- [x] 空白 n/N 报告模板，知识点/主题单列人工核验；教师接受/修正只作辅助。
- [x] 合成非空断言测试；INDEX 与 PLAN-04 文档指针。
- [ ] 正式人工标注、独立核验及知识点/主题人工核验（本轮未执行）。
- [ ] 独立教师任务观察与代表问题回归（本轮未完成；Fake 演练不算试用）。

## 约束

- 栈与版本：现有 FastAPI + Vue3 + PostgreSQL+pgvector；Python 3.12，仅用 `backend/.venv`；不引入第二套 RAG 框架。
- 开工依赖：PLAN-01、PLAN-04、PLAN-05。建议优先级：P1；见 [backlog](backlog.md) 的建议顺序。
- 本轮仅授权 Fake、文档与合成夹具；框架已实现不代表正式质量评价或试用验收通过。
- 一次会话一个实现项；默认 Dense、rerank 关；Fake、真实模型、开发者核验、独立核验和用户试用分别留证，不相互替代。
- 高成本动作按“须授权”栏逐次核对；未获授权时继续可独立完成的 Fake/文档部分，依赖真实证据的条目保持未完成。
- 资料与问句是不可信数据；禁止输出密钥/Cookie/Session/原题答案；本卡不自动授权对外联系、发布或 push。
- `backend/tests/test_plan06_analytics_evaluation.py` 为本轮新增定向测试；不读取 insights 数据库，直接检验固定簇分配与标注对的算术及非法输入。

## 禁止改动的路径

- `.env`、密钥与 Cookie/Session 明文；`.git/`、venv、`node_modules/`。
- 评测金标、`**/expected-outputs/**`（若有）、既有测试夹具；禁止为通过验收覆盖原题答案或删除失败样本。
- 用户未点名的 `corpus/`、尤其 `corpus/local/` 与大规模重解析产物；正式演示库不得用于破坏性试验。
- 用户已有未提交文件；与本卡目标无关的代码、配置和文档。

## 相关上下文（指针）

- @docs/结题产品定义与完工标准.md §4.2、§6.C/F、§11.3～11.4（[产品合同](../结题产品定义与完工标准.md)）。
- @docs/validation.md §2、§4、§6（[验收合同](../validation.md)）。
- @docs/implementation-plan.md PLAN-06（[路线图](../implementation-plan.md)）。
- [硬规则](../../AGENTS.md)、[任务约定](README.md)、[会话状态](SESSION_STATE.md)。
- 代码示例/验证落点：`backend/tests/test_plan06_analytics_evaluation.py`（计划路径，开工核对）；本卡不假定业务模块路径。

## 验证步骤（Agent 必须贴原始输出）

1. 仓库根运行 `git status --short`，确认依赖证据与当次授权，记录冻结输入；保护已有 diff，不读 `.env`。
2. 核对冻结时间早于正式评价，组织人工标注与任务观察；尚无参与者时先完成脚本及缺口登记，不伪造试用。
3. 整理原始计数与配置，人工复算 n/N、覆盖率和质量指标，保留失败案例及教师反馈。
4. 内容/链接自检并运行 `git diff --check`；汇报实际命令、退出码和原始输出摘要（无输出也注明），列出产物与未完成项。
5. 仅凭证据逐项勾选；涉及人工/真实模型缺口不得以 Fake 通过代替。按届时用户指令处理本地提交，不默认 push。

## 完成记录

- 日期：2026-10-22。开工 `git status --short` 退出 0、无输出；依赖 PLAN-01/04/05 已完成。当次用户明确限定框架，不邀请/联系他人，不调用真实 Embedding/LLM，不读 `.env`，不 push。
- 产物：[冻结协议](../analytics-validation-protocol.md)、[报告模板](../analytics-validation-report-TEMPLATE.md)、[评估工具](../../backend/app/services/analytics_evaluation.py)、[合成样本](../../backend/tests/fixtures/plan06_analytics_synthetic_v1.json)、[14 项 Fake 测试](../../backend/tests/test_plan06_analytics_evaluation.py)。复用标准库，无新依赖，未改业务分组/规则/既有金标。
- 正式人工评价、独立核验、知识点/主题核验及独立教师试用：**未完成**。上方相关验收未勾选；模板空白和算术演练不能替代实测。候选模式保留；下一工程项 PLAN-08，缺口继续约束 PLAN-09/10。
- 真实模型新增调用 0 次，新增费用 ¥0，约 ¥2 预算保留；无数据库读取或变更、重入库、Vision。
- 提交：**未完成（环境权限阻断）**。按本轮 10 个文件的明确清单执行 `git add -- ...`，随后实际执行 `git commit -m "docs(PLAN-06): analytics validation protocol and Fake metrics"`，均退出 1：`fatal: Unable to create 'D:/workspace/univ-course-rag/.git/index.lock': Permission denied`。托管环境 `.git` 只读且禁止权限升级；未创建提交、未 push。改动完整保留于工作区，供外部执行器按上述标题提交，不宣称工作区已干净。

### 实际命令与原始输出摘要

仓库根执行：

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan06_analytics_evaluation.py -q
```

退出 0：

```text
..............                                                           [100%]
14 passed, 2 warnings in 0.16s
```

警告原文摘要：`DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated`（既有 Starlette）；`PytestCacheWarning: could not create cache path ...backend\.pytest_cache\v\cache\nodeids: [WinError 5] 拒绝访问`。无失败或跳过，没有为消除警告改环境/测试逻辑。现有 conftest 在 app.db 导入前禁用 dotenv，测试只调本轮纯函数。

```powershell
backend/.venv/Scripts/python.exe -m ruff check backend/app/services/analytics_evaluation.py backend/tests/test_plan06_analytics_evaluation.py
```

退出 0：`All checks passed!`。

```powershell
backend/.venv/Scripts/python.exe backend/app/services/analytics_evaluation.py backend/tests/fixtures/plan06_analytics_synthetic_v1.json
```

退出 0，stdout JSON 原始字段摘要：`sample_version=plan06-synthetic-v1`，`evidence_level=synthetic_fake_arithmetic`，`tp=1, fp=1, fn=1, tn=2, labeled_pairs=6, evaluated_pairs=5, uncertain_count=1`；precision/recall 各 `n=1,N=2,value=0.5`；coverage/singleton 各 `n=3,N=8,value=0.375`，ungrouped `n=2,N=8,value=0.25`。完整输出由该固定输入确定性复算，不能当真人质量结果。

文档核对：协议 §1～6、模板独立知识点/主题核验列与空白 n/N 表、PLAN-01 §5 和 PLAN-04 §1～2 指针均已核对。用 `backend/.venv/Scripts/python.exe -` 执行标准库 `pathlib/re/hashlib` 只读断言脚本，退出 0：

```text
Markdown local links: 67 checked, 0 missing (7 files)
Synthetic fixture SHA-256: match frozen protocol
```

`git diff --check` 退出 0，无空白错误输出；stderr 仅有 `LF will be replaced by CRLF the next time Git touches it` 换行提示。

### 2026-10-26 框架复验

- 仅复验现有离线框架、固定合成夹具与定向测试；未改业务默认分组行为，未改以上任何验收/框架交付复选框。
- 合成夹具算术仍为 TP/FP/FN/TN = 1/1/1/2；总标注对 6、可判定对 5、不确定对 1；precision=1/2、recall=1/2；覆盖 3/8、单例 3/8、未分组 2/8。这些是固定合成算术断言，不是人工质量结果。
- 正式人工标注、独立核验、知识点/主题人工核验、独立教师试用均仍未完成；对应验收复选框保持未勾选。框架复验通过不改变候选模式结论，也不替代真实证据。

仓库根实际运行：

```powershell
backend/.venv/Scripts/python.exe -m pytest backend/tests/test_plan06_analytics_evaluation.py -q -p no:cacheprovider --tb=short
```

退出 0：

```text
..............                                                           [100%]
14 passed, 1 warning in 0.70s
```

唯一警告为 Starlette `testclient.py:53` 引发的既有 `DeprecationWarning`：`The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.` 未改依赖或测试逻辑。

```powershell
backend/.venv/Scripts/python.exe -m ruff check backend/app/services/analytics_evaluation.py backend/tests/test_plan06_analytics_evaluation.py
```

退出 0：`All checks passed!`。本次复验只编辑本任务卡；无数据库、真实模型或教师试用操作。

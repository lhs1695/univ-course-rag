# PLAN-09 核心用户任务脚本

冻结版本：`p09-tasks-v1`，2026-10-23（Asia/Shanghai）。**脚本与观察表已准备。独立用户试用按用户指示取消；改由开发者 Vite 代观察**（见 [observation-2026-10-23-developer.md](observation-2026-10-23-developer.md)）。排练≠独立试用；开发者观察≠独立试用。

| 文件 | 用途 |
| --- | --- |
| [student-core.md](student-core.md) | S1 提问到原 PDF 页；S2 依据不足；S3 系统故障；S4 流式与取消 |
| [teacher-core.md](teacher-core.md) | T1 资料质量；T2 候选核查与动作；T3 刷新持久化 |
| [observation-sheet-TEMPLATE.md](observation-sheet-TEMPLATE.md) | 一人一角色一轮，记录 n/N、耗时、协助、困惑与复测 |
| [rehearsal-log-2026-10-22.md](rehearsal-log-2026-10-22.md) | 开发者 Fake/API 排练与检查原始输出；非用户试用 |
| [observation-2026-10-23-developer.md](observation-2026-10-23-developer.md) | 开发者 Vite 代观察记录（用户授权替代独立试用） |
| [evidence-2026-10-23/](evidence-2026-10-23/) | 观察与真实小样本证据（含估费记录） |

## 冻结与执行

1. 执行前复制观察表，登记脚本版本、代码提交、日期、匿名参与者代号、角色、是否参与开发和环境。冻结课程、问句、资料及目标 PDF 页；不改评测金标。脚本变更另升版本，旧记录保留。
2. 后续人工观察从 Vite 进入，使用已安排且获授权的课内账号；不得直连 `:8000` 登录。本轮只在 pytest 隔离 SQLite、临时文件和 FakeEmbedder/FakeLLM 下排练 HTTP API，不读 `.env`，不操作正式资料。
3. 人工试用前需准备安全的本地 Fake 场景：可引用 PDF、依据不足、受控系统错误、成功带质量警告与整份失败的资料、至少一个主题候选。没有隔离场景就记「前置缺失」，不破坏正式服务制造故障。不点击「生成候选组」或外发确认，不启用真实 embedding/LLM/Vision/reranker，不重入库。
4. 观察者只读任务目标，不提示按钮位置或解释正确答案；协助须记原话与时刻。每项从读完任务到完成/停止计时，10 分钟仍未完成则停止并记未完成；耗时用于描述，不新增性能达标结论。
5. 保存脱敏证据位置，不留凭据、Cookie、Session、真实学生身份或原题答案。发现阻断，回流对应实现卡；保留修复前记录，用相同任务版本/输入复测，记录新提交和是否换人。

## 统计与证据边界

- 学生计划 N=4（S1～S4），教师计划 N=3（T1～T3），按角色分别报告，不混为准确率。n 是无操作协助且满足该任务全部成功条件的项数；协助后完成单列。已分配但失败、跳过、前置缺失的任务仍在该轮 N 中，逐项注明原因。
- 尚未执行的独立试用填写「未观察；计划 N=4/3」，不能写成已观察的 0/N、100% 或 PASS。开发者/API 测试用例通过数与人类任务 n/N 分栏，pytest 耗时不代替用户耗时。
- S1 必须保留「授权提问→回答→依据→点引用→实际原 PDF 页」链路；HTTP 返回 PDF 和页码只覆盖接口段，不能证明浏览器跳页或主张正确。T3 的 GET 重取只覆盖数据库持久化，不能证明浏览器刷新体验。
- S4 的 Vite 流式/取消/重试：开发者观察已执行（见 observation-2026-10-23-developer）；Node 单测仍只是逻辑 smoke。教师候选是备课线索，不表示学生掌握度、知识点事实或教学效果。
- 仍缺可选补证：S3 隔离故障场景、T1 整份失败资料对照（见 [PLAN-09 覆盖矩阵 2026-10-26](../tasks/PLAN-09-core-user-tasks.md#覆盖矩阵补记2026-10-26-asiashanghai--对照-m3m4-观察与门禁)）。

合同入口：[PLAN-09 任务卡](../tasks/PLAN-09-core-user-tasks.md)、[验收合同](../validation.md)、[PLAN-05 闭环](../teacher-action-loop.md)、[生命周期/权限](../lifecycle-permissions-matrix.md)。PLAN-10 清单已建；**不得宣称独立试用或结题验收通过**。

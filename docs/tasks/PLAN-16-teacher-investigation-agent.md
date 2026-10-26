# TASK: 教师侧课程问题调查 Agent

> 对齐 [结题已拍板规格](../结题已拍板规格.md)。

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-16 |
| 状态 | **已落地**：M2+M3 已提交；2026-10-26 developer 观察（确认门禁+Fake 报告 UI/API）PASS；浏览器 PDF 实落页仍 SKIP；真模型调查非本轮主验收 |
| 须授权 | 真实模型调用、真实学生问句外发、正式课程资料/索引写入均须当次明确授权 |

## 目标

- 完成一个端到端的教师课程问题调查任务。
- 复用现有问答统计、相似问句候选、课程资料状态、检索、证据和引用能力。
- 输出可追溯的待核查报告，并提供任务状态、Trace、失败原因、取消及受控恢复入口。

按拍板分期：M2 已按 2026-10-26 当次授权实现调查报告 API，仅依赖 PLAN-14 + PLAN-15 对应的最小存储、权限和有界 Fake/Replay 执行子集，实际命令/计数见 [SESSION_STATE](SESSION_STATE.md)。M3 已沿册/衡样式补教师调查页、必要事件摘要、PDF 页链接与最小 lease/取消/恢复；当前环境阻止 Node 子进程及 Git 写锁，build、Vite 实点和本地提交尚未闭环。完整 TTL 清理/Trace UI 不作为 M2 前置，不重开前端翻新；定向验证不代表真实模型质量或 M3 通过。

## 非目标

- 不优先建设学生侧多步检索 Agent，不做多 Agent 协作平台。
- 不直接修改正式课程资料、索引、课程成员或权限。
- 不输出个体学生掌握度、成绩或教师教学质量结论。
- 不创建第二套 RAG 或平行的课程/身份数据模型。
- 不宣称可以回溯审计历史回答正文：当前 QueryLog 未保存最终回答文本或实际引用快照。

## M2 / M3 分期硬验收（M2 定向已验，待 bot 验收；M3 待完成环境验收）

- [x] M2：报告 API schema + 来源校验 + 落库；独立 HTTP+新 DB Session 报告读取受课程教师权限，失败有明确终态；原详情不泄露报告。显式 POST `/{task_id}/run` 仅同步 Fake/Replay，创建保持 queued。
- [x] M2：非 Fake LLM/Embedding 配置（含语义分组构建 Embedding 场景）未 confirm 时创建前拒绝、不入队；真实工厂/getter 与 question_groups.build_embedder spies 均为 0；确认后也仅 Fake 执行，无真实外发。
- [x] M2：空窗样本/学生分母为 0、无发现/候选原因、unknowns 说明无数据，合法 succeeded；过期/删除/错课 QueryLog 与删除/禁用/错课资料/Chunk 均 unavailable，读取仅查元数据、隐去相关结论，SQL 捕获断言不读取问句/Chunk 正文。
- [x] M2：版本夹具 `e5a-m2-v1` 固定同课程/时间窗/快照，A 统计列表、B 明确 N/A（未运行语义分组）、C Fake/Replay 报告；必需事实覆盖 5/5、捏造引用 0/6、候选原因确定化 0/1；no_evidence 不断言缺资料、系统失败不归教学；终态 succeeded，3 模型动作/3 工具调用。实际耗时/完整命令见 SESSION_STATE，成本标 Fake，不代表真实模型质量或教师效率。
- [x] M3：UI 明示/确认与请求前拒绝：代码+49 前端测+后端 spies 既有；**2026-10-26 developer Vite**：未勾确认被拒文案 PASS，勾选后 Fake 报告 PASS（见 observation-2026-10-26）。首版仅为 UI/请求确认。
- [~] M3：Vite 发起→Fake 报告 PASS；**浏览器点引用实落页仍 SKIP**（服务/前端 `#page=` 拼装在真问路径已断言 page=10）。来源删除/禁用门控沿用既有服务端测。
- [x] M3：H06 取消生效、H07 一次进程中断后仅显式恢复、H11 DB 幂等、来源 unavailable 通过；最小 lease/token fencing 不允许旧执行者覆盖新结果。

完整 Harness 分期/预算与 E5-A 门禁见 [任务合同 §7](../teacher-agent-task-contract.md#7-初始预算与可判定终止规则2026-10-26-用户确认) / [§9](../teacher-agent-task-contract.md#9-harness-首批场景与分期门禁)。H12 物理 TTL 清理可后置，失效来源不可解析须在 M2/M3 验；无真实教师参与不得宣称效率已验证，真实模型质量单列。

## M3 实际实现与待验（2026-10-26）

- 新 `/courses/:courseId/investigation`，沿用课程 capability 与「册」共用 token；教师导航启用课程调查，管理员学期/班级占位保留。时间窗/焦点、必选外发确认、创建、显式 Fake/Replay run、累计预算/事件摘要、取消/恢复/重试与 URL task 恢复读取已实现。
- 报告分观察事实、支持证据、候选解释、未知、建议人工动作；来源失效不显示关联正文；证据使用服务端授权 `content_url` + `#page=`。Replay 只作当前授权资料的 Fake 字面核对，不接真实语义检索或模型；无匹配时不编 PDF 引用。
- 后端 129 例通过（含 M1/M2、M3 runtime 22 例），前端现有 Node tests 扩展后 49/49，新增页 Vue SFC parse/script/template 编译通过，ruff 通过。非 vitest 项目，无新增依赖。
- `npm run build` 失败 `spawn EPERM`；Vite `--configLoader native` 可监听，但 `/src/main.js` 与调查页模块均 HTTP 500 / `spawn EPERM`，不能用首页 HTTP 200 或 SFC 编译替代点击验收。预期夹具 Document `00000000-0000-0000-0000-000000000014` 第 3 页，服务层 URL/page 断言通过，浏览器实际 Document/落页 **未验证**。
- build、Vite 确认/取消/恢复/重试控件、报告依据点击、新窗口 PDF 实际落页仍待补；本地 stage/commit 因 `.git/index.lock: Permission denied` 未完成。完整命令/原始输出/复验清单见 [SESSION_STATE](SESSION_STATE.md#m3-本轮交付与证据2026-10-26)。未 push；未触及 M4。

## 通用验收标准

- [ ] 教师可在授权课程与时间窗口内创建调查任务，调查重复问句、依据不足、系统失败及当前课件证据，并查看任务 ID、状态、进度、结果和失败原因。
- [ ] Agent 只使用后端 allowlist 中的只读工具，不能通过参数或提示注入访问其他课程。
- [ ] 报告明确区分观察事实、支持证据、候选原因、不确定点和建议人工动作；重要结论能回溯到问句/文档/Chunk/PDF 页。
- [ ] 证据不足时明确说明限制；没有来源支持的原因不得写成事实。
- [x] 最小只读时间线已落地：教师在既有 details 查看 attempt/step、事件/工具名、耗时、时间、安全摘要与错误码；沿用既有取消、显式恢复/重试。完整 Trace UI 仍后置；本批 Vite 点验未完成。
- [ ] 对课程资料、索引、成员或权限的业务写入不由 Agent 静默执行；需要时跳转现有业务界面并要求人工确认。
- [ ] 与原始统计/问句列表基线进行固定任务对照，记录证据覆盖、无依据推断、任务终态、工具调用量、耗时与成本。
- [ ] PLAN-14/15 Harness 覆盖该工作流的正常、失败、取消、恢复和越权路径；定向测试、ruff、前端 build 与关键 Vite 路径按实际改动执行。

## 约束

- 首版只做“课程问题调查”，不扩展为通用教师聊天机器人。
- 默认使用 Fake/Replay 开发与回归；真实云调用和真实问句外发需当次授权。
- 教师接受/修正结果是辅助信号，不代替独立标注或答案证据评价。
- 用户独立试用已取消；只能将脚本化测试和开发者 Vite 观察标注为对应证据级别。

## 禁止改动的路径

- .env、密钥、Cookie/Session 明文、.git、venv、node_modules。
- 评测金标与既有冻结题集。
- 未经授权的 corpus/local、正式演示数据库和资料重入库。
- 与调查任务无关的学生端功能、额外数据源或 GraphRAG 实现。

## 相关上下文

- [PLAN-14 合同与 Harness](PLAN-14-agent-harness-contract.md)
- [PLAN-15 运行时可靠性](PLAN-15-agent-runtime-reliability.md)
- [现有代码审查](../teacher-agent-current-code-audit.md)
- [产品合同](../结题产品定义与完工标准.md) §2.2、§3、§4.2、§6.H
- [验收合同](../validation.md) §8
- [施工计划](../implementation-plan.md) PLAN-16
- 历史参考：`中期答辩材料/笔记/04-教师侧Agent与Harness实施方案.md`（冻结，非链接）

## 验证步骤

1. 开工前检查 git status、当前权限与 PLAN-14/15 实际验收证据。
2. 先实现一条可解释的只读任务链，明确报告 schema 和来源回溯规则。
3. 使用 Fake/Replay 执行 Harness；验证正常、证据不足、超时、取消、恢复、越权和预算终止。
4. 如需真实模型，先获得当次授权并记录模型、样本、预算和输出留存规则。
5. 运行定向测试、ruff、build 与关键 Vite 路径；保留未完成项，不以演示成功代替异常路径验收。

## 2026-10-26 Trace 薄切（t272u）

- **最小只读时间线已落地；完整 Trace UI 仍后置**。沿用现有 details 与视觉 token，不新增路由/依赖；展示 attempt、可空 step/tool/duration（含 0 ms）、事件类型、安全摘要、错误码与本地短时间。安全证据引用仅在 API 输出 ID/页码；不展示原始问句或异常内容。
- events 当前课程教师权限保持不变；后端新增引用白名单/恶意文本剥离与非教师 403 断言。Trace 三文件定向 pytest **51 passed, 1 warning in 23.65s**；ruff `All checks passed!`；调查页 Node **5 pass / 0 fail**（含 compiler-sfc parse/script/template）。完整命令见 [PLAN-15 本批记录](PLAN-15-agent-runtime-reliability.md#2026-10-26-最小只读时间线t272u)。
- `frontend` 下 `npm run build` 实际 exit 1：加载配置时 esbuild `spawn EPERM`；本批 Vite 交互点验 **SKIP**。不覆盖此前 developer 观察，也不把本批 SFC 检查称为 build/浏览器通过；PDF 实落页、完整 Trace UI 与真实模型调查质量仍未完成。
- 本批无演示库写入/迁移、真实外发、stage/commit/push；由 bot 后续验收提交，不宣告结题通过。


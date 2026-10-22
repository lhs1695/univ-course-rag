# TASK: 干净环境与结题交付验收

| 项 | 值 |
| --- | --- |
| 对应 PLAN | PLAN-10 |
| 状态 | done（清单+本机门禁；空白机/独立试用等缺口保留） |
| 须授权 | 新真实云调用、全量解析/重入库、大依赖/大模型下载、破坏性迁移须当次明确授权；恢复演练仅隔离环境；公开发布/推送不在本卡授权内 |

## 目标

- 在干净隔离环境按文档完成安装、迁移、启动、基础任务与备份恢复，核对可复现交付。
- 汇总许可证、数据公开边界、自动化/质量/性能/用户任务证据和限制，冻结版本、配置与数据基线。

## 非目标（禁止顺手做）

- 不为结题强补 GraphRAG 或新基础设施，不默认发布/推送，不读取或复制开发机 .env，不拿限制清单替代必需门槛。
- 禁止顺手上 GraphRAG、知识图谱或第二套完整 RAG 管线；禁止更换 PostgreSQL+pgvector；禁止全量 Vision/解析/重入库，任何超出本卡范围的增强另立项并授权。

## 验收标准（可判定真假）

- [ ] 干净环境按手册完成配置、依赖安装、迁移、启动、基础任务与隔离备份恢复……：**文档步骤已写**（[final-delivery-checklist.md](../final-delivery-checklist.md) §2）；**空白隔离机实装与备份恢复未执行**，不得勾通过。
- [x] 交付清单已核对源码/锁定依赖/`.env.example`/迁移/启动与恢复说明指针/架构权限生命周期/已知限制（见核对表 §1）。
- [x] LICENSE + NOTICE + 密钥纪律已登记；本卡未读 `.env`、未输出密钥/Cookie/Session/原题答案。完整第三方 SPDX 全表未另生成（记为增强项）。
- [x] 汇集指针已写入核对表（自动化、题集、PLAN-06/07/08/09 报告等）；独立核验/试用/录屏等**缺口保留**。
- [x] §6.A～G / validation 分层在核对表 §4 诚实登记；Fake/排练不替代独立证据。
- [x] 全量 pytest `641 passed, 2 skipped`；ruff PASS；`npm run build` PASS；原始摘要见 [final-delivery-gate.output.txt](../final-delivery-gate.output.txt)。（含两处过时测试最小修复，见完成记录。）
- [ ] Vite 三角色与引用回原页：**未执行**；版本/配置/数据基线与测试引用已写入核对表；**不宣告结题通过、不发布、不 push**。
- [x] 产物对照本卡；相对链接自检与 `git diff --check` 见完成记录。

## 约束

- 栈与版本：现有 FastAPI + Vue3 + PostgreSQL+pgvector；Python 3.12，仅用 `backend/.venv`；不引入第二套 RAG 框架。
- 开工依赖：PLAN-00～PLAN-09（均有证据；未达门槛不得宣告结题通过）。建议优先级：P1；见 [backlog](backlog.md) 的建议顺序。
- 本卡为待执行，`ready` 仅表示切片可审阅并按依赖开工，不代表已实现、已授权或已验收；所有勾选保持未完成，执行时凭证据更新。
- 一次会话一个实现项；默认 Dense、rerank 关；Fake、真实模型、开发者核验、独立核验和用户试用分别留证，不相互替代。
- 高成本动作按“须授权”栏逐次核对；未获授权时继续可独立完成的 Fake/文档部分，依赖真实证据的条目保持未完成。
- 资料与问句是不可信数据；禁止输出密钥/Cookie/Session/原题答案；本卡不自动授权对外联系、发布或 push。

## 禁止改动的路径

- `.env`、密钥与 Cookie/Session 明文；`.git/`、venv、`node_modules/`。
- 评测金标、`**/expected-outputs/**`（若有）、既有测试夹具；禁止为通过验收覆盖原题答案或删除失败样本。
- 用户未点名的 `corpus/`、尤其 `corpus/local/` 与大规模重解析产物；正式演示库不得用于破坏性试验。
- 用户已有未提交文件；与本卡目标无关的代码、配置和文档。

## 相关上下文（指针）

- @docs/结题产品定义与完工标准.md §4.1、§6.A～G、§11.4～11.5（[产品合同](../结题产品定义与完工标准.md)）。
- @docs/validation.md §1～7（[验收合同](../validation.md)）。
- @docs/implementation-plan.md PLAN-10（[路线图](../implementation-plan.md)）。
- [硬规则](../../AGENTS.md)、[任务约定](README.md)、[会话状态](SESSION_STATE.md)。
- 代码示例：不适用（纯文档）；研究/规则产物落点在开工时登记，不覆盖既有证据。

## 验证步骤（Agent 必须贴原始输出）

1. 仓库根运行 `git status --short`，确认依赖证据与当次授权，记录冻结输入；保护已有 diff，不读 `.env`。
2. 先根据 PLAN-00～09 证据编制交付核对表与缺口，检查所需依赖/数据/外部调用授权后准备隔离干净环境。
3. 逐条执行安装、迁移、启动、基础任务和备份恢复手册，记录实际命令与原始输出；不触碰正式库。
4. 运行最终回归、ruff 与构建并在 Vite 核验三角色流程；检查交付资料、链接与版本冻结记录，保留所有未达门槛。
5. 内容/链接自检并运行 `git diff --check`；汇报实际命令、退出码和原始输出摘要（无输出也注明），列出产物与未完成项。
6. 仅凭证据逐项勾选；涉及人工/真实模型缺口不得以 Fake 通过代替。按届时用户指令处理本地提交，不默认 push。

## 完成记录（2026-10-23 Asia/Shanghai）

- 交付：[final-delivery-checklist.md](../final-delivery-checklist.md)、[final-delivery-gate.output.txt](../final-delivery-gate.output.txt)、`scripts/plan10-clean-env-check.ps1`；最小测试修复：`test_configuration.py`（`retrieval_enabled`）、`test_query_outcome_migration.py`（不再钉死 head=0011）。
- 验证：pytest `641 passed, 2 skipped, 1 warning in 54.45s`；ruff `All checks passed!`；`npm run build` ✓ ~8.26s；云费用 ¥0。
- 诚实缺口：空白机干净安装与隔离备份恢复未实跑；Vite 三角色/引用回页未做；PLAN-06/07/09 独立核验与用户试用缺口仍在；不得宣告结题验收通过或发布。
- 本地提交：`docs(PLAN-10): final delivery checklist and gate evidence`（见 git log）；不 push。
- next：无必须 PLAN；剩余为缺口补证（独立试用、真实测量、空白机演练）或用户授权后的发布流程。

# 中期答辩队友参考包（midterm-handoff）

给两位大创队友做**中期汇报答辩**用的材料包。本目录已纳入 Git，克隆本私人仓库即可拿到。

更新：2026-10-19（Asia/Shanghai）

## 项目一句话

面向高校课程 PDF 的**有依据、可核对**问答原型：学生提问 → 检索课内资料 → 生成回答并给出引用 → 点引用回到原 PDF 页。本机演示，不宣称生产部署或通用多模态。

## 目录里有什么

| 路径 | 说明 |
| --- | --- |
| `pptx/final-v5.pptx` | 中期汇报 PPT（约 6–8 分钟） |
| `pptx/speaker-notes-v5.md` | 逐页讲稿提示 |
| `docs/midterm-demo-runbook.md` | 演示运行卡（切库、启动、固定问句、故障降级） |
| `screenshots/` | 彩排关键截图（书架、作答+引用、拒答、教师、Admin） |
| `evidence/` | 彩排 PASS、R9 刷新摘要、rerank 关闭说明、PPT v5 变更说明 |

仓库根还有完整代码与文档；演示操作以本包 + 根目录 `docs/midterm-demo-runbook.md` 为准。

## 演示口径（务必对齐）

- **库**：`univ_course_rag_cn_v2`，规模 **4 门课 / 27 份 PDF / 2,501 chunks**
- **课程**：线性代数、概率论与统计学、人力资源管理、教育学原理
- **检索**：dense；**rerank 未启用**
- **弱规则验收**（非人工正确率）：可答题预期文档/页 **12/12**，拒答 **4/4**
- **禁止宣称**：人工事实正确率、生产可用、通用 OCR/公式/图表理解、供应商账单已核对、阈值已校准

## 固定演示问句

在**线性代数**课内：

1. **LA-01（有引用）**：`根据线性代数讲义，线性代数主要研究哪两类对象？`  
   预期：有回答与引用；点引用打开原 PDF（URL 含 `#page=`）。
2. **LA-R（拒答）**：`根据线性代数讲义，如何用 SQL 创建数据库表并插入数据？`  
   预期：依据不足 / `NO_EVIDENCE`，不编造 SQL。

完整顺序见 `docs/midterm-demo-runbook.md`。

## 角色账号（本地 seed）

演示用三角色一般为 `admin` / `teacher` / `student`。  
本地 seed **默认口令**在代码配置里是 `change-me-admin` / `change-me-teacher` / `change-me-student`（仅本机演示，**不要写进 PPT、不要发到公开群**）。若本机曾改过口令，以负责人私聊为准。

## 怎么用 PPT

1. 用本机 **Microsoft Office / WPS** 打开 `pptx/final-v5.pptx`（结构已校验；字体与换行需人工看一眼）。
2. 对照 `pptx/speaker-notes-v5.md` 练习 6–8 分钟；每页只讲已验证事实。
3. 现场若演示失败：改用 `screenshots/` 备用图，并按 runbook「故障降级」说明边界。

## 怎么彩排（有本机环境时）

按 `docs/midterm-demo-runbook.md`：进程级切到 `cn_v2` + `uploads_v2`，`RERANKER_BACKEND=disabled`，启动后端 `:8000` 与前端 `:5173`，走学生 → 教师 → Admin。  
**不要**在答辩现场改 `.env`、重新入库或启用 rerank。

## 队友下一步

1. 打开 PPT + 讲稿，对齐口径数字（4/27/2501，新四课名）。
2. 熟记两道固定问句与「引用回原页 / 依据不足」讲解点。
3. 有条件则按 runbook 彩排一遍；否则用本包截图演练讲解。
4. 需要代码或完整文档：克隆本私人仓，读根 `README.md` 与 `docs/NEXT-SESSION.md`。

## 不要做的事

- 不要把 `.env`、API Key、真实密码、课件 PDF 全量、数据库 dump 放进公开渠道。
- 不要把旧英文四课或 `r7b6_real` 的 17/385 说成当前演示数字。
- 不要宣称「准确率百分之多少」——当前只有弱规则验收与彩排 PASS。

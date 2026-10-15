# 新版评测与结果登记

更新：2026-10-15。按用户决定，旧阶段报告、旧评测/性能数字、逐文件旧实验清单与嵌入JSON汇总已移除。中期汇报前，在改进后的项目上重新建基线、入库和评测。**当前没有可作为改进版本验收依据的新真实效果结果。**

操作与指标以 [validation](validation.md#eval-protocol) 为准；本文只登记实际核验的新资料来源、运行条件与脱敏结果。不把计划、代码状态或Fake输出写成真实效果，不新增单独阶段报告。

## 当前登记状态

| 项目 | 状态 |
| --- | --- |
| 可恢复的新版代码/依赖/配置基线 | 用户已授权累计实现检查点提交，以git log/status核对；正式实验的依赖/配置与资料仍待冻结 |
| 目标库迁移/资料重新入库 | 待受控执行与核验，当前代码需0011；旧来源/事件字段不回填 |
| 新资料清单/许可/哈希与切分版本 | 待按新实验核验和登记 |
| 人工支持位置/必需要点/拒答标签与题集划分 | 待建立与冻结 |
| 新版真实模型连通/预算与校准 | 待当次授权后执行 |
| 同条件课程对照与失败审查 | 待执行 |
| 非开发者独立试用 | 待真实参与后登记 |

<a id="current-parameters"></a>
<!-- 保留现有代码注释的跳转目标；不保留原阶段报告或旧结果。 -->
<a id="stage49-threshold-results"></a>

## 当前参数与重验要求

代码中的dense最终Top-K默认8，Fake最低余弦0.15、SiliconFlow最低余弦0.45；hybrid每路召回默认32，重排默认关闭。它们是当前实现配置，文档清理没有修改这些值。旧证据已退出本文件，源码注释中的历史依据链接不能当新版效果证明；新资料、切分与模型条件下应按开发集重新校准，再在封存测试集评价，不保证沿用参数有收益。

关键词独有候选尚不能自动进入生成，重排高分不等于支持充分。不得把合法引用率、正确文档覆盖或合成命中率写成事实正确率，不把未运行项目标成零失败。

## 资料来源与使用条件

现有资料曾来自MIT OpenCourseWare；原文件仍在受控忽略区，本轮未读取、删除、重入库或重新核验。这里仅保留来源/归属入口，原选定文件、字节/抽取计数与旧实验哈希不再作为新数据清单。

| 来源入口 | 归属 |
| --- | --- |
| [18.02SC Multivariable Calculus](https://ocw.mit.edu/courses/18-02sc-multivariable-calculus-fall-2010/) | Massachusetts Institute of Technology / MIT OpenCourseWare |
| [18.06SC Linear Algebra](https://ocw.mit.edu/courses/18-06sc-linear-algebra-fall-2011/) | 同上 |
| [9.00SC Introduction to Psychology](https://ocw.mit.edu/courses/9-00sc-introduction-to-psychology-fall-2011/) | 同上 |
| [21H.001 How to Stage a Revolution](https://ocw.mit.edu/courses/21h-001-how-to-stage-a-revolution-fall-2013/) | 同上，不改称通用历史教材 |
| [24.251 Introduction to Philosophy of Language](https://ocw.mit.edu/courses/24-251-introduction-to-philosophy-of-language-fall-2011/) | 同上，不改称覆盖全部哲学 |

原登记许可为OCW CC BY-NC-SA 4.0，来源条款见 [MIT OCW使用条件](https://ocw.mit.edu/pages/privacy-and-terms-of-use/)。新一轮选材须逐份核对具体资源归属与允许用途，不能由课程页推断第三方教材/试题/答案同样可再分发；本项目不暗示MIT背书。本轮没有重新联网审计这些条款或访问资源内容。

## 新结果登记规则

只有实际执行后才补充：运行日期、可恢复代码/依赖/配置标识、资料与题集哈希、模型/索引身份、切分版本、检索/生成/重排设置、题型和分母、事实/引用/拒答/权限/延迟/费用结果、失败/降级与人工审查边界。

每个结果说明真实/Fake、数据范围与可复现条件；同一版本同一题集的对照才能直接比较。缺项写待验，不移植旧指标或虚构独立反馈。原课件、问题/答案、逐题输出、引用UUID、身份、数据库连接和凭据不得进入本文，留受控忽略区。

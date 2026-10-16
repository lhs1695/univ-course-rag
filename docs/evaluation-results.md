# 新版评测与结果登记

更新：2026-10-16。以下仅登记 R7 本次真实供应商调用和新隔离库上的有限课程对照。旧阶段数字不迁作基线；本次没有人工复核或非开发者试用。

操作与指标以 [validation](validation.md#eval-protocol) 为准；本文只登记实际核验的新资料来源、运行条件与脱敏结果。不把计划、代码状态或Fake输出写成真实效果，不新增单独阶段报告。

## 当前登记状态

| 项目 | 状态 |
| --- | --- |
| 可恢复的新版代码/依赖/配置基线 | main / 9214ac3，运行前工作区干净；冻结配置和受控运行脚本哈希见下文 |
| 目标库迁移/资料重新入库 | 本次**新隔离库**现场从空库迁移至0011，四份资料入库成功；原有长期目标库状态未核验，旧来源/事件字段未回填 |
| 新资料清单/许可/哈希与切分版本 | 四份心理学 PDF 字节与 MIT 官方资源一致；清单、许可边界、切分和索引身份见下文 |
| 支持位置/必需要点/拒答标签与题集划分 | AI 预标 24 题并先冻结；**无人工复核**，开发/测试按知识点隔离 |
| 新版真实模型连通/预算与校准 | SiliconFlow、DeepSeek 实际连通；沿用默认阈值，**未校准** |
| 同条件课程对照与失败审查 | dense / hybrid 各 24 题完成；结果见下文 |
| 非开发者独立试用 | 待真实参与后登记 |

<a id="current-parameters"></a>
<!-- 保留现有代码注释的跳转目标；不保留原阶段报告或旧结果。 -->
<a id="stage49-threshold-results"></a>

## 当前参数与重验要求

本次 dense 最终 Top-K 8，SiliconFlow 余弦阈值 0.45；hybrid 每路候选 32、RRF k=60，最终仍经保守余弦准入；重排 disabled。生成温度 0.2、thinking 关闭、每来源正文上限 1200 字符、总上下文 6000 字符。沿用代码默认阈值，未在开发集重新校准，不宣称最优。

关键词独有候选尚不能自动进入生成，重排高分不等于支持充分。不得把合法引用率、正确文档覆盖或合成命中率写成事实正确率，不把未运行项目标成零失败。

## 资料来源与使用条件

本次仅使用 MIT OpenCourseWare [9.00SC Introduction to Psychology](https://ocw.mit.edu/courses/9-00sc-introduction-to-psychology-fall-2011/) 四份讲义。逐份从 MIT 官方资源流读取并与本机受控 PDF 的字节数、SHA-256 比对一致；下表哈希是原始 PDF，不是抽取文本。

| 本次资料（官方资源） | 原 PDF SHA-256 |
| --- | --- |
| [Introduction](https://ocw.mit.edu/courses/9-00sc-introduction-to-psychology-fall-2011/resources/mit9_00scf11_lec01/) | A4E7B7FB1710620FBEDD6D4E3DF9A3C8C0EC75DB4518458BFD287D3336ED7E3E |
| [Science and Research](https://ocw.mit.edu/courses/9-00sc-introduction-to-psychology-fall-2011/resources/mit9_00scf11_lec02_scires/) | 2915AAADEE7D0721FAEEAE4C878582C15878CAEC7BD4229E3C7461749C41181B |
| [Learning](https://ocw.mit.edu/courses/9-00sc-introduction-to-psychology-fall-2011/resources/mit9_00scf11_lec09_learning/) | 46EDDB2229A501933B93ACC8653CE74E8FCFE79155F929B6EAC6B28AE93BD32D |
| [Emotion and Motivation](https://ocw.mit.edu/courses/9-00sc-introduction-to-psychology-fall-2011/resources/mit9_00scf11_lec15_emotion/) | 6BA4F3FB63CB1AC5BD81AFF74280749B404E32ABC553E82711898BAB0A6CBBC4 |

MIT OCW [使用条件](https://ocw.mit.edu/pages/privacy-and-terms-of-use/)为 CC BY-NC-SA 4.0，但讲义内标明的第三方内容有例外；不能将整份 PDF 当作全部可再许可。仅用于本机非商业研究评测，原件与抽取文本留受控忽略区；不暗示 MIT 背书。题集支持页避开讲义内明确排除的第三方页。

## R7 冻结范围与恢复身份

- 课程：新隔离的 9.00SC 心理学课程；单课、仅四份 PDF。原始 264 页，解析出 252 个非空页单位和 257 个片段；未做 OCR、图像或公式专项。PyMuPDF 1.28.2，semantic-text-splitter 0.33.0；切分身份 `sts-0.33.0-char800-overlap120-r5-v1`。
- 代码：`9214ac3d0b6e0593114826df51467a78f7d3b4fb`；SQLAlchemy 2.0.52、Alembic 1.19.1、OpenAI SDK 3.6.0。新 PostgreSQL 16.15 / pgvector 0.8.7 库迁移至 0011，建库前空库和入库后数据库恢复包均保存在受控忽略区；原长期目标库未迁移核验。
- 索引：真实 SiliconFlow `BAAI/bge-m3`、1024 维，身份 `siliconflow|BAAI/bge-m3|1024|v1`；10 批实际嵌入请求、15,549 输入 token，四份任务成功。查询侧也是此索引模型。生成请求 `deepseek-v4-flash`，供应商实际返回 `deepseek-flash`；生成合同 `r6-context-citations-refusal-v1`。未调用 reranker。
- 题集：AI 预标 24 题，开发 8（可回答 6、应拒答 2）、封存测试 16（可回答 14、应拒答 2）；按知识点分组隔离。类型为 PDF 事实 16、跨页 4、相似但无答案 2、资料外 1、排除文档 1。没有人工支持位置、答案或判分复核，因而事实指标仅是 **AI 按预冻结要点评判**。20–30 题的首轮范围内，远小于约 80 题完整设计；不覆盖 PPTX/DOCX/文本、跨课权限或真实删除。
- 冻结哈希：资料清单 `3b3089a0602b99ee2676d501b83f97d09e9001bcd39cb3c49a135914db6a2f0f`；题集/要点 `80d495be66c5c0640e3537dcc74a5a5c7bb11b0fe8defc92b57431543ce4f758`；运行冻结 `8a8349dfaa8ed7a6d4a350060964243f63cc6ec53b9ced92aff8d6fe71a2f556`；本地受控运行脚本 `c72850f7e7602380d5146054e84b8c43a17d34ef23c74ccd76d50102f380d026`。这些原件均在 `corpus/local/r7-psychology-2026-10-16/`，不入 Git。
- 预算/停止：用户分别为两个 key 设置 10 元人民币硬额度；本次另限最多 48 次问答尝试、先 4 题开发集试跑、每次 I/O 阶段 20 秒、零重试，出错即停。未按测试结果筛题或调参。密钥与原题不进入本文。

## R7 实际结果：封存测试集

2026-10-16 两策略各运行同一 16 题，先完成 dense 开发集 4 题试跑，再跑其余 dense 与 hybrid；共 48 题次。下表分母固定，失败和退化保留。支持页到达指 AI 预标页进入最终证据，仍不等于事实正确。

| 指标 | dense | hybrid |
| --- | ---: | ---: |
| 可回答题：预期文档进入最终证据 | 14/14 | 14/14 |
| 可回答题：至少一处预标支持页进入最终证据 | 13/14 | 13/14 |
| 可回答题：合法引用 ID | 12/14 | 12/14 |
| 可回答题：AI 判完整必需要点 | 7/14 | 9/14 |
| 可回答题：AI 判部分要点 | 1/14 | 0/14 |
| 可回答题：只有引用而无实质答案 | 4/14 | 3/14 |
| 可回答题：错误拒答 | 2/14 | 2/14 |
| 应拒答题：正确拒答 | 2/2 | 2/2 |
| 有实质且有引用的回答：AI 判引用快照支持主张 | 8/8 | 9/9 |
| 单题检索+生成墙钟 p50 / p95 | 1,049.9 / 2,200.0 ms | 1,187.0 / 2,084.4 ms |
| 已运行题次的服务/索引失败 | 0/16 | 0/16 |

开发集 dense 完整要点 6/6、hybrid 5/6；两者正确拒答均 2/2。全部 48 次尝试中未见服务/索引失败，但未运行的权限、独立试用、重排和故障注入不计为零失败。测试集 14/16 题的两策略最终证据片段序列完全相同；hybrid 多出的两道完整要点题其最终证据也相同，温度 0.2 的生成波动可能解释差异，**不能归因为 hybrid 检索增益**。关键词独有候选仍过保守余弦准入，未验证完整互补召回。AI 自审存在共同错误风险，以上不称人工核验正确率。逐题输出和审查记录留受控忽略区。

## 延迟、用量、费用与失败边界

上述延迟含真实网络检索/生成，不含入库，单次测量、nearest-rank p95；不能推断并发容量。总用量：SiliconFlow 嵌入 58 请求（入库 10、查询 48），16,657 输入 token；DeepSeek 生成 46 请求（两策略排除文档题均无证据，未生成），cache-miss 输入 28,257、cache-hit 输入 13,056、输出 2,591 token。无重试、无超时或服务/索引故障。本次未调重排，也未验证实际账单。

按 [DeepSeek 官方价格表](https://api-docs.deepseek.com/quick_start/pricing/)中 `deepseek-flash` 费率估算，本次离峰约 USD 0.00583，按峰时价上界约 USD 0.01167；**是用量估算而非实际扣费或人民币账单**。 [SiliconFlow 官方价目](https://siliconflow.cn/pricing)列 `BAAI/bge-m3` 免费，但未独立读取账户账单，不把实际支出写成 0。两个 key 的 10 元硬上限由用户确认，本次用量与失败边界不等同账户结算证明。

受控恢复包 SHA-256：空库0011 `E543B98A50B33819D3552364298209C01B9BDFF88C604CE611C6D9C4DEA91CC1`；入库后0011 `b695959bb8201a7e21c611df4a78d47bb58c30616c2037ffde18fd49e7506d4d`；AI 审查记录 `63422c8a003df431fa9d40c75c6f63b3d48fc7e77e7e9936fb77789300daabcb`；脱敏汇总 `0d27bed5ace6627051459e60f86d60975c8bd551c44c2f404d6ea82ab0e44441`。恢复需对应受控源文件、配置、代码及数据库恢复包；哈希本身不提供公开原题或数据库。

## 新结果登记规则

只有实际执行后才补充：运行日期、可恢复代码/依赖/配置标识、资料与题集哈希、模型/索引身份、切分版本、检索/生成/重排设置、题型和分母、事实/引用/拒答/权限/延迟/费用结果、失败/降级与人工审查边界。

每个结果说明真实/Fake、数据范围与可复现条件；同一版本同一题集的对照才能直接比较。缺项写待验，不移植旧指标或虚构独立反馈。原课件、问题/答案、逐题输出、引用UUID、身份、数据库连接和凭据不得进入本文，留受控忽略区。

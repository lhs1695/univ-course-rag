# PLAN-09 观察表（开发者 Vite 代观察）

脚本版本 `p09-tasks-v1`。记录 ID：`obs-2026-10-23-developer`。

| 登记项 | 值 |
| --- | --- |
| 记录 ID / 日期 / 观察者代号 | obs-2026-10-23-developer / 2026-10-23 / developer |
| 参与者匿名代号 / 角色 | developer-self / 学生+教师 |
| 是否参与开发 / 是否独立操作 | 是 / 否（用户授权开发者代观察，**不作独立试用**） |
| 证据层 | 开发者 Vite（Playwright Chromium headless + 截图） |
| 环境 | Windows / Chromium(Playwright) / http://127.0.0.1:5173 / uvicorn:8000 / Postgres cn_v2 |
| 代码提交 / 脚本版本 / 输入冻结 | 6269e8f 起观察；观察脚本 `scripts/plan09-developer-vite-observe.py` / `plan09-teacher-ascii.py`；p09-tasks-v1 |
| 模型 / 检索 / rerank / 云费用 | deepseek（已配置） / dense / 关 / 本轮 Vite+小样本估 << ¥2（未读账单；未 Vision/重入库） |
| 课程 / 角色 | 线性代数 / student + teacher |
| 问句与资料 | S1/S4：LA-01；S2 近似：LA-R；PDF：`01-linear-algebra-full.pdf`；目标页以回答引用为准（观察见第 10 页） |
| 本轮任务 / 计划 N | 学生 S1–S4、教师 T1–T3 / 学生 4、教师 3 |
| 前置缺失 / 中止 | S3 无隔离 Fake 故障注入；T1 演示库无 `failed` 资料；**空白机+备份恢复：用户指示暂缓** |

## 任务结果

| 任务 ID | 结果 | 实际行为与成功条件核对 | 证据 |
| --- | --- | --- | --- |
| S1 | **开发者观察通过**（非独立） | 登录 student→线性代数→LA-01→有回答与非空依据→依据卡显示讲义第 10 页→「打开原 PDF · 第 10 页」href 指向同文档 `/content#page=10`；PDF 字节接口返回 `%PDF`。主张与摘录可见支持关系（弱核验，不宣称金标正确率）。Headless 弹窗截图不稳，不以截图代替 href+content 核验。 | `evidence-2026-10-23/s1-answer.png`；PDF content 200 |
| S2 | **近似通过（LA-R）** / 正式隔离场景前置缺失 | LA-R 得到「课内资料依据不足…」+ 0 条依据 +「浏览课程资料」链接；已点进资料页。未预置专用「无可用依据」隔离集。 | `s2-la-r.png` `s2-documents.png` |
| S3 | **前置缺失** | 未启用隔离 Fake 超时/不可用；不硬造故障。 | — |
| S4 | **开发者观察通过**（非独立） | 提问后可见等待态；点「取消回答」→「请求已中断，输入已保留。」+「重试本次问题」；提交按钮可再点；重试后再次得到带引用回答。 | `s4-after-cancel.png` `s4-retry-answer.png` |
| T1 | **部分通过** | 资料表：`succeeded` + 橙色「部分页面解析疑问」警告文案正确；可打开 PDF（href `#page=10`）。演示库**无**整份 `failed` 资料 → 失败对照前置缺失。 | `t1-documents.png`；teacher JSON href |
| T2 | **开发者观察通过** | 问答反馈页有主题候选/统计；填写处理对象/意图/知识点/行动→保存→toast「已保存处理记录」且表中可见。 | `t2-insights.png` `t2-after-save.png`；`observation-teacher.json` |
| T3 | **开发者观察通过** | 「刷新记录」后仍在；整页 reload 后仍在；未被迫重新登录。 | `t3-refresh-records.png` `t3-full-reload.png` |

## 困惑/失败 / 阻断

| ID | 任务 | 现象 | 严重度 | 回流 |
| --- | --- | --- | --- | --- |
| B1 | S1/T1 | Playwright headless 打开 PDF 弹窗后 screenshot/`domcontentloaded` 易超时；**产品链接与 PDF 字节正常**，判为观察工具限制非产品阻断 | 一般 | 不改产品；真人浏览器核验链接即可 |
| B2 | T1 | 演示库无 failed 资料，无法对照「警告 vs 整份失败」 | 前置缺失 | 需合成失败样例卡另授权时补 |
| B3 | S3 | 无隔离故障注入场景 | 前置缺失 | 可后续接 Fake 故障开关 |

**本轮无已确认的产品阻断 UX/bug 需立刻修代码。**

## 汇总

| 汇总 | 结果 |
| --- | --- |
| 开发者 Vite 完成 | S1/S4/T2/T3 通过；S2 近似；T1 部分；S3 前置缺失 |
| 独立试用 | **未做**（用户指示去掉，改开发者代观察） |
| 空白机+备份恢复 | **用户指示暂缓** |
| 是否可宣告独立试用通过 | **否** |
| 下一步 | 真实模型小样本留证；空白机暂缓；无阻断则不改代码 |

观察时刻：2026-10-23 08:40 Asia/Shanghai

## 真实小样本

- 路径：`docs/user-task-scripts/evidence-2026-10-23/real-small-sample-2026-10-23-developer.json`（与 `results/` 同内容；`results/` gitignore）
- LA-01：cited p10；LA-R：NO_EVIDENCE；估费 <¥1，累计 <<¥2。

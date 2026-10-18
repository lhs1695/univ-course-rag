# 中期汇报演示运行卡

更新：2026-10-18。与 `build/midterm-presentation/output/final-v4.pptx` 配套；完整验收协议见 [validation.md 的演示与恢复](validation.md#demo)，R8 事实证据见 `corpus/local/r8-joint-acceptance-2026-10-17/`。

## 目标与时间

- 汇报：约 6–8 分钟；产品实走：约 3–5 分钟。
- 只证明本机四课文本型问答原型、引用跳转、失败状态与已验收的权限边界。
- 不宣称人工事实正确率、通用多模态理解、生产部署或非开发者独立试用。

## 演示前检查

1. 启动本机 PostgreSQL；目标库必须是 `univ_course_rag_r7b6_real`，migration `0011`，规模 **4 门课 / 17 份 PDF / 385 chunks**。
2. 在启动后端的 PowerShell 终端中，进程级设置 `DATABASE_URL`：保留本机原连接串，只把数据库名改成 `univ_course_rag_r7b6_real`。不要修改 `.env` 并提交密钥。
3. 从仓库根启动后端：

   ```powershell
   backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
   ```

4. 在 `frontend` 目录运行 `npm run dev`，浏览器访问 `http://127.0.0.1:5173`；登录必须走 Vite，不直连 `:8000`。
5. 检查 `/health`、`/ready`、`/runtime`，并再次确认数据库为 `r7b6_real`。`configured` 只代表本地配置状态，不代表模型供应商连通。
6. 确认 `student` 已加入四门演示课。不要使用隔离恢复库 `univ_course_rag_r9_restore_20261018`，不要重新入库、临场换模型或启动旧 Docling 任务。

**任一步失败就停。** 不在答辩现场排查密钥、重建数据库或临时重跑全量评测；改用下方备用截图并说明实际边界。

## 建议演示顺序

| 顺序 | 操作 | 预期 / 讲解重点 |
| --- | --- | --- |
| 1. 学生正常问答 | 登录 `student` → 我的课程 → 心理学课 → 提问 PSY-D01 | 有回答与引用卡片；点“查看原资料”打开 `01_introduction.pdf` 对应页（`#page=2`）。讲清楚引用用于回到原文核对，不等于主张已被证明。 |
| 2. 依据不足 | 提问 PSY-D03 | 问句：`According to these 9.00SC psychology PDFs, what is the half-life of carbon-14 used in radiocarbon dating?` 预期 `NO_EVIDENCE` / 依据不足；不能编造半衰期。 |
| 3. 教师覆盖警告 | 登录 `teacher` → 打开心理学课资料页 | 展示“已入库（覆盖不全）”及文本覆盖警告。强调页级质量门禁是风险提示，不是完整性证明。 |
| 4. 失败与重试 | 优先展示 R8 已留存截图；若现场时间充足再实走 | 已提交问句后制造后端中断，确认页面显示系统失败而非 `NO_EVIDENCE`；修改草稿为无关诱饵后点“重试本次问题”，重试必须发送原已提交问句。恢复后端并确认 `/ready`。证据：`04-failure-retry-visible.png`、`04-after-retry.png`。 |
| 5. 权限边界 | 口头说明 R8 API 已验收；只有有专用测试成员且能立即恢复时才现场操作 | 撤权后再次请求或打开未授权课程必须被拒绝；同名 `01_introduction.pdf` 不得跨心理学/哲学串课。不要为了演示随意删课。 |

固定问句：

- **PSY-D01**：`According to the 9.00 Intro to Psychology lecture, what is the stated course objective?`
- **PSY-D03**：`According to these 9.00SC psychology PDFs, what is the half-life of carbon-14 used in radiocarbon dating?`
- **PHIL-D01（可选）**：`In Yablo’s introduction, list two reasons given under “Language is special.”` 必须在哲学课提问，核对同名 PDF 不串心理学。
- **PHIL-T02（可选观察）**：`What informative-identity example does Frege’s critique use involving Hesperus?` 当前可能出现“检索命中但生成拒答”；这属于已知质量边界，不要包装成检索成功或系统故障。

## 汇报数字怎么说

- `23/23`：可回答题命中预期文档/页；`27/28`：自动弱引用支持检查；`5/5`：预期拒答题判定为拒答。
- 题集为 AI 预标，未独立人工复核；以上都不是人工事实正确率。余弦阈值 `0.45` 未校准。
- Hybrid 只完成检索对照，未运行生成，不能说它优于 Dense。
- 真实供应商人民币账单未核对；OCR、纯图片、可靠公式恢复与图表理解未覆盖。
- 数据库与文件隔离恢复子项已通过，但 P7 整体仍部分完成；Demo Reset 与成本/资源专项仍待验。

## 收尾与故障降级

1. 若做过成员撤权，立刻恢复 `student` 在四门演示课的成员关系并核对课程列表。
2. 不在现场清理数据或修改题集；结束后可停止本轮启动的前后端进程。
3. 真实模型返回异常时不循环重试、不切换供应商；保留失败状态，转用 R8 截图继续汇报。
4. 录屏不显示密码、`.env`、Cookie、连接串或个人信息。

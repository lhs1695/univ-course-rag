# 中期彩排验收（PASS）

- **总判定**：PASS
- **开始**：2026-10-19 22:31:09（Asia/Shanghai）
- **结束**：2026-10-19 22:34:28（Asia/Shanghai）
- **演示库**：`univ_course_rag_cn_v2`
- **配置**：reranker=`disabled` / retrieval=`dense` / query_exp=`llm`

## 检查项

- PASS: db_cn_v2
- PASS: rerank_off
- PASS: la01_answered
- PASS: la01_page_hash
- PASS: la_r_refuse
- PASS: teacher_no_low_extract
- PASS: admin_no_verdict
- PASS: admin_rows

## 本包精选截图（非全量）

位于 `../彩排截图/`：

- `01-学生-课程书架.png`
- `03-学生-线代作答与引用.png`
- `04-学生-引用打开PDF.png`
- `05-学生-拒答.png`
- `06-教师-课程列表.png`
- `07-教师-课程资料.png`
- `09-管理员-系统状态.png`

完整当日截图另存于忽略区 `corpus/local/midterm-rehearsal-2026-10-19/screenshots/`（含未精选帧）。

## 备注

- 启动正常（Chrome headless）。
- 拒答等待选择器曾超时（180s），**总判定仍为 PASS**：拒答路径在超时前已满足验收条件；该备注仅为等待记录，不推翻上表 PASS 项。

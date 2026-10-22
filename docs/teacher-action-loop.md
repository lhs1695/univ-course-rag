# 教师知识点与人工处理闭环（PLAN-05）

> 更新：2026-10-22（Asia/Shanghai）  
> 对齐：[metrics-data-boundary.md](metrics-data-boundary.md)

## 持久化

表 `insight_reviews`（Alembic `0013`）：课程内教师对线索/分组/问句的确认与处理记录。

| 字段 | 含义 |
| --- | --- |
| subject_type | `group` / `clue` / `query_text` |
| subject_key | 代表问句或线索标题（非学生身份） |
| intent_code | 教师确认的意图（可空） |
| knowledge_point | 轻量知识点字符串；无大纲时可为「待归类」 |
| review_status | confirmed / rejected / deferred / split |
| cause_code | coverage_gap / retrieval_citation / question_wording / normal_review / undecidable |
| action_code | update_material / clarify_in_class / add_regression / no_action / investigate_system |

## API

- `GET/POST /courses/{id}/insight-reviews`
- `PATCH /courses/{id}/insight-reviews/{review_id}`
- 仅课内教师；跨课 403。

## 迁移

正式 Postgres：`alembic upgrade head`（含 0013）。测试 SQLite 经 `create_all`。

## 不做

不自动改资料/重入库；`add_regression` 只记录意图，人工把代表问句加入题集。

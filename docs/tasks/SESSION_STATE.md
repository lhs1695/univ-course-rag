# SESSION_STATE

会话外状态（长任务用）。更新：2026-10-23（Asia/Shanghai）。

## 当前目标

**PLAN-00～10 本地切片 done（多卡为 Fake/文档限定范围）**。结题验收**未宣告通过**。
用户已授权：**去掉独立用户试用**，改由开发者 Vite 代观察验收；**空白机安装+备份恢复暂缓**；Vite 观察后做真实模型小样本（累计云花费 ≤¥2）。

## 已定

- 只本地 commit；不默认 push/发布
- 独立试用：取消；以开发者 Vite 观察代替（见 `docs/user-task-scripts/observation-2026-10-23-developer.md`）
- 空白机+备份恢复：用户指示暂缓
- PLAN-08/09 Vite：开发者观察已执行（S1/S4/T2/T3 通过；S2 近似；T1 部分；S3 前置缺失）
- 本轮未发现需立刻修的产品阻断；PDF headless 截图不稳属工具限制
- **中期冻结演示 worktree（展示完可删）**：`D:\workspace\univ-course-rag-midterm` ← tag `midterm-freeze-2026-10-21`（`f8278d7`）；后端 `http://127.0.0.1:8001`，前端 `http://127.0.0.1:5174`；共用主库 `univ_course_rag_cn_v2`（0013，只读演示冒烟已通）。删除：先停 8001/5174，再 `git -C D:\workspace\univ-course-rag worktree remove D:\workspace\univ-course-rag-midterm`（未建副本库，勿 DROP 主 `cn_v2`）

## 下一步

1. 老师展示用 midterm worktree；展示完按上文删除
2. 空白机+备份恢复：暂缓，待用户再指示
3. 用户点名后才考虑 push / 公开发布材料冻结

## 活跃 diff

- （提交后清空）

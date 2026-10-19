# 教师与 Admin 设计说明（合并）

更新：2026-10-19。本文合并原 `DESIGN-NOTES-STAFF.md`、`DESIGN-NOTES-STAFF-STUDY-ALIGN.md`、`DESIGN-NOTES-ADMIN-COPY.md`。学生端说明仍见 [DESIGN-NOTES.md](DESIGN-NOTES.md)。旧稿全文见 `docs/archive/`。

## 定位

教师管理学生与核对问答，管理员维护账号、课程授权和系统状态；各页继续以操作栏和表格回答管理问题。Staff/admin 与学生端同属「课程知识库」：延续学生 A 的纸白、冷白、葡萄紫与宋体书签气质，但管理页不用学生书架布局。

## 品牌 Token 与壳

- Token：纸白 `#FFFFFF`、冷白 `#F8F7FB`、葡萄紫 `#633A88`、墨紫 `#342447`、淡藤 `#EEE8F5`、铅笔黄 `#F0D97C`、线 `#DDD6E5`。黄色仅作品牌 token。Element Plus primary 深浅阶与 `student.css` 一致；成功/警告/删除保留语义色。
- 壳策略：横向导航、约 1200px 内容区、白纸操作面板与清晰表格；顶栏紫色「课」书签为造型标识。管理员与教师标题可用 `STSong` / `SimSun` / `Songti SC`；页签可用紫底白字圆角选中态。
- 复用：Vue 3 + Element Plus（lockfile 版本），不新增依赖/字体/外部素材。只适配 CSS 与模板文案；创建、授权、移出、刷新等业务逻辑保持原样。

## 学生边界（勿破）

`App.vue` 的 `studentSurface`、`.study-app`、`student.css`、Login / Courses / Ask / Documents 学生路径不因 staff 对齐而改。教师 Documents 可继续留在学生壳共享紫色表格 token，上传与入库逻辑不变。Members / Insights 与 `/admin/*` 走 `app-shell`，路由守卫不变。

## 文案与布局收口（原 ADMIN-COPY）

- 系统状态：简洁 verdict + 库/向量/生成键值 + 下一步；Fake/configured 用白话；细节默认可见。
- 提问日志维护：预览优先；无匹配时隐藏删除；不可逆范围写在确认框。
- 课程创建并入课程列表面板；行操作「进入」+ 菜单；成员授权标题稳定。
- 账号文案用「系统角色」；种子账号说明留在页内；改密/停用诚实标明需运维（无假接口）。
- Staff 导航可换行；表格保留横向滚动；维护页标「高级」，演示时勿当场删除。

## 变更史摘要

| 批次 | 要点 |
| --- | --- |
| A 品牌对齐 | staff/admin 壳对齐学生 A 紫色书签；7 个前端文件级改动；静态解析与 `git diff --check` 通过 |
| STUDY-ALIGN | `.app-shell` 范围 CSS 加深与学生 token 一致；证据 `corpus/local/demo-staff-study-align-2026-10-19/` |
| ADMIN-COPY | 仅文案/模板/CSS；无 API/权限变更 |
| F1–F20 | 角色选壳、原文入口、反馈降噪等；逐项见 [docs/archive/NOTES-F1-F20.md](../docs/archive/NOTES-F1-F20.md) |

## 验收提示

构建与 Playwright 三角色走查由外层/演示环境完成；静态检查不能替代浏览器验收。未宣称生产级无障碍认证。

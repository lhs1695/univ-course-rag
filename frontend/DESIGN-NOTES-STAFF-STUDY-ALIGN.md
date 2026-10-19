# Staff 壳与学生 A 视觉对齐

Staff/admin 是同一本课程知识库里的管理章：延续学生 A 的纸白、冷白、葡萄紫与宋体书签；管理工作仍使用清楚的表格、列表和表单。

本项复用 `student.css` / `styles.css` 现有品牌 token、Vue 3 与 Element Plus 组件，只增加 `.app-shell` 范围内的 CSS。管理员和教师标题使用 `STSong` / `SimSun` / `Songti SC`；页眉使用紫色剪角书签；卡片、表单和表格使用白纸、淡紫描边与轻阴影；课程内页签使用紫底白字圆角选中态。导航、权限、API、业务文案和学生 `study-app` 页面未改。

验收与截图：`corpus/local/demo-staff-study-align-2026-10-19/STATUS.md` 和 `results.json`（本机忽略区）。

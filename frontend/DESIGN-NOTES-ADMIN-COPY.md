# Admin copy and layout cleanup

Admin and teacher staff pages retain the existing Vue 3 / Element Plus shell and A bookmark palette. This pass changes only staff copy, template composition, and staff-shell CSS; no API, permission, or operational logic changed. Student pages and the `studentSurface` book shell remain unchanged.

- System status uses a concise verdict, database/vector/generation key-value rows, and one next step. Fake and configured statuses are described in plain language; the detail is visible by default.
- Query-log maintenance uses “提问日志”, puts preview first, removes presentation instructions, and hides the delete action when no records match. Irreversible-scope information stays with the confirmation and compact warning.
- Course creation now shares the course-list panel. Row actions are “进入” plus a menu; member authorization has a stable heading and a separate course label.
- Account copy uses “系统角色”, includes the seed credentials in-page, and states where password and disable requests go.
- Staff navigation and header copy describe administration/teaching work. Staff headings use system sans-serif, the bookmark is smaller, table density is slightly tighter, wrapping is Chinese-friendly, and admin has a minimal footer.

Reuse decision: existing Element Plus alerts, descriptions, dropdowns, forms, and tables cover these display and interaction needs; no new package or custom interaction framework was needed. Acceptance is a focused frontend build and static diff review. Browser interaction and visual acceptance remain for the outer Playwright pass.

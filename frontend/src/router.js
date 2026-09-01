import { createRouter, createWebHistory } from "vue-router";
import { refreshMe, session } from "./session";
import LoginView from "./views/LoginView.vue";
import CoursesView from "./views/CoursesView.vue";
import AskView from "./views/AskView.vue";
import DocumentsView from "./views/DocumentsView.vue";
import InsightsView from "./views/InsightsView.vue";
import MembersView from "./views/MembersView.vue";
import AdminUsersView from "./views/AdminUsersView.vue";
import AdminCoursesView from "./views/AdminCoursesView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView, meta: { public: true } },
    { path: "/", redirect: "/courses" },
    { path: "/admin/users", component: AdminUsersView, meta: { admin: true } },
    { path: "/admin/courses", component: AdminCoursesView, meta: { admin: true } },
    { path: "/courses", component: CoursesView },
    { path: "/courses/:courseId/documents", component: DocumentsView },
    { path: "/courses/:courseId/members", component: MembersView, meta: { teacher: true } },
    { path: "/courses/:courseId/insights", component: InsightsView },
    { path: "/courses/:courseId", component: AskView },
  ],
});

router.beforeEach(async (to) => {
  if (!session.ready) {
    await refreshMe();
  }
  if (!to.meta.public && !session.user) {
    return { path: "/login", query: { next: to.fullPath } };
  }
  if (to.meta.admin && session.user?.role !== "admin") {
    return "/courses";
  }
  if (to.meta.teacher && session.user?.role !== "teacher") {
    return "/courses";
  }
  if (to.path === "/login" && session.user) {
    return session.user.role === "admin" ? "/admin/users" : "/courses";
  }
  return true;
});

import { ElMessage } from "element-plus";
import { createRouter, createWebHistory } from "vue-router";
import { refreshMe, session } from "./session";
import { clearCourseAccess, refreshCourseAccess } from "./courseAccess";
import LoginView from "./views/LoginView.vue";
import CoursesView from "./views/CoursesView.vue";
import AskView from "./views/AskView.vue";
import DocumentsView from "./views/DocumentsView.vue";
import InsightsView from "./views/InsightsView.vue";
import MembersView from "./views/MembersView.vue";
import AdminUsersView from "./views/AdminUsersView.vue";
import AdminCoursesView from "./views/AdminCoursesView.vue";
import AdminMaintenanceView from "./views/AdminMaintenanceView.vue";
import AdminSystemStatusView from "./views/AdminSystemStatusView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/login", component: LoginView, meta: { public: true } },
    { path: "/", redirect: "/courses" },
    { path: "/admin/users", component: AdminUsersView, meta: { admin: true } },
    { path: "/admin/courses", component: AdminCoursesView, meta: { admin: true } },
    { path: "/admin/maintenance", component: AdminMaintenanceView, meta: { admin: true } },
    { path: "/admin/system", component: AdminSystemStatusView, meta: { admin: true } },
    { path: "/courses", component: CoursesView },
    { path: "/courses/:courseId/documents", component: DocumentsView },
    { path: "/courses/:courseId/members", component: MembersView, meta: { capability: "can_manage_members" } },
    { path: "/courses/:courseId/insights", component: InsightsView, meta: { capability: "can_view_insights" } },
    { path: "/courses/:courseId", component: AskView },
  ],
});

router.beforeEach(async (to, from) => {
  if (!session.ready || (session.user && !to.meta.public)) {
    const verified = await refreshMe();
    if (!verified && session.error && session.error.status !== 401) {
      session.retryPath = to.fullPath;
      return from.matched.length ? false : true;
    }
  }
  if (!to.meta.public && !session.user) {
    return { path: "/login", query: { next: to.fullPath } };
  }
  if (to.meta.admin && session.user?.role !== "admin") {
    sessionStorage.setItem("accessDeniedFlash", "你没有访问这个页面的权限");
    ElMessage.warning("你没有访问这个页面的权限");
    return "/courses";
  }
  if (to.params.courseId) {
    try {
      const course = await refreshCourseAccess(String(to.params.courseId));
      if (!course || (to.meta.capability && !course.capabilities[to.meta.capability])) {
        clearCourseAccess();
        sessionStorage.setItem("accessDeniedFlash", "你没有访问这个页面的权限");
        ElMessage.warning("你没有访问这个页面的权限");
        return "/courses";
      }
    } catch (error) {
      if (![401, 403, 404].includes(error.status)) {
        session.retryPath = to.fullPath;
        return from.matched.length ? false : true;
      }
      if (session.user) {
        sessionStorage.setItem("accessDeniedFlash", "你没有访问这个页面的权限");
        ElMessage.warning("你没有访问这个页面的权限");
      }
      return session.user ? "/courses" : "/login";
    }
  } else {
    clearCourseAccess();
  }
  if (to.path === "/login" && session.user) {
    return session.user.role === "admin" ? "/admin/users" : "/courses";
  }
  session.retryPath = "";
  return true;
});

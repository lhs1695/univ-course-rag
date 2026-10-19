<template>
  <a class="skip-link" href="#main-content" @click.prevent="focusMain">跳到主要内容</a>
  <el-container class="app-shell" :class="{ 'student-shell': studentExperience, 'entry-shell': route.path === '/login' }">
    <StudentNavigation v-if="studentExperience && session.user" :course="currentCourse" @logout="onLogout" />
    <el-header class="app-header" v-if="session.user && !studentExperience">
      <router-link class="app-title" to="/courses"><span class="brand-mark" aria-hidden="true">课</span><span>课程知识库<small>有依据，可核对</small></span></router-link>
      <div class="app-user">
        <span class="role-pill">{{ roleLabel }}</span>
        <span class="username">{{ session.user.username }}</span>
        <el-button text @click="onLogout">退出</el-button>
      </div>
    </el-header>
    <nav v-if="session.user && !studentExperience" class="global-nav" aria-label="主导航">
      <template v-if="isAdmin">
        <router-link to="/admin/users">账号管理</router-link>
        <router-link to="/admin/courses">课程与授权</router-link>
        <router-link to="/admin/maintenance">日志维护</router-link>
        <router-link to="/admin/system">系统状态</router-link>
      </template>
      <router-link to="/courses" :aria-current="route.path === '/courses' ? 'page' : undefined" :class="{ 'nav-selected': !route.path.startsWith('/admin') }">我的课程</router-link>
    </nav>
    <el-main id="main-content" tabindex="-1">
      <nav v-if="pageAllowed && currentCourse && !studentExperience" class="course-nav" aria-label="当前课程导航">
        <div class="course-context"><span>当前课程</span><strong>{{ currentCourse.title }}</strong><span class="role-pill">课内{{ currentCourse.membership_role === 'teacher' ? '教师' : '学生' }}</span></div>
        <div class="course-tabs">
          <router-link :to="`/courses/${currentCourse.id}`" exact-active-class="tab-selected">课程问答</router-link>
          <router-link :to="`/courses/${currentCourse.id}/documents`" exact-active-class="tab-selected">课程资料</router-link>
          <router-link v-if="currentCourse.capabilities.can_manage_members" :to="`/courses/${currentCourse.id}/members`" exact-active-class="tab-selected">本课学生</router-link>
          <router-link v-if="currentCourse.capabilities.can_view_insights" :to="`/courses/${currentCourse.id}/insights`" exact-active-class="tab-selected">问答反馈</router-link>
        </div>
      </nav>
      <template v-if="recoveryError">
        <el-alert :title="recoveryError.message" type="warning" :closable="false" />
        <el-button v-if="recoveryError.status !== 401" :loading="recovering" @click="retryConnection">重试连接</el-button>
        <el-button v-else @click="router.push({ path: '/login', query: { next: route.fullPath } })">重新登录</el-button>
      </template>
      <router-view v-if="pageAllowed" :key="`${route.fullPath}:${courseAccess.revision}`" />
      <template v-else-if="!recoveryError">
        <el-alert title="访问权限已变化，请重新选择课程或登录。" type="warning" :closable="false" />
        <el-button @click="router.push(session.user ? '/courses' : '/login')">返回</el-button>
      </template>
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { logout, refreshMe, session } from "./session";
import { clearCourseAccess, courseAccess, refreshCourseAccess } from "./courseAccess";
import StudentNavigation from "./components/StudentNavigation.vue";

const router = useRouter();
const route = useRoute();
const studentExperience = computed(() => route.path === '/login' || session.user?.role === 'student');
const isAdmin = computed(() => session.user?.role === "admin");
const roleLabel = computed(() => ({ admin: "管理员", teacher: "教师", student: "学生" }[session.user?.role] || ""));
const currentCourse = computed(() => courseAccess.course?.id === route.params.courseId ? courseAccess.course : null);
const recovering = ref(false);
const recoveryError = computed(() => {
  const error = session.error || courseAccess.error;
  return route.meta.public && error?.status === 401 ? null : error;
});
const pageAllowed = computed(() => {
  if (route.meta.public) return true;
  if (!session.user) return false;
  if (route.meta.admin && !isAdmin.value) return false;
  if (!route.params.courseId) return true;
  const course = courseAccess.course;
  return course?.id === route.params.courseId &&
    (!route.meta.capability || course.capabilities[route.meta.capability]);
});

async function recheckAccess() {
  if (document.hidden || route.meta.public || !session.user) return;
  if (!await refreshMe()) return;
  if (!session.user) return;
  if (!route.params.courseId) {
    if (route.path === "/courses") clearCourseAccess();
    return;
  }
  try {
    await refreshCourseAccess(String(route.params.courseId));
  } catch {
    // The access loader clears confirmed denial; keep the view for network recovery.
  }
}

async function retryConnection() {
  if (recovering.value) return;
  recovering.value = true;
  try {
    if (!await refreshMe()) return;
    const target = session.retryPath || route.fullPath;
    const courseId = target.match(/^\/courses\/([^/?]+)/)?.[1];
    if (courseId) await refreshCourseAccess(courseId);
    session.retryPath = "";
    await router.replace(target);
  } catch {
    // The session/access store supplies the persistent failure message.
  } finally { recovering.value = false; }
}

onMounted(() => {
  window.addEventListener("focus", recheckAccess);
  document.addEventListener("visibilitychange", recheckAccess);
});
onUnmounted(() => {
  window.removeEventListener("focus", recheckAccess);
  document.removeEventListener("visibilitychange", recheckAccess);
});

async function onLogout() {
  try {
    await logout();
    await router.push("/login");
  } catch (error) {
    ElMessage.error(error.message);
  }
}

function focusMain() {
  const main = document.getElementById("main-content");
  main?.focus();
  main?.scrollIntoView({ block: "start" });
}
</script>

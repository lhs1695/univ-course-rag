<template>
  <div class="study-app" v-if="studentSurface">
    <a class="skip-link" href="#main-content" @click.prevent="focusMain">跳到主要内容</a>
    <header class="study-header">
      <router-link to="/courses" class="study-brand"><span class="bookmark-logo" aria-hidden="true">课</span>课程知识库</router-link>
      <div v-if="session.user" class="study-account"><router-link v-if="isAdmin" to="/admin/users">管理后台</router-link><span>{{ session.user.username }}</span><button class="quiet-button" @click="onLogout">退出登录</button></div>
      <span v-else class="brand-promise">让每一个答案，有出处。</span>
    </header>
    <main id="main-content" tabindex="-1" class="study-main" :class="{ 'is-login': route.path === '/login' }">
      <nav v-if="session.user" class="study-navigation" aria-label="课程导航">
        <router-link to="/courses" class="shelf-link">我的课程</router-link>
        <template v-if="currentCourse"><span aria-hidden="true">/</span><strong>{{ currentCourse.title }}</strong><div class="study-tabs"><router-link :to="`/courses/${currentCourse.id}`" exact-active-class="is-active">提问</router-link><router-link :to="`/courses/${currentCourse.id}/documents`" exact-active-class="is-active">资料</router-link><router-link v-if="currentCourse.capabilities.can_manage_members" :to="`/courses/${currentCourse.id}/members`">本课学生</router-link><router-link v-if="currentCourse.capabilities.can_view_insights" :to="`/courses/${currentCourse.id}/insights`">问答反馈</router-link></div></template>
        <span v-else class="navigation-note">从一门课开始，读懂一个问题。</span>
      </nav>
      <div v-if="recoveryError" class="recovery-box"><el-alert :title="recoveryError.message" type="warning" :closable="false"/><el-button v-if="recoveryError.status !== 401" :loading="recovering" @click="retryConnection">重试连接</el-button><el-button v-else @click="router.push({path:'/login',query:{next:route.fullPath}})">重新登录</el-button></div>
      <router-view v-if="pageAllowed" :key="`${route.fullPath}:${courseAccess.revision}`"/>
      <div v-else-if="!recoveryError" class="study-empty"><h2>访问权限已变化</h2><p>请重新选择课程或登录。</p><router-link :to="session.user ? '/courses' : '/login'">返回</router-link></div>
    </main>
    <footer class="study-footer"><span>课程知识库</span><span>以课内资料为据，带着问题阅读。</span></footer>
  </div>

  <el-container v-else class="app-shell">
    <el-header class="app-header" v-if="session.user">
      <router-link class="app-title" to="/courses"><span class="staff-bookmark" aria-hidden="true">课</span><span>课程知识库<small>有依据，可核对</small></span></router-link>
      <div class="app-user">
        <span class="role-pill">{{ roleLabel }}</span>
        <span class="username">{{ session.user.username }}</span>
        <el-button text @click="onLogout">退出登录</el-button>
      </div>
    </el-header>
    <nav v-if="session.user" class="global-nav" aria-label="主导航">
      <template v-if="isAdmin">
        <router-link to="/admin/users">账号管理</router-link>
        <router-link to="/admin/courses">课程与授权</router-link>
        <router-link to="/admin/maintenance">日志维护 · 高级</router-link>
        <router-link to="/admin/system">系统状态</router-link>
      </template>
      <router-link to="/courses" :aria-current="route.path === '/courses' ? 'page' : undefined" :class="{ 'nav-selected': !route.path.startsWith('/admin') }">我的课程</router-link>
    </nav>
    <el-main id="main-content" tabindex="-1">
      <nav v-if="pageAllowed && currentCourse" class="course-nav" aria-label="当前课程导航">
        <div class="course-context"><span>当前课程</span><strong>{{ currentCourse.title }}</strong><span class="role-pill">课内{{ currentCourse.membership_role === 'teacher' ? '教师' : '学生' }}</span></div>
        <div class="course-tabs">
          <router-link :to="`/courses/${currentCourse.id}`" exact-active-class="tab-selected">提问</router-link>
          <router-link :to="`/courses/${currentCourse.id}/documents`" exact-active-class="tab-selected">资料</router-link>
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

const router = useRouter();
const route = useRoute();
const studentSurface = computed(() => route.path === "/login" || (session.user?.role === "student" && route.path.startsWith("/courses")));
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
    if (error.status !== 401) ElMessage.error(error.message);
  }
}

function focusMain() {
  const main = document.getElementById("main-content");
  main?.focus();
  main?.scrollIntoView({ block: "start" });
}
</script>

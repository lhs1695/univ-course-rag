<template>
  <div class="workspace" :class="{ 'student-workspace': isStudent, 'staff-workspace': !isStudent, 'entry-workspace': isLogin }">
    <a class="skip-link" href="#main-content" @click.prevent="focusMain">跳到主要内容</a>
    <header class="workspace-header">
      <router-link :to="homePath" class="brand"><span class="brand-mark" aria-hidden="true">课</span><span>课程知识库<small>以课内资料为据</small></span></router-link>
      <div v-if="isStudent && !isLogin" class="surface-switch" role="group" aria-label="学习工作态">
        <button :aria-pressed="surface === 'study'" @click="selectSurface('study')"><span>学</span> 浏览与阅读</button>
        <button :aria-pressed="surface === 'ask'" @click="selectSurface('ask')"><span>问</span> 提问与核对</button>
      </div>
      <div v-if="session.user && !isLogin" class="account-menu"><span class="role-pill">{{ roleLabel }}</span><span class="username">{{ session.user.username }}</span><button class="quiet-button" @click="onLogout">退出登录</button></div>
      <span v-else class="entry-header-note">课内资料 · 有据可查</span>
    </header>
    <div class="workspace-body" :class="{ 'without-rail': isLogin || !session.user }">
      <aside v-if="session.user && !isLogin" class="workspace-rail">
        <div class="rail-heading">{{ isAdmin ? '管理工作台' : isStudent ? '学习空间' : '教学工作台' }}</div>
        <nav class="primary-nav" aria-label="主导航">
          <template v-if="isAdmin">
            <router-link to="/admin/users"><span aria-hidden="true">01</span>账号管理</router-link>
            <router-link to="/admin/courses"><span aria-hidden="true">02</span>课程与授权</router-link>
            <router-link to="/admin/maintenance"><span aria-hidden="true">03</span>提问日志</router-link>
            <router-link to="/admin/system"><span aria-hidden="true">04</span>系统状态</router-link>
          </template>
          <router-link v-else to="/courses"><span aria-hidden="true">▤</span>我的课程</router-link>
        </nav>
        <nav v-if="pageAllowed && currentCourse" class="course-navigation" aria-label="当前课程导航">
          <div class="rail-heading">当前课程</div><strong class="course-context-title">{{ currentCourse.title }}</strong>
          <router-link :to="'/courses/' + currentCourse.id" exact-active-class="is-current">提问 <span aria-hidden="true">↗</span></router-link>
          <router-link :to="'/courses/' + currentCourse.id + '/documents'" exact-active-class="is-current">课程资料</router-link>
          <router-link v-if="currentCourse.capabilities.can_manage_members" :to="'/courses/' + currentCourse.id + '/members'" exact-active-class="is-current">本课学生</router-link>
          <router-link v-if="currentCourse.capabilities.can_view_insights" :to="'/courses/' + currentCourse.id + '/insights'" exact-active-class="is-current">问答反馈</router-link>
        </nav>
        <div class="planned-navigation"><div class="rail-heading">后续功能</div><button disabled>{{ isAdmin ? '学期 / 班级' : '课程调查' }}<small>即将推出</small></button></div>
        <div class="rail-footnote"><span class="rail-rule" aria-hidden="true"></span><p>{{ isAdmin ? '账号与课内授权分别管理。' : '从资料出发，回到原文核对。' }}</p></div>
      </aside>
      <main id="main-content" tabindex="-1" class="workspace-main">
        <div v-if="!isLogin && session.user" class="context-bar"><span>{{ isAdmin ? '管理' : isStudent ? '我的课程' : '教学' }}<template v-if="currentCourse"> / {{ currentCourse.title }}</template></span><span>{{ isStudent ? (surface === 'study' ? '浏览 · 阅读' : '提问 · 核对') : '课程知识库' }}</span></div>
        <div v-if="recoveryError" class="recovery-box"><el-alert :title="recoveryError.message" type="warning" :closable="false"/><el-button v-if="recoveryError.status !== 401" :loading="recovering" @click="retryConnection">重试连接</el-button><el-button v-else @click="router.push({path:'/login',query:{next:route.fullPath}})">重新登录</el-button></div>
        <router-view v-if="pageAllowed" :key="route.fullPath + ':' + courseAccess.revision"/>
        <div v-else-if="!recoveryError" class="study-empty"><h2>访问权限已变化</h2><p>请重新选择课程或登录。</p><router-link :to="session.user ? homePath : '/login'">返回</router-link></div>
      </main>
    </div>
    <footer class="workspace-footer"><span>课程知识库</span><span>回答供学习参考，请结合原资料核对。</span></footer>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watchEffect } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { logout, refreshMe, session } from "./session";
import { studentSurface } from "./theme";
import { clearCourseAccess, courseAccess, refreshCourseAccess } from "./courseAccess";

const router = useRouter();
const route = useRoute();
const isStudent = computed(() => session.user?.role === "student");
const isLogin = computed(() => route.path === "/login");
const { surface, select: selectSurface } = studentSurface;

const isAdmin = computed(() => session.user?.role === "admin");
watchEffect(() => {
  document.documentElement.dataset.theme = isStudent.value && !isLogin.value ? surface.value : "study";
  document.documentElement.dataset.surface = isLogin.value ? "entry" : isStudent.value ? "student" : isAdmin.value ? "balance" : "ce";
});
const homePath = computed(() => (session.user?.role === "admin" ? "/admin/users" : "/courses"));
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

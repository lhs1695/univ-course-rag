<template>
  <div class="study-app">
    <a class="study-skip" href="#study-main">跳到主要内容</a>
    <aside class="study-sidebar">
      <router-link to="/courses" class="study-brand"><StudyIcon /><span>课程知识库<small>让每一次理解，有据可循</small></span></router-link>
      <span class="study-nav-label">学习空间</span>
      <nav aria-label="学生导航">
        <router-link to="/courses" :class="{ active: !course }" :aria-current="!course ? 'page' : undefined"><StudyIcon name="grid" />我的课程</router-link>
        <template v-if="course">
          <div class="study-course-context">{{ course.title }}</div>
          <router-link :to="`/courses/${course.id}`" exact-active-class="active" :aria-current="!isDocuments ? 'page' : undefined"><StudyIcon name="ask" />课程问答</router-link>
          <router-link :to="`/courses/${course.id}/documents`" exact-active-class="active" :aria-current="isDocuments ? 'page' : undefined"><StudyIcon name="file" />课程资料</router-link>
        </template>
      </nav>
      <div class="study-side-note"><StudyIcon name="book" /><p>答案是理解的起点，<br>原文是核对的依据。</p></div>
      <div class="study-profile"><span class="study-avatar">{{ session.user.username.slice(0, 1).toUpperCase() }}</span><span>{{ session.user.username }}<small>学生账号</small></span><button class="study-icon-button" aria-label="退出登录" :disabled="leaving" @click="leave"><StudyIcon name="exit" /></button></div>
    </aside>
    <div class="study-workspace">
      <header class="study-topline"><span>我的课程 <template v-if="course"> / <strong>{{ course.title }}</strong></template></span><span class="study-top-note">基于课内资料 · 回答可溯源</span></header>
      <main id="study-main" ref="main" tabindex="-1">
        <div v-if="error" class="study-error" role="alert">{{ error.message }}<button class="study-button" :disabled="recovering" @click="recover">{{ recovering ? '连接中…' : '重试连接' }}</button></div>
        <StudentCourses v-if="!route.params.courseId" />
        <StudentDocuments v-else-if="course && isDocuments" :key="`docs-${course.id}`" />
        <StudentAsk v-else-if="course" :key="`ask-${course.id}`" />
        <div v-else class="study-empty"><h1>课程访问权限已变化</h1><router-link to="/courses">返回我的课程</router-link></div>
      </main>
    </div>
  </div>
</template>
<script setup>
import { computed, nextTick, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { logout, refreshMe, session } from '../session';
import { courseAccess, refreshCourseAccess } from '../courseAccess';
import StudyIcon from './StudyIcon.vue';
import StudentCourses from '../views/StudentCourses.vue';
import StudentAsk from '../views/StudentAsk.vue';
import StudentDocuments from '../views/StudentDocuments.vue';
import '../student.css';
const route = useRoute(), router = useRouter();
const course = computed(() => courseAccess.course?.id === String(route.params.courseId) ? courseAccess.course : null);
const isDocuments = computed(() => route.path.endsWith('/documents'));
const error = computed(() => session.error || courseAccess.error);
const main = ref(null), leaving = ref(false), recovering = ref(false);
watch(() => route.fullPath, async () => { await nextTick(); main.value?.focus({ preventScroll: true }); });
async function leave() { leaving.value = true; try { await logout(); await router.push('/login'); } catch (e) { ElMessage.error(e.message); } finally { leaving.value = false; } }
async function recover() { recovering.value = true; try { if (await refreshMe() && route.params.courseId) await refreshCourseAccess(String(route.params.courseId)); if (session.retryPath) await router.replace(session.retryPath); } catch (e) { ElMessage.error(e.message); } finally { recovering.value = false; } }
</script>

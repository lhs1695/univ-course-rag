<template>
  <div class="student-ui study-shell">
    <aside class="study-sidebar" :class="{ 'is-open': menuOpen }">
      <router-link to="/courses" class="study-brand" @click="menuOpen = false"><StudyIcon name="book"/><span>课程知识库<small>你的课内学习空间</small></span></router-link>
      <div class="workspace-label">个人空间 <span>学生</span></div>
      <router-link class="side-link" :class="{ selected: !course }" to="/courses" @click="menuOpen = false"><StudyIcon name="grid"/>我的课程</router-link>
      <template v-if="course">
        <p class="side-caption">正在学习</p>
        <div class="side-course"><span :style="{ background: identity.tint }">{{ identity.symbol }}</span><strong>{{ course.title }}</strong></div>
        <router-link class="side-link" :to="`/courses/${course.id}`" exact-active-class="selected" @click="menuOpen = false"><StudyIcon name="chat"/>课程问答</router-link>
        <router-link class="side-link" :to="`/courses/${course.id}/documents`" exact-active-class="selected" @click="menuOpen = false"><StudyIcon name="file"/>课程资料</router-link>
      </template>
      <div class="side-bottom"><div class="side-note"><StudyIcon name="book"/><p>理解，始于追问。<small>每一个引用，都有原文可循。</small></p></div><div class="student-account"><span class="account-avatar">{{ session.user.username.slice(0, 1).toUpperCase() }}</span><span>{{ session.user.username }}<small>学生账号</small></span><button class="quiet-button" @click="$emit('logout')">退出</button></div></div>
    </aside>
    <div v-if="menuOpen" class="nav-scrim" @click="menuOpen = false"></div>
    <div class="study-content">
      <header class="study-topbar"><button class="mobile-menu quiet-button" aria-label="打开导航" :aria-expanded="menuOpen" @click="menuOpen = !menuOpen"><StudyIcon name="menu"/></button><router-link to="/courses">我的课程</router-link><template v-if="course"><span class="breadcrumb-divider">/</span><span>{{ course.title }}</span><span class="breadcrumb-divider">/</span><span>{{ route.path.endsWith('/documents') ? '课程资料' : '课程问答' }}</span></template><span class="topbar-note">有依据，可核对</span></header>
      <main id="main-content" tabindex="-1" class="study-main"><slot/></main>
    </div>
  </div>
</template>
<script setup>
import { computed, ref } from 'vue';
import { useRoute } from 'vue-router';
import { session } from '../session';
import { courseAccess } from '../courseAccess';
import { courseIdentity } from '../courseIdentity';
import StudyIcon from './StudyIcon.vue';
defineEmits(['logout']);
const route = useRoute();
const menuOpen = ref(false);
const course = computed(() => courseAccess.course?.id === route.params.courseId ? courseAccess.course : null);
const identity = computed(() => courseIdentity(course.value?.title));
</script>

<template>
  <nav class="study-rail" aria-label="学生主导航">
    <router-link class="study-mark" to="/courses" aria-label="课程知识库首页" title="课程知识库"><svg viewBox="0 0 28 28" aria-hidden="true"><path d="M4 5h8l2 3 2-3h8v17h-8l-2 2-2-2H4zM14 8v16M7 9h4M7 13h4M17 9h4M17 13h4" /></svg></router-link>
    <router-link to="/courses" class="rail-link" :class="{ active: !course }" title="我的课程" aria-label="我的课程"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h6v7H4zM14 4h6v7h-6zM4 15h6v5H4zM14 15h6v5h-6z" /></svg><span>课程</span></router-link>
    <router-link v-if="course" :to="`/courses/${course.id}`" class="rail-link" exact-active-class="active" title="课程问答" aria-label="课程问答"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h16v12H9l-5 4zM8 8h8M8 12h5" /></svg><span>问答</span></router-link>
    <router-link v-if="course" :to="`/courses/${course.id}/documents`" class="rail-link" exact-active-class="active" title="课程资料" aria-label="课程资料"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h8l4 4v14H6zM14 3v5h4M9 12h6M9 16h6" /></svg><span>资料</span></router-link>
    <button class="rail-link rail-exit" type="button" title="退出登录" aria-label="退出登录" @click="$emit('logout')"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 4H4v16h6M9 12h11M16 8l4 4-4 4" /></svg><span>退出</span></button>
  </nav>
</template>
<script setup>
defineProps({ course: { type: Object, default: null } });
defineEmits(['logout']);
</script>

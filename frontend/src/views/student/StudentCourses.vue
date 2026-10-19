<template>
  <div class="study-home">
    <header class="study-top"><router-link class="study-wordmark" to="/courses">课程知识库</router-link><span>{{ session.user.username }} · 学生</span></header>
    <main class="study-library">
      <header class="study-title"><div><h1>我的课程</h1><p>带着问题读课件，带着依据理解知识。</p></div><span class="study-total">{{ courses.length }} 门已加入</span></header>
      <el-alert v-if="deniedNotice" :title="deniedNotice" type="warning" @close="deniedNotice = ''" />
      <div class="library-tools"><label class="study-search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/></svg><input v-model="search" type="search" aria-label="查找课程" placeholder="查找课程" /></label><button class="quiet-button" :disabled="loading" @click="loadCourses">{{ loading ? '加载中…' : '刷新' }}</button></div>
      <p v-if="failure" class="study-error" role="alert">{{ failure }} <button class="quiet-button" @click="loadCourses">重试</button></p>
      <p v-else-if="loading" class="study-state" role="status">正在打开你的课程书架…</p>
      <section v-else-if="filtered.length" class="course-shelf" aria-label="已加入课程">
        <article v-for="row in filtered" :key="row.id" class="shelf-course">
          <div class="course-spine" aria-hidden="true"><span>{{ row.title.slice(0, 1) }}</span><small>课程资料</small></div>
          <div class="shelf-content"><span class="study-meta">已加入课程</span><h2><router-link :to="`/courses/${row.id}`">{{ row.title }}</router-link></h2><p>从课内资料出发，让每个回答有据可查。</p><div class="shelf-actions"><router-link class="ink-button" :to="`/courses/${row.id}`">开始提问 <span aria-hidden="true">↗</span></router-link><router-link class="text-button" :to="`/courses/${row.id}/documents`">查看资料</router-link></div></div>
        </article>
      </section>
      <div v-else class="study-state"><h2>{{ search ? '没有找到这门课程' : '你的课程书架还是空的' }}</h2><p>{{ search ? '换一个课程名称试试。' : '联系任课教师或管理员加入课程，即可查看资料和提问。' }}</p><button v-if="search" class="quiet-button" @click="search = ''">查看全部课程</button></div>
      <footer class="library-foot"><span>学习从提问开始，理解回到原文。</span><span>课内问答 · 逐页核对</span></footer>
    </main>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue';
import { api } from '../../api';
import { session } from '../../session';
const courses = ref([]), loading = ref(false), failure = ref(''), search = ref('');
const deniedNotice = ref(sessionStorage.getItem('accessDeniedFlash') || '');
sessionStorage.removeItem('accessDeniedFlash');
const filtered = computed(() => courses.value.filter(row => row.title.toLowerCase().includes(search.value.trim().toLowerCase())));
async function loadCourses() {
  if (loading.value) return;
  loading.value = true;
  try { courses.value = await api('/courses'); failure.value = ''; }
  catch (error) { failure.value = error.message; }
  finally { loading.value = false; }
}
onMounted(loadCourses);
</script>

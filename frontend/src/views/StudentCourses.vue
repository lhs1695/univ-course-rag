<template>
  <div class="study-content">
    <div class="study-page-heading"><div><p class="study-kicker">你的学习书架</p><h1>今天，想理解什么？</h1><p>走进一门课程，从资料出发，让疑问得到有依据的回应。</p></div><span v-if="!loading && !failure" class="study-count">{{ courses.length }} 门课程</span></div>
    <div class="study-toolbar"><h2>我的课程</h2><label class="study-search"><StudyIcon name="search" /><input v-model="search" aria-label="查找课程" placeholder="查找课程" type="search" /></label></div>
    <p v-if="notice" class="study-error" role="alert">{{ notice }}</p>
    <div v-if="loading" class="study-empty" role="status">正在整理你的课程书架…<el-skeleton :rows="4" animated /></div>
    <div v-else-if="failure" class="study-error" role="alert">{{ failure }}<button class="study-button" @click="load">重新加载</button></div>
    <div v-else-if="!courses.length" class="study-empty"><StudyIcon name="book" /><h2>书架等待第一门课程</h2><p>请联系本课教师或管理员，将你的账号加入课程。</p></div>
    <p v-else-if="!filtered.length" class="study-empty">没有找到“{{ search }}”相关课程。试试其他名称。</p>
    <ul v-else class="study-course-grid">
      <li v-for="(item, index) in filtered" :key="item.id" class="study-course-card">
        <div class="study-book-spine"><span>{{ String(index + 1).padStart(2, '0') }}</span><StudyIcon name="book" /></div>
        <div class="study-course-details"><span class="study-kicker">已加入的课程</span><h2>{{ item.title }}</h2><p>带着问题阅读，沿着引用核对。</p><div class="study-card-actions"><router-link :to="`/courses/${item.id}`" class="study-button study-primary">开始学习<StudyIcon name="arrow" /></router-link><router-link :to="`/courses/${item.id}/documents`" class="study-text-link">查看资料</router-link></div></div>
      </li>
    </ul>
    <div class="study-how"><span>一个问题，一条有据可循的学习路径。</span><ol><li><b>01</b> 提出问题</li><li><b>02</b> 阅读回答与依据</li><li><b>03</b> 回到原文核对</li></ol></div>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue';
import { api } from '../api';
import StudyIcon from '../components/StudyIcon.vue';
const courses = ref([]), loading = ref(true), failure = ref(''), search = ref('');
const notice = sessionStorage.getItem('accessDeniedFlash');
sessionStorage.removeItem('accessDeniedFlash');
const filtered = computed(() => courses.value.filter(c => c.title.toLowerCase().includes(search.value.toLowerCase())));
async function load() { loading.value = true; failure.value = ''; try { courses.value = await api('/courses'); } catch (e) { failure.value = e.message; } finally { loading.value = false; } }
onMounted(load);
</script>

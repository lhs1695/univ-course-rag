<template>
  <div class="study-page">
    <header class="study-page-title"><div><h1>我的课程</h1><p>把疑问带进来，把理解带回课堂。</p></div><span class="muted" v-if="!loading">已加入 {{ courses.length }} 门课程</span></header>
    <section class="study-intro"><div><span class="intro-book"><StudyIcon name="book"/></span><h2>每一次追问，<br>都有迹可循。</h2><p>在课程资料里寻找答案，<br>从引用回到原文，形成自己的理解。</p></div><div class="reading-diagram" aria-label="提问、回答与依据、原文页"><div class="diagram-question"><StudyIcon name="chat"/>一个具体的问题</div><span class="diagram-line"></span><div class="diagram-answer"><span>课内回答</span><i></i><i></i><i></i><b>依据 [1]</b></div><div class="diagram-source"><StudyIcon name="file"/><span>课程资料<small>回到引用页</small></span><StudyIcon name="external"/></div></div></section>
    <div class="section-toolbar"><h2>课程书架</h2><label class="study-search"><StudyIcon name="search"/><input v-model="search" placeholder="查找课程" aria-label="查找课程"/></label></div>
    <el-alert v-if="deniedNotice" :title="deniedNotice" type="warning" @close="deniedNotice = ''"/>
    <div v-if="failure" class="study-empty" role="alert"><p>{{ failure }}</p><button class="secondary-button" @click="loadCourses">重新加载</button></div>
    <el-skeleton v-else-if="loading" :rows="4"/>
    <div v-else-if="!courses.length" class="study-empty"><h3>你的课程书架还是空的</h3><p>联系本课教师或管理员加入课程，即可查看资料并提问。</p></div>
    <div v-else-if="!filtered.length" class="study-empty"><p>没有找到“{{ search }}”相关的课程。</p><button class="quiet-button" @click="search = ''">查看全部课程</button></div>
    <ul v-else class="bookshelf"><li v-for="course in filtered" :key="course.id" class="course-book"><router-link :to="`/courses/${course.id}`" class="book-cover" :style="{ background: courseIdentity(course.title).tint }"><span class="cover-label">课程笔记</span><strong>{{ courseIdentity(course.title).symbol }}</strong><StudyIcon name="book"/></router-link><div class="book-details"><h3><router-link :to="`/courses/${course.id}`">{{ course.title }}</router-link></h3><p>{{ courseIdentity(course.title).description }}</p><div class="book-actions"><router-link class="book-ask" :to="`/courses/${course.id}`">开始提问 <StudyIcon name="arrow"/></router-link><router-link :to="`/courses/${course.id}/documents`">浏览资料</router-link></div></div></li></ul>
    <footer class="study-footnote">回答用于辅助理解，请结合课程资料核对。</footer>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from 'vue';
import { api } from '../api';
import { courseIdentity } from '../courseIdentity';
import StudyIcon from '../components/StudyIcon.vue';
const courses = ref([]), loading = ref(true), failure = ref(''), search = ref('');
const deniedNotice = ref(sessionStorage.getItem('accessDeniedFlash') || '');
sessionStorage.removeItem('accessDeniedFlash');
const filtered = computed(() => courses.value.filter(row => row.title.toLowerCase().includes(search.value.trim().toLowerCase())));
async function loadCourses() { loading.value = true; try { courses.value = await api('/courses'); failure.value = ''; } catch (error) { failure.value = error.message; } finally { loading.value = false; } }
onMounted(loadCourses);
</script>

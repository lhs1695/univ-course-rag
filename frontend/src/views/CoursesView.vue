<template>
  <div class="course-shelf">
    <header class="shelf-heading"><div><h1>今天，想读懂什么？</h1><p>选择一门课程，把疑问交给资料。</p></div><span v-if="loaded && !failure" class="shelf-count">{{ courses.length }} 门已加入的课程</span></header>
    <el-alert v-if="deniedNotice" :title="deniedNotice" type="warning" closable @close="deniedNotice = ''"/>
    <div v-if="failure" class="study-empty" role="alert"><h2>课程暂时没有加载出来</h2><p>{{ failure }}</p><el-button :loading="loading" @click="loadCourses">重新加载</el-button></div>
    <div v-else-if="loading" class="study-empty" role="status"><p>正在整理你的课程书架…</p><el-skeleton :rows="4" animated/></div>
    <div v-else-if="!courses.length" class="study-empty"><h2>你的书架还空着</h2><p>联系本课教师或管理员加入课程，然后就可以阅读资料、开始提问。</p><router-link v-if="session.user?.role === 'admin'" to="/admin/courses">课程与授权</router-link></div>
    <ul v-else class="shelf-list">
      <li v-for="(row,index) in courses" :key="row.id" class="shelf-course" :class="`book-tone-${index % 4}`">
        <div class="book-spine" aria-hidden="true"><span>{{ row.title }}</span></div>
        <div class="book-cover"><span class="book-caption">课程知识库</span><h2>{{ row.title }}</h2><span class="book-bottom">带着问题，回到原文。</span><span class="cover-orbit" aria-hidden="true"></span></div>
        <div class="book-details"><span class="course-membership">{{ row.membership_role === 'teacher' ? '教师课程' : '已加入课程' }}</span><h3>{{ row.title }}</h3><p>从课堂上的疑问出发，<br>让每一个回答都有资料可循。</p><div class="book-actions"><el-button type="primary" @click="openAsk(row)">开始提问</el-button><button class="text-button" @click="openDocs(row)">浏览资料 <span aria-hidden="true">↗</span></button></div><div class="book-management" v-if="row.capabilities.can_manage_members || row.capabilities.can_view_insights"><button v-if="row.capabilities.can_manage_members" class="quiet-button" @click="openMembers(row)">本课学生</button><button v-if="row.capabilities.can_view_insights" class="quiet-button" @click="openInsights(row)">问答反馈</button></div></div>
      </li>
    </ul>
    <div class="shelf-footnote"><span class="footnote-symbol" aria-hidden="true">↳</span><p>答案是阅读的起点。<br><span>在回答下方点击引用，即可回到原资料的对应页。</span></p></div>
  </div>
</template>
<script setup>
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { session } from "../session";
import { api } from "../api";

const router = useRouter();
const courses = ref([]);
const loading = ref(true);
const loaded = ref(false);
const failure = ref("");
const deniedNotice = ref("");
const flash = sessionStorage.getItem("accessDeniedFlash");
if (flash) {
  deniedNotice.value = flash;
  sessionStorage.removeItem("accessDeniedFlash");
}

async function loadCourses() {
  if (loading.value && loaded.value) return;
  loading.value = true;
  try {
    courses.value = await api("/courses");
    failure.value = "";
  } catch (error) {
    failure.value = error.message;
    ElMessage.error(error.message);
  } finally {
    loading.value = false;
    loaded.value = true;
  }
}
onMounted(loadCourses);

function openAsk(row) {
  router.push(`/courses/${row.id}`);
}

function openDocs(row) {
  router.push(`/courses/${row.id}/documents`);
}

function openInsights(row) {
  router.push(`/courses/${row.id}/insights`);
}

function openMembers(row) {
  router.push(`/courses/${row.id}/members`);
}
</script>

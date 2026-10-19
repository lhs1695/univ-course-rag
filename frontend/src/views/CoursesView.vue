<template>
  <div class="course-shelf" :class="{ 'staff-shelf': !isStudent }">
    <header class="shelf-heading">
      <div>
        <h1>{{ isStudent ? "今天，想读懂什么？" : "备课，从本课资料开始" }}</h1>
        <p>{{ isStudent ? "选择一门课程，把疑问交给资料。" : "检查资料依据，管理本课学生，核对问答反馈。" }}</p>
      </div>
      <span v-if="loaded && !failure" class="shelf-count">{{ courses.length }} 门已加入的课程</span>
    </header>
    <el-alert v-if="deniedNotice" :title="deniedNotice" type="warning" closable @close="deniedNotice = ''"/>
    <div v-if="failure" class="study-empty" role="alert"><h2>课程暂时没有加载出来</h2><p>{{ failure }}</p><el-button :loading="loading" @click="loadCourses">重新加载</el-button></div>
    <div v-else-if="loading" class="study-empty" role="status"><p>正在整理你的课程书架…</p><el-skeleton :rows="4" animated/></div>
    <div v-else-if="!courses.length" class="study-empty">
      <h2>{{ isStudent ? "你的书架还空着" : "尚未加入课程" }}</h2>
      <p>{{ isStudent ? "联系本课教师或管理员加入课程，然后就可以阅读资料、开始提问。" : "请联系管理员授予课内教师身份，然后即可上传资料、管理学生与查看反馈。" }}</p>
    </div>
    <ul v-else class="shelf-list">
      <li v-for="(row,index) in courses" :key="row.id" class="shelf-course" :class="`book-tone-${index % 4}`">
        <div class="book-spine" aria-hidden="true"><span>{{ row.title }}</span></div>
        <div class="book-cover">
          <span class="book-caption">课程知识库</span>
          <h2>{{ row.title }}</h2>
          <span class="book-bottom">{{ isStudent ? "带着问题，回到原文。" : "核对资料，再问一句。" }}</span>
          <span class="cover-orbit" aria-hidden="true"></span>
        </div>
        <div class="book-details">
          <span class="course-membership">{{ row.membership_role === 'teacher' ? '教师课程' : '已加入课程' }}</span>
          <h3>{{ row.title }}</h3>
          <p v-if="isStudent">从课堂上的疑问出发，<br>让每一个回答都有资料可循。</p>
          <p v-else>备课时核对资料，关注待核对问句，补充教学依据。</p>
          <div class="book-actions">
            <template v-if="isStudent">
              <el-button type="primary" @click="openAsk(row)">开始提问</el-button>
              <button class="text-button" @click="openDocs(row)">浏览资料 <span aria-hidden="true">↗</span></button>
            </template>
            <template v-else>
              <el-button type="primary" @click="openDocs(row)">进入备课</el-button>
              <button class="text-button" @click="openAsk(row)">试问本课 <span aria-hidden="true">↗</span></button>
            </template>
          </div>
          <div class="book-management" v-if="row.capabilities.can_manage_members || row.capabilities.can_view_insights">
            <button v-if="row.capabilities.can_manage_members" class="management-button" @click="openMembers(row)">本课学生</button>
            <button v-if="row.capabilities.can_view_insights" class="management-button" @click="openInsights(row)">问答反馈</button>
          </div>
        </div>
      </li>
    </ul>
    <div v-if="isStudent" class="shelf-footnote"><span class="footnote-symbol" aria-hidden="true">↳</span><p>答案是阅读的起点。<br><span>在回答下方点击引用，即可回到原资料的对应页。</span></p></div>
    <div v-else-if="courses.length" class="shelf-footnote"><span class="footnote-symbol" aria-hidden="true">↳</span><p>备课入口默认打开资料。<br><span>需要时可从「试问本课」核对问答依据是否足够。</span></p></div>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { session } from "../session";
import { api } from "../api";

const router = useRouter();
const isStudent = computed(() => session.user?.role === "student");
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
    if (error.status !== 401) ElMessage.error(error.message);
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

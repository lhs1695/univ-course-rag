<template>
  <div class="page courses-page">
    <header class="page-heading"><p class="eyebrow">课程空间</p><h1>我的课程</h1><p class="page-description">选择一门已加入的课程，查看资料或开始提问。管理入口按你的课内权限显示。</p></header>
    <el-alert v-if="deniedNotice" :title="deniedNotice" type="warning" show-icon :closable="true" @close="deniedNotice = ''" style="margin-bottom: 16px;" />
    <template v-if="failure">
      <el-alert :title="failure" type="error" :closable="false" show-icon />
      <el-button :loading="loading" @click="loadCourses">重新加载课程</el-button>
    </template>
    <div v-else-if="loading" aria-busy="true"><p role="status" class="page-description">正在加载你的课程…</p><el-skeleton :rows="4" animated /></div>
    <el-empty v-else-if="loaded && courses.length === 0" description="还没有加入任何课程"><p v-if="session.user?.role === 'admin'" class="page-description">管理员默认不加入课程，请到「课程与授权」把自己加入某课后，这里才会出现。</p><p v-else class="page-description">请联系本课教师或管理员加入已有课程。</p><router-link v-if="session.user?.role === 'admin'" to="/admin/courses">前往课程与授权</router-link></el-empty>
    <ul v-else class="course-grid">
      <li v-for="row in courses" :key="row.id" class="course-card">
        <span class="role-pill">课内{{ row.membership_role === 'teacher' ? '教师' : '学生' }}</span>
        <h2>{{ row.title }}</h2>
        <p>{{ row.capabilities.can_manage_documents ? '维护本课资料与成员，查看问答反馈。' : '阅读课内资料，在回答中逐条核对来源。' }}</p>
        <div class="course-card-primary"><el-button type="primary" @click="openAsk(row)">进入问答</el-button><el-button plain @click="openDocs(row)">课程资料</el-button></div>
        <div v-if="row.capabilities.can_manage_members || row.capabilities.can_view_insights" class="course-card-secondary">
          <el-button v-if="row.capabilities.can_manage_members" type="primary" text @click="openMembers(row)">本课学生</el-button>
          <el-button v-if="row.capabilities.can_view_insights" type="primary" text @click="openInsights(row)">问答反馈</el-button>
        </div>
      </li>
    </ul>
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

<style scoped>
.courses-page { padding-top: 2px; }
.course-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr)); gap: 20px; padding: 0; margin: 0; list-style: none; align-items: stretch; }
.course-card { display: flex; flex-direction: column; align-items: flex-start; height: 100%; padding: 22px 24px; min-width: 0; background: #fff; border: 1px solid #dfe7e2; border-radius: 12px; box-shadow: 0 8px 24px rgba(37, 72, 63, .035); }
.course-card h2 { font-size: 21px; font-weight: 700; line-height: 1.35; margin: 14px 0 8px; overflow-wrap: anywhere; }
.course-card p { font-size: 13px; color: #65736e; line-height: 1.7; margin: 0 0 22px; }
.course-card-primary { margin-top: auto; display: flex; flex-wrap: wrap; gap: 8px; }
.course-card-primary .el-button + .el-button { margin-left: 0; }
.course-card-primary .el-button { min-height: 40px; }
.course-card-primary .el-button--primary { min-width: 110px; font-weight: 600; }
.course-card-secondary { width: 100%; padding-top: 14px; margin-top: 18px; border-top: 1px solid #e7ede9; }
.course-card-secondary .el-button { padding-left: 0; padding-right: 0; color: #66756f; font-size: 13px; font-weight: 400; }
@media (max-width: 700px) { .course-grid { grid-template-columns: minmax(0, 1fr); gap: 16px; } .course-card { padding: 20px; } }
</style>

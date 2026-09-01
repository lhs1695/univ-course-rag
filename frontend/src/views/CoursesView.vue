<template>
  <div class="page">
    <h2>我的课程</h2>
    <el-alert
      v-if="loaded && courses.length === 0"
      title="还没有加入任何课程"
      type="info"
      :closable="false"
    />
    <el-table v-else :data="courses" v-loading="loading" empty-text="加载中">
      <el-table-column prop="title" label="课程" />
      <el-table-column label="" :width="isTeacher ? 220 : 100">
        <template #default="{ row }">
          <el-button v-if="isTeacher" type="primary" link @click="openDocs(row)">资料</el-button>
          <el-button type="primary" link @click="openAsk(row)">提问</el-button>
          <el-button v-if="isTeacher" type="primary" link @click="openInsights(row)">学情</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { session } from "../session";

const router = useRouter();
const courses = ref([]);
const loading = ref(true);
const loaded = ref(false);
const isTeacher = computed(() => session.user?.role === "teacher");

onMounted(async () => {
  try {
    courses.value = await api("/courses");
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    loading.value = false;
    loaded.value = true;
  }
});

function openAsk(row) {
  router.push(`/courses/${row.id}`);
}

function openDocs(row) {
  router.push(`/courses/${row.id}/documents`);
}

function openInsights(row) {
  router.push(`/courses/${row.id}/insights`);
}
</script>

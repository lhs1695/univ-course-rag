<template>
  <div class="page">
    <el-page-header @back="router.push('/courses')">
      <template #content>学情</template>
    </el-page-header>
    <p class="hint">
      只统计本课学生在最近 {{ retentionDays || "当前配置" }} 天留存窗口内的提问（规范化后计数）。不展示提问者，也不对学习情况作结论；到期记录即使尚未清理，也不会进入这里。
    </p>

    <h3>高频问句</h3>
    <el-table :data="frequent" v-loading="loading" empty-text="暂无命中问句">
      <el-table-column prop="query" label="问句" min-width="280" />
      <el-table-column prop="count" label="次数" width="100" />
    </el-table>

    <h3 class="second">未命中 / 拒答</h3>
    <el-table :data="noEvidence" v-loading="loading" empty-text="暂无未命中问句">
      <el-table-column prop="query" label="问句" min-width="280" />
      <el-table-column prop="count" label="次数" width="100" />
      <el-table-column label="最近时间" width="200">
        <template #default="{ row }">
          {{ formatTime(row.last_asked_at) }}
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";

const route = useRoute();
const router = useRouter();
const courseId = computed(() => String(route.params.courseId));
const loading = ref(true);
const frequent = ref([]);
const noEvidence = ref([]);
const retentionDays = ref(null);

function formatTime(value) {
  if (!value) {
    return "—";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return date.toLocaleString();
}

onMounted(async () => {
  try {
    const data = await api(`/courses/${courseId.value}/insights`);
    retentionDays.value = data.retention_days || null;
    frequent.value = data.frequent || [];
    noEvidence.value = data.no_evidence || [];
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.hint {
  margin: 16px 0 8px;
  color: #606266;
  font-size: 13px;
  line-height: 1.6;
}

h3 {
  margin: 16px 0 8px;
  font-size: 16px;
  font-weight: 600;
}

.second {
  margin-top: 28px;
}
</style>

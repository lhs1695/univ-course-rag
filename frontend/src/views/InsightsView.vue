<template>
  <div class="page">
    <header class="page-heading"><p class="eyebrow">课程反馈</p><h1>问答反馈</h1><p class="page-description">查看已有问答聚合，用于核对资料需求；不作为学生掌握程度判断。</p></header>
    <p class="hint">
      按提问时的课内学生角色统计，留存上限 {{ retentionDays || "当前配置" }} 天。每次提交（含显式重试）分别计数，不代表人数；以已保存事件为准，记录不覆盖所有失败请求。不展示提问者，也不判断掌握程度或回答正确性。
    </p>
    <el-button :loading="loading" @click="loadInsights">刷新统计</el-button>
    <el-alert v-if="failure" :title="failure" type="error" :closable="false" show-icon />
    <template v-else>
    <div v-if="summary" class="hint" aria-label="统计口径与样本量">
      <p>统计时间：{{ formatTime(windowStart) }}（含）至 {{ formatTime(windowEnd) }}（不含），以服务端记录的提问时间为准。</p>
      <p>学生提交 {{ summary.student_attempts }} 次：有引用回答 {{ summary.cited_answer }}、依据不足 {{ summary.no_evidence }}、失败 {{ summary.failure }}、结果未知 {{ summary.unknown_outcome }}。</p>
      <p>依据不足占比：{{ summary.no_evidence_rate == null ? '暂无可计算样本' : `${(summary.no_evidence_rate * 100).toFixed(1)}%` }}；分母为有引用回答＋依据不足（{{ summary.knowledge_attempts }} 次），失败和未知不进入该分母。</p>
      <p>窗口内共记录 {{ summary.recorded_attempts }} 次；另有非学生角色 {{ summary.non_student_attempts }} 次、角色未知 {{ summary.unknown_role_attempts }} 次，均不进入学生列表。旧记录不按当前成员角色补写。</p>
    </div>

    <h3>有引用回答的问句（按次数）</h3>
    <el-table :data="frequent" v-loading="loading" empty-text="本窗口暂无已登记的有引用回答">
      <el-table-column prop="query" label="问句" min-width="280" />
      <el-table-column prop="count" label="次数" width="100" />
    </el-table>

    <h3 class="second">依据不足的问句（待核对）</h3>
    <p class="hint">有候选但未形成可引用回答也属于依据不足；服务或索引失败不进入本表。同词规范化计数不等于同义分组。</p>
    <el-table :data="noEvidence" v-loading="loading" empty-text="本窗口暂无已登记的依据不足">
      <el-table-column prop="query" label="问句" min-width="280" />
      <el-table-column prop="count" label="次数" width="100" />
      <el-table-column label="最近时间" width="200">
        <template #default="{ row }">
          {{ formatTime(row.last_asked_at) }}
        </template>
      </el-table-column>
    </el-table>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";

const route = useRoute();
const courseId = computed(() => String(route.params.courseId));
const loading = ref(false);
const frequent = ref([]);
const noEvidence = ref([]);
const retentionDays = ref(null);
const summary = ref(null);
const windowStart = ref(null);
const windowEnd = ref(null);
const failure = ref("");

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

async function loadInsights() {
  if (loading.value) return;
  loading.value = true;
  failure.value = "";
  try {
    const data = await api(`/courses/${courseId.value}/insights`);
    retentionDays.value = data.retention_days || null;
    frequent.value = data.frequent || [];
    noEvidence.value = data.no_evidence || [];
    summary.value = data.summary;
    windowStart.value = data.window_start;
    windowEnd.value = data.window_end;
  } catch (error) {
    failure.value = error.message;
    ElMessage.error(error.message);
  } finally {
    loading.value = false;
  }
}
onMounted(loadInsights);
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

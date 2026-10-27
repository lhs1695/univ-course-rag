<template>
  <div class="page">
    <header class="page-heading">
      <h1>问答反馈</h1>
      <p class="page-lead">本课学生提问统计；不推断学生能力；有引用不等于答对。</p>
    </header>

    <el-alert
      v-if="summary?.sample_limited"
      type="warning"
      :closable="false"
      show-icon
      title="样本有限（学生提问次数 &lt; 30），统计仅供参考，不做强结论。"
      class="insights-section"
    />
    <section v-if="summary" class="key-counts" aria-label="汇总">
      <div><span>学生提问次数</span><strong>{{ summary.student_attempts ?? 0 }}</strong></div>
      <div><span>不同问句</span><strong>{{ summary.distinct_student_questions ?? 0 }}</strong></div>
      <div><span>有引用回答</span><strong>{{ summary.cited_answer ?? 0 }}</strong><small v-if="summary.cited_answer_rate != null"> / {{ pct(summary.cited_answer_rate) }}</small></div>
      <div><span>依据不足</span><strong>{{ summary.no_evidence ?? 0 }}</strong><small v-if="summary.no_evidence_rate != null"> / {{ pct(summary.no_evidence_rate) }}</small></div>
      <div><span>系统失败</span><strong>{{ summary.failure ?? 0 }}</strong><small v-if="summary.failure_rate != null"> / {{ pct(summary.failure_rate) }}</small></div>
    </section>
    <p v-else-if="!loading && !failure" class="hint">还没有可展示的问答统计。</p>

    <div class="toolbar">
      <el-button :loading="loading" @click="loadInsights">刷新</el-button>
    </div>

    <el-alert v-if="failure" :title="failure" type="error" :closable="false" show-icon />
    <section v-else class="panel-card insights-section">
      <h3 class="section-title">高频问句</h3>
      <el-table :data="questionRows" v-loading="loading" empty-text="暂无有引用或依据不足的问句">
        <el-table-column label="问句" min-width="280">
          <template #default="{ row }"><span class="query-clamp">{{ row.query }}</span></template>
        </el-table-column>
        <el-table-column prop="count" label="次数" width="100" />
        <el-table-column prop="outcome" label="结果" width="120" />
        <el-table-column label="最近时间" min-width="180">
          <template #default="{ row }">{{ formatTime(row.last_asked_at) }}</template>
        </el-table-column>
      </el-table>
    </section>
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
const summary = ref(null);
const failure = ref("");

const questionRows = computed(() => [
  ...frequent.value.map(row => ({ ...row, outcome: "有引用" })),
  ...noEvidence.value.map(row => ({ ...row, outcome: "依据不足" })),
].sort((a, b) => b.count - a.count || String(a.query).localeCompare(String(b.query), "zh")));

function pct(rate) {
  return `${Math.round(Number(rate) * 1000) / 10}%`;
}

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

async function loadInsights() {
  if (loading.value) return;
  loading.value = true;
  failure.value = "";
  try {
    const data = await api(`/courses/${courseId.value}/insights`);
    frequent.value = data.frequent || [];
    noEvidence.value = data.no_evidence || [];
    summary.value = data.summary;
  } catch (error) {
    failure.value = error.message;
    summary.value = null;
    frequent.value = [];
    noEvidence.value = [];
    if (error.status !== 401) ElMessage.error(error.message);
  } finally {
    loading.value = false;
  }
}

onMounted(loadInsights);
</script>

<style scoped>
.key-counts { display: flex; flex-wrap: wrap; gap: 16px; margin: 18px 0; }
.key-counts > div { flex: 1; min-width: 130px; padding: 16px 20px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-panel); }
.key-counts strong { display: block; font-size: 28px; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--text-strong); margin-top: 6px; }
.hint { margin: 12px 0 8px; color: var(--text-muted); font-size: 12.5px; line-height: 1.75; }
.toolbar { margin: 8px 0 16px; }
.page-lead { margin: 8px 0 0; max-width: 52rem; color: var(--text-muted); font-size: 14px; line-height: 1.7; }
.insights-section { margin: 20px 0; }
.section-title { margin: 0 0 12px; font-size: 16px; font-weight: 600; }
.query-clamp { display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-clamp: 2; overflow-wrap: anywhere; line-height: 1.5; }
</style>
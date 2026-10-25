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
    <section v-if="summary" class="key-counts" aria-label="本窗口汇总">
      <div><span>学生提问次数</span><strong>{{ summary.student_attempts ?? 0 }}</strong></div>
      <div><span>不同问句</span><strong>{{ summary.distinct_student_questions ?? 0 }}</strong></div>
      <div><span>有引用回答</span><strong>{{ summary.cited_answer ?? 0 }}</strong><small v-if="summary.cited_answer_rate != null"> / {{ pct(summary.cited_answer_rate) }}</small></div>
      <div><span>依据不足</span><strong>{{ summary.no_evidence ?? 0 }}</strong><small v-if="summary.no_evidence_rate != null"> / {{ pct(summary.no_evidence_rate) }}</small></div>
      <div><span>系统失败</span><strong>{{ summary.failure ?? 0 }}</strong><small v-if="summary.failure_rate != null"> / {{ pct(summary.failure_rate) }}</small></div>
    </section>
    <p v-if="summary" class="hint">比率以学生提问次数为分母；合同 {{ metricContract || "metrics-v1" }}；留存 {{ retentionDays }} 天；窗口 {{ formatTime(windowStart) }}（含）至 {{ formatTime(windowEnd) }}（不含）。</p>
    <p v-else-if="!loading && !failure" class="hint">本窗口还没有可展示的问答统计。</p>

    <fieldset class="window-filter">
      <legend>统计时间</legend>
      <el-date-picker
        v-model="draftRange"
        type="datetimerange"
        range-separator="至"
        start-placeholder="开始时刻（含）"
        end-placeholder="结束时刻（不含）"
        :shortcuts="rangeShortcuts"
        :default-time="defaultTimes"
        aria-label="统计时间范围，开始包含、结束不包含"
      />
      <el-button :disabled="loading" @click="applyWindow">按此时间统计</el-button>
      <el-button :disabled="loading" @click="resetWindow">使用留存窗口</el-button>
      <el-button :loading="loading" @click="loadInsights">刷新</el-button>
    </fieldset>

    <el-alert v-if="failure" :title="failure" type="error" :closable="false" show-icon />
    <section v-else class="panel-card insights-section">
      <h3 class="section-title">高频问句</h3>
      <el-table :data="questionRows" v-loading="loading" empty-text="本窗口暂无有引用或依据不足的问句">
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
const metricContract = ref("");
const retentionDays = ref(0);
const summary = ref(null);
const windowStart = ref(null);
const windowEnd = ref(null);
const failure = ref("");
const draftRange = ref(null);
const appliedQuery = ref("");
const defaultTimes = [new Date(2000, 0, 1, 0, 0, 0), new Date(2000, 0, 1, 23, 59, 59)];
const rangeShortcuts = [
  { text: "最近 7 天", value: () => [hoursAgo(24 * 7), new Date()] },
  { text: "最近 30 天", value: () => [hoursAgo(24 * 30), new Date()] },
];

const questionRows = computed(() => [
  ...frequent.value.map(row => ({ ...row, outcome: "有引用" })),
  ...noEvidence.value.map(row => ({ ...row, outcome: "依据不足" })),
].sort((a, b) => b.count - a.count || String(a.query).localeCompare(String(b.query), "zh"));

function hoursAgo(hours) {
  return new Date(Date.now() - hours * 60 * 60 * 1000);
}

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
    const data = await api(`/courses/${courseId.value}/insights${appliedQuery.value}`);
    frequent.value = data.frequent || [];
    noEvidence.value = data.no_evidence || [];
    metricContract.value = data.metric_contract || "metrics-v1";
    retentionDays.value = data.retention_days || 0;
    summary.value = data.summary;
    windowStart.value = data.window_start;
    windowEnd.value = data.window_end;
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

function applyWindow() {
  if (loading.value) return;
  const range = draftRange.value;
  if (!Array.isArray(range) || !range[0] || !range[1]) {
    ElMessage.warning("请同时选择开始和结束时间。");
    return;
  }
  if (range[0].getTime() >= range[1].getTime()) {
    ElMessage.warning("开始时刻需要早于结束时刻。统计包含开始、不包含结束。");
    return;
  }
  const params = new URLSearchParams({
    start_at: range[0].toISOString(),
    end_at: range[1].toISOString(),
  });
  appliedQuery.value = `?${params.toString()}`;
  loadInsights();
}

function resetWindow() {
  if (loading.value) return;
  draftRange.value = null;
  appliedQuery.value = "";
  loadInsights();
}

onMounted(loadInsights);
</script>

<style scoped>
.key-counts { display: flex; flex-wrap: wrap; gap: 16px; margin: 18px 0; }
.key-counts > div { flex: 1; min-width: 130px; padding: 16px 20px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-panel); }
.key-counts strong { display: block; font-size: 28px; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--text-strong); margin-top: 6px; }
.hint { margin: 12px 0 8px; color: var(--text-muted); font-size: 12.5px; line-height: 1.75; }
.window-filter {
  margin: 22px 0 26px;
  padding: 18px 20px;
  border: 1px solid var(--line);
  border-radius: var(--radius-panel);
  background: var(--surface);
}
.window-filter legend { padding: 0 7px; color: var(--text-strong); font-size: 15px; font-weight: 600; }
.window-filter .el-button { margin: 8px 8px 0 0; }
.page-lead { margin: 8px 0 0; max-width: 52rem; color: var(--text-muted); font-size: 14px; line-height: 1.7; }
.insights-section { margin: 20px 0; }
.section-title { margin: 0 0 12px; font-size: 16px; font-weight: 600; }
.query-clamp { display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-clamp: 2; overflow-wrap: anywhere; line-height: 1.5; }
</style>

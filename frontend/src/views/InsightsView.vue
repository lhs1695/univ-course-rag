<template>
  <div class="page">
    <header class="page-heading">
      <h1>问答反馈</h1>
      <p class="page-description">查看已保存问答的计数、趋势和待核对问句。</p>
    </header>

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
      <el-button @click="applyWindow">按此时间统计</el-button>
      <el-button @click="resetWindow">使用留存窗口</el-button>
      <el-button :loading="loading" @click="loadInsights">刷新统计</el-button>
    </fieldset>

    <el-alert v-if="failure" :title="failure" type="error" :closable="false" show-icon />
    <template v-else>
      <section class="panel-card insights-section">
        <h3 class="section-title">依据不足的问句（待核对）</h3>
        <el-table :data="noEvidence" v-loading="loading" empty-text="这段时间暂无已登记的依据不足问句">
          <el-table-column label="问句" width="420">
            <template #default="{ row }"><span class="query-clamp">{{ row.query }}</span></template>
          </el-table-column>
          <el-table-column prop="count" label="次数" width="100" />
          <el-table-column label="最近时间" width="200">
            <template #default="{ row }">{{ formatTime(row.last_asked_at) }}</template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel-card insights-section" aria-live="polite"><h3 class="section-title">备课建议</h3><p>{{ teachingSuggestion }}</p></section>

      <section class="panel-card insights-section">
        <h3 class="section-title">学生提交趋势（按本地日期）</h3>
        <p class="hint">按上海时间的自然日统计；下表只列有学生提交的日期。</p>
        <InsightTrend :points="trend" />
        <el-table :data="activeDays" empty-text="本窗口没有学生提交">
          <el-table-column label="日期" width="140">
            <template #default="{ row }">{{ localDayLabel(row.bucket_start) }}</template>
          </el-table-column>
          <el-table-column prop="cited_answer" label="有引用回答" width="120" />
          <el-table-column prop="no_evidence" label="依据不足" width="110" />
          <el-table-column prop="failure" label="失败" width="90" />
          <el-table-column prop="unknown_outcome" label="结果未知" width="110" />
        </el-table>
      </section>

            <details class="panel-card insights-section">
        <summary>统计口径说明</summary>

          <p class="hint">有候选但未形成可引用回答也属于依据不足；服务或索引失败不进入待核对表。同词规范化计数不等于同义分组，也不能据此认定教学缺口或学生未掌握。</p>
          <p class="hint">
            按提问时的课内学生角色统计，留存上限 {{ retentionDays || "当前配置" }} 天。每次提交（含显式重试）分别计数，不代表人数；以已保存事件为准，记录不覆盖所有失败请求。不展示提问者，也不判断掌握程度或回答正确性。旧记录保持未知，不按当前成员角色补写。
          </p>
          <div v-if="summary" class="hint summary-surface" aria-label="统计口径与样本量">
            <p>统计时间：{{ formatTime(windowStart) }}（含）至 {{ formatTime(windowEnd) }}（不含），以服务端记录的提问时间为准。</p>
            <p>学生提交 {{ summary.student_attempts }} 次：有引用回答 {{ summary.cited_answer }}、依据不足 {{ summary.no_evidence }}、失败 {{ summary.failure }}、结果未知 {{ summary.unknown_outcome }}。</p>
            <p>依据不足占比：{{ summary.no_evidence_rate == null ? "暂无可计算样本" : `${(summary.no_evidence_rate * 100).toFixed(1)}%` }}；分母为有引用回答＋依据不足（{{ summary.knowledge_attempts }} 次），失败和未知不进入该分母，也不能称为教学缺口率。</p>
            <p>窗口内共记录 {{ summary.recorded_attempts }} 次；另有非学生角色 {{ summary.non_student_attempts }} 次、角色未知 {{ summary.unknown_role_attempts }} 次，均不进入学生列表或趋势。</p>
          </div>
          <p>统计窗口与当前留存窗口取交集，不读取到期或未来记录；刷新统计不会发送问句。</p>
          <p>趋势按本地日期（Asia/Shanghai）分桶；无事件的日期为 0，下表只列有提交的日期。候选组未验证，不代表已确认的同义问句。最低成对相似度是组内任意两条问句相似度的最小值，不是同义概率。</p>
        
      </details>

      <details class="panel-card insights-section">
        <summary>有引用回答的问句（按次数）</summary>
        <el-table :data="frequent" v-loading="loading" empty-text="这段时间暂无已登记的有引用回答">
          <el-table-column label="问句" width="420">
            <template #default="{ row }"><span class="query-clamp">{{ row.query }}</span></template>
          </el-table-column>
          <el-table-column prop="count" label="次数" width="100" />
        </el-table>
      </details>

      <details class="panel-card insights-section">
        <summary>相似问句分组（仅供参考，未验证）</summary>
        <details class="hint"><summary>候选分组说明</summary>
        <p>
        把相近的问法放在一起，方便核对；分组默认关闭，相似度阈值尚未校准。只有填写阈值并勾选确认后，才会把当前已应用统计窗口内的学生问句原文发送到已配置的嵌入服务，可能产生费用。请求发出后，离开页面也不能保证调用停止。返回结果只是达到该阈值的候选；单例表示未与其他问句成组。候选组不是已验证同义、教学缺口或学生掌握度。
        </p>
        </details>
        <div class="group-controls">
        <label>
          相似度阈值
          <el-input v-model="thresholdText" placeholder="必填，大于 0 且不超过 1" aria-label="未校准的相似度阈值" />
        </label>
        <el-checkbox v-model="confirmExternal">我确认本次把当前窗口内的学生问句原文发送到已配置的嵌入服务（可能产生费用）</el-checkbox>
        <el-button type="primary" :disabled="!canGroup" :loading="grouping" @click="loadGroups">生成候选组</el-button>
        </div>
        <el-alert v-if="groupingFailure" :title="groupingFailure" type="warning" :closable="false" show-icon />
        <div v-if="groups" class="hint summary-surface" aria-label="候选分组样本量">
        <p>分组窗口：{{ formatTime(groups.window_start) }}（含）至 {{ formatTime(groups.window_end) }}（不含）。阈值 {{ groups.min_similarity }}，尚未校准。合同 {{ groups.grouping_contract }}。</p>
        <p>{{ groups.embedding_called ? "本次调用了嵌入服务。" : "本次没有调用嵌入服务。" }} 嵌入身份：{{ groups.embedding_model || "未返回" }} / {{ groups.embedding_identity || "未返回" }}。身份只说明调用配置，不表示效果已验收。</p>
        <p>可分组学生事件 {{ groups.eligible_attempts }} 次，不同问句 {{ groups.distinct_questions }} 条；已进入多问句候选的问句 {{ groups.grouped_questions }} 条。单例问句 {{ groups.singleton_questions }} 条、单例事件 {{ groups.singleton_attempts }} 次。另有 {{ groups.excluded_attempts }} 次学生事件因失败、结果未知或空问句被排除，不进入候选组。</p>
        </div>
        <h4>多问句候选</h4>
        <p class="hint">代表问句是组内真实问句，不是生成的知识点名称。最低成对相似度不是同义概率。</p>
        <el-table :data="candidates" empty-text="本次没有多问句候选">
        <el-table-column type="expand">
          <template #default="{ row }">
            <el-table :data="row.members" empty-text="没有成员">
              <el-table-column label="问句" width="420">
                <template #default="{ row: member }"><span class="query-clamp">{{ member.query }}</span></template>
              </el-table-column>
              <el-table-column prop="count" label="次数" width="80" />
              <el-table-column prop="cited_answer" label="有引用回答" width="120" />
              <el-table-column prop="no_evidence" label="依据不足" width="100" />
              <el-table-column label="与代表的相似度" width="150">
                <template #default="{ row: member }">{{ formatSimilarity(member.similarity_to_representative) }}</template>
              </el-table-column>
              <el-table-column label="最近时间" width="180">
                <template #default="{ row: member }">{{ formatTime(member.last_asked_at) }}</template>
              </el-table-column>
            </el-table>
          </template>
        </el-table-column>
        <el-table-column label="代表问句" width="420">
          <template #default="{ row }"><span class="query-clamp">{{ row.representative }}</span></template>
        </el-table-column>
        <el-table-column prop="count" label="次数" width="80" />
        <el-table-column prop="distinct_questions" label="不同问句" width="110" />
        <el-table-column label="最低成对相似度" width="150">
          <template #default="{ row }">{{ formatSimilarity(row.min_pair_similarity) }}</template>
        </el-table-column>
        </el-table>
        <h4>未成组的单例</h4>
        <p class="hint">同一问句重复多次仍是单例，不表示已经与其他问法合并。</p>
        <el-table :data="singletons" empty-text="本次没有单例">
        <el-table-column label="问句" width="420">
          <template #default="{ row }"><span class="query-clamp">{{ row.representative }}</span></template>
        </el-table-column>
        <el-table-column prop="count" label="次数" width="80" />
        <el-table-column label="成员结果" min-width="180">
          <template #default="{ row }">{{ memberOutcome(row) }}</template>
        </el-table-column>
        </el-table>
      </details>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { localDayLabel } from "../insightTrend";
import InsightTrend from "../components/InsightTrend.vue";

const route = useRoute();
const courseId = computed(() => String(route.params.courseId));
const loading = ref(false);
const frequent = ref([]);
const noEvidence = ref([]);
const trend = ref([]);
const retentionDays = ref(null);
const summary = ref(null);
const windowStart = ref(null);
const windowEnd = ref(null);
const failure = ref("");
const draftRange = ref(null);
const appliedQuery = ref("");
const grouping = ref(false);
const groupingFailure = ref("");
const groups = ref(null);
const thresholdText = ref("");
const confirmExternal = ref(false);
const defaultTimes = [new Date(2000, 0, 1, 0, 0, 0), new Date(2000, 0, 1, 23, 59, 59)];
const rangeShortcuts = [
  { text: "最近 7 天", value: () => [hoursAgo(24 * 7), new Date()] },
  { text: "最近 30 天", value: () => [hoursAgo(24 * 30), new Date()] },
];

const teachingSuggestion = computed(() => {
  if (loading.value) return "正在读取本窗口问答记录…";
  if (!summary.value || !summary.value.knowledge_attempts) return "暂无可用于建议的问答数据；可先检查本课资料。";
  if (summary.value.no_evidence > 0) return `有 ${summary.value.no_evidence} 次提问依据不足，建议先对照上方问句核对原文，再决定是否补充资料。`;
  if (summary.value.cited_answer > 0) return "当前已登记问答均有引用，可抽查引用原页与回答是否一致；有引用不代表回答正确。";
  return "暂无可用于建议的问答数据。";
});

const threshold = computed(() => {
  const value = Number(thresholdText.value);
  return thresholdText.value.trim() && Number.isFinite(value) && value > 0 && value <= 1 ? value : null;
});
const canGroup = computed(() => threshold.value != null && confirmExternal.value && !grouping.value && !loading.value);
const activeDays = computed(() => trend.value.filter((row) => row.cited_answer || row.no_evidence || row.failure || row.unknown_outcome));
const candidates = computed(() => (groups.value?.groups || []).filter((row) => row.kind === "candidate"));
const singletons = computed(() => (groups.value?.groups || []).filter((row) => row.kind === "singleton"));

function hoursAgo(hours) {
  return new Date(Date.now() - hours * 60 * 60 * 1000);
}

function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function formatSimilarity(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number.toFixed(3) : "—";
}

function memberOutcome(row) {
  const member = row.members?.[0];
  if (!member) return "—";
  return `有引用回答 ${member.cited_answer}，依据不足 ${member.no_evidence}`;
}

function clearGroups() {
  groups.value = null;
  groupingFailure.value = "";
  confirmExternal.value = false;
}

async function loadInsights() {
  if (loading.value) return;
  loading.value = true;
  failure.value = "";
  clearGroups();
  try {
    const data = await api(`/courses/${courseId.value}/insights${appliedQuery.value}`);
    retentionDays.value = data.retention_days || null;
    frequent.value = data.frequent || [];
    noEvidence.value = data.no_evidence || [];
    trend.value = data.trend || [];
    summary.value = data.summary;
    windowStart.value = data.window_start;
    windowEnd.value = data.window_end;
  } catch (error) {
    failure.value = error.message;
    summary.value = null;
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

async function loadGroups() {
  if (!canGroup.value) return;
  grouping.value = true;
  groupingFailure.value = "";
  groups.value = null;
  const body = {
    min_similarity: threshold.value,
    confirm_external_processing: true,
  };
  const applied = new URLSearchParams(appliedQuery.value.replace(/^\?/, ""));
  if (applied.get("start_at")) body.start_at = applied.get("start_at");
  if (applied.get("end_at")) body.end_at = applied.get("end_at");
  try {
    groups.value = await api(`/courses/${courseId.value}/insights/groups`, { method: "POST", json: body });
  } catch (error) {
    groupingFailure.value = error.message;
    if (error.status !== 401) ElMessage.error(error.message);
  } finally {
    grouping.value = false;
  }
}

onMounted(loadInsights);
</script>

<style scoped>
.key-counts { display: flex; flex-wrap: wrap; gap: 16px; margin: 18px 0; }
.key-counts > div { flex: 1; min-width: 130px; padding: 16px 20px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-panel); }
.key-counts strong { display: block; font-size: 28px; font-weight: 600; font-variant-numeric: tabular-nums; color: var(--text-strong); margin-top: 6px; }
details > summary { cursor: pointer; }
.hint { margin: 12px 0 8px; color: var(--text-muted); font-size: 12.5px; line-height: 1.75; }
h3, h4 { margin: 28px 0 8px; font-size: 16px; font-weight: 600; }
h4 { font-size: 15px; }
.second { margin-top: 30px; }
.window-filter, .group-controls {
  margin: 22px 0 26px;
  padding: 18px 20px;
  border: 1px solid var(--line);
  border-radius: var(--radius-panel);
  background: var(--surface);
}
.window-filter legend { padding: 0 7px; color: var(--text-strong); font-size: 15px; font-weight: 600; }
.window-filter .el-button, .group-controls .el-button { margin: 8px 8px 0 0; }
.group-controls label { display: block; max-width: 360px; color: var(--text-strong); font-size: 14px; }
.group-controls .el-checkbox { display: flex; margin-top: 12px; white-space: normal; height: auto; }
.summary-surface { margin: 24px 0 26px; padding: 16px 18px; background: var(--surface-subtle); border-left: 3px solid var(--el-color-primary-light-5); }
.summary-surface p { margin: 4px 0; }
.insights-section { margin: 20px 0; }
.section-title { margin: 0 0 12px; font-size: 16px; font-weight: 600; }
.query-clamp { display: -webkit-box; overflow: hidden; -webkit-box-orient: vertical; -webkit-line-clamp: 2; line-clamp: 2; overflow-wrap: anywhere; line-height: 1.5; }
</style>

<template>
  <div class="page investigation-page">
    <header class="page-heading"><p class="eyebrow">教学 / 课程调查</p><h1>从问题回到依据</h1><p class="page-lead">回看本课提问，区分事实、候选解释与未知。报告供教师核查。</p></header>
    <section class="panel-card investigation-section" aria-labelledby="request-heading">
      <h2 id="request-heading" class="section-title">发起调查</h2>
      <form @submit.prevent="create">
        <div class="investigation-fields">
          <label>开始时间<input v-model="start" type="datetime-local" required /></label>
          <label>结束时间<input v-model="end" type="datetime-local" required /></label>
          <label>调查焦点<select v-model="focus"><option value="all">综合回看</option><option value="repeated_questions">重复提问</option><option value="no_evidence">依据不足</option><option value="system_failures">系统失败</option></select></label>
        </div>
        <p class="hint">单次最多 30 天，默认最近 7 天。Fake/Replay 仅用于核验流程，不代表真实模型质量。</p>
        <label class="investigation-confirm"><input v-model="confirmed" type="checkbox" />我确认本次调查可将本课学生问句与资料证据发送给配置的外部 LLM、Embedding 或语义分组服务；已了解数据处理范围。当前运行仅使用 Fake/Replay。</label>
        <el-button native-type="submit" type="primary" :loading="busy === 'create'" :disabled="!!busy">创建调查任务</el-button>
      </form>
    </section>
    <el-alert v-if="failure" :title="failure" type="error" :closable="false" show-icon />
    <section v-if="task" class="panel-card investigation-section" aria-labelledby="task-heading">
      <div class="investigation-heading"><h2 id="task-heading" class="section-title">调查记录</h2><span role="status">{{ statusLabel(task.status) }} · 第 {{ task.attempt }} 次尝试</span></div>
      <p class="hint">任务 {{ task.task_id }}</p>
      <p>累计：{{ task.budget_used.model_calls }} / {{ task.budget_limits.max_model_calls }} 模型动作 · {{ task.budget_used.tool_calls }} / {{ task.budget_limits.max_tool_calls }} 工具调用 · {{ task.budget_used.runtime_seconds.toFixed(2) }} 秒</p>
      <p v-if="task.error_code" class="hint">{{ errorLabel(task.error_code) }}</p>
      <div class="toolbar">
        <template v-if="task.status === 'queued'"><label>运行方式<select v-model="mode"><option value="fake">Fake · 日志观察</option><option value="replay">Replay · 当前资料字面核对</option></select></label><el-button type="primary" :loading="busy === 'run'" :disabled="!!busy" @click="act('run')">运行 Fake/Replay</el-button></template>
        <el-button v-if="['queued','running','interrupted'].includes(task.status)" :loading="busy === 'cancel'" :disabled="busy && busy !== 'run'" @click="act('cancel')">取消调查</el-button>
        <el-button v-if="task.status === 'interrupted'" :disabled="!!busy" @click="act('resume')">显式恢复</el-button>
        <el-button v-if="['failed','cancelled','budget_exceeded'].includes(task.status)" :disabled="!!busy || !remainingBudget" @click="act('retry')">显式重试</el-button>
        <el-button :disabled="busy && busy !== 'run'" @click="refresh">刷新状态</el-button>
      </div>
      <p v-if="task.status === 'interrupted'" class="hint">执行已中断。系统不会自动恢复；确认授权和来源后才能开始新尝试。</p>
      <p v-if="task.status === 'cancel_requested'" class="hint">已请求取消，当前调用在安全边界停止，不再启动下一调用。</p>
      <details><summary>步骤与安全事件摘要（{{ task.events.length }}）</summary><ol class="investigation-events"><li v-for="event in task.events" :key="event.sequence">
        <span>{{ event.sequence }} · 尝试 {{ event.attempt }}<template v-if="event.step_no != null"> · 步骤 {{ event.step_no }}</template> · {{ event.event_type }}</span>
        <span v-if="event.tool_name"> · {{ event.tool_name }}</span><span v-if="event.duration_ms != null"> · {{ event.duration_ms }} ms</span>
        <time :datetime="event.created_at"> · {{ eventTime(event.created_at) }}</time>
        <p>{{ event.safe_summary }} <small v-if="event.error_code" :title="errorLabel(event.error_code)">{{ event.error_code }}</small></p>
      </li></ol></details>
    </section>
    <article v-if="reportData?.report" class="panel-card investigation-section" aria-labelledby="report-heading">
      <p class="eyebrow">待核查报告 / Fake · Replay</p><h2 id="report-heading">调查报告</h2>
      <p>本次样本 {{ reportData.sample_count }} 条；日志与当前资料不能还原历史回答，也不能据此评价教学质量。</p>
      <p>{{ reportData.report.summary }}</p>
      <section v-for="section in reportSections" :key="section.title" class="investigation-report-part"><h3>{{ section.title }}</h3><p v-if="!section.items.length" class="hint">暂无可核查内容。</p><ul v-else><li v-for="(item, index) in section.items" :key="index">{{ item.description || item.explanation || item.reason || item }}<template v-for="id in item.evidence_chunk_ids || []" :key="id"> <a :href="`#evidence-${id}`">查看依据</a></template></li></ul></section>
      <section class="investigation-report-part"><h3>支持证据 · 回到原文</h3><p v-if="!reportData.evidence_sources.length" class="hint">本次没有 PDF 依据。日志观察不能替代课件证据。</p>
        <ol><li v-for="source in reportData.evidence_sources" :id="`evidence-${source.chunk_id}`" :key="source.chunk_id" class="investigation-evidence">
          <template v-if="source.available && source.content_url"><p>{{ claimFor(source.chunk_id) }}</p><span>Document {{ source.document_id }} · {{ citationPageLabel(source.page) }}</span> <a :href="citationUrl(source)" target="_blank" rel="noopener">{{ citationOpenLabel(source.page) }} ↗</a></template>
          <span v-else>来源不可用，相关正文已隐藏。</span>
        </li></ol>
        <p v-if="reportData.sources.some(source => !source.available)" class="hint">部分问句来源不可用，依赖这些来源的结论已隐藏。</p>
      </section>
    </article>
    <p v-else-if="task" class="hint">{{ task.status === 'succeeded' ? '暂无可展示报告。' : '任务完成后在此查看报告与依据。' }}</p>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { investigationApi } from '../api.js';
import { citationPageLabel, citationOpenLabel, citationUrl } from '../citationDisplay.js';

const route = useRoute(), router = useRouter();
const courseId = computed(() => String(route.params.courseId));
const localTime = date => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
const start = ref(localTime(new Date(Date.now() - 7 * 86400000))), end = ref(localTime(new Date()));
const focus = ref('all'), confirmed = ref(false), mode = ref('fake');
const task = ref(null), reportData = ref(null), failure = ref(''), busy = ref('');
let generation = 0, timer, creationKey = '';
const statusLabel = state => ({ queued: '待运行', running: '运行中', cancel_requested: '等待取消生效', cancelled: '已取消', interrupted: '已中断', succeeded: '已完成', failed: '失败', budget_exceeded: '预算终止' }[state] || state);
const errorLabel = code => ({ agent_lease_expired: '执行 lease 已过期，旧执行权已撤销。', agent_budget_exhausted: '累计预算耗尽。', investigation_checkpoint_unsafe: '检查点无法安全恢复。', source_unavailable: '来源已不可用，请核对资料与课程授权。' }[code] || `安全错误码：${code}`);
function eventTime(value) {
  const date = new Date(value);
  return !value || Number.isNaN(date.getTime()) ? '时间未知' : date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
}
const remainingBudget = computed(() => task.value && Object.entries({ steps: 'max_steps', model_calls: 'max_model_calls', tool_calls: 'max_tool_calls', runtime_seconds: 'max_runtime_seconds' }).every(([key, limit]) => task.value.budget_used[key] < task.value.budget_limits[limit]));
const reportSections = computed(() => {
  const r = reportData.value?.report;
  return r ? [{ title: '观察事实', items: r.findings }, { title: '候选解释 · 尚未证实', items: r.candidate_causes }, { title: '未知与限制', items: r.unknowns }, { title: '建议人工动作', items: r.suggested_actions }] : [];
});
const claimFor = id => reportData.value?.report?.evidence_refs.find(ref => ref.chunk_id === id)?.claim_supported || '当前资料依据，请打开原文核对。';
function fail(error) {
  failure.value = error.message;
  if ([401, 403, 404].includes(error.status)) { task.value = null; reportData.value = null; }
}
function poll() {
  clearTimeout(timer);
  if (['queued', 'running', 'cancel_requested'].includes(task.value?.status)) timer = setTimeout(refresh, 3000);
}
async function refresh() {
  const id = String(route.query.task || task.value?.task_id || '');
  if (!id) return;
  const current = generation;
  try {
    const [next, report] = await Promise.all([investigationApi.read(courseId.value, id), investigationApi.report(courseId.value, id)]);
    if (current !== generation) return;
    task.value = next; reportData.value = report; failure.value = ''; poll();
  } catch (error) { if (current === generation) { fail(error); clearTimeout(timer); } }
}
async function create() {
  if (busy.value) return;
  failure.value = '';
  busy.value = 'create';
  const current = generation;
  try {
    creationKey ||= crypto.randomUUID();
    const next = await investigationApi.create(courseId.value, { start_at: new Date(start.value).toISOString(), end_at: new Date(end.value).toISOString(), focus: focus.value, confirm_external_processing: confirmed.value, idempotency_key: creationKey });
    if (current !== generation) return;
    task.value = next; reportData.value = null;
    await router.replace({ query: { ...route.query, task: next.task_id } });
    await refresh();
  } catch (error) { if (current === generation) fail(error); }
  finally { if (current === generation) busy.value = ''; }
}
async function act(action) {
  const current = generation;
  if (!task.value) return;
  busy.value = action; failure.value = '';
  try {
    await investigationApi.action(courseId.value, task.value.task_id, action, confirmed.value, mode.value);
    if (current === generation) await refresh();
  } catch (error) { if (current === generation) fail(error); }
  finally { if (current === generation) busy.value = ''; }
}
watch([start, end, focus, confirmed], () => { creationKey = ''; });
watch(() => [courseId.value, route.query.task], () => { generation++; clearTimeout(timer); task.value = null; reportData.value = null; failure.value = ''; busy.value = ''; refresh(); }, { immediate: true });
onBeforeUnmount(() => { generation++; clearTimeout(timer); });
</script>

<style scoped>
.investigation-page { max-width: var(--content-max); }
.investigation-section { margin: var(--section-gap) 0; }
.investigation-fields { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: var(--space-4); }
.investigation-fields label, .toolbar label { display: grid; gap: var(--space-2); }
input:not([type="checkbox"]), select { width: 100%; min-height: 40px; border: 1px solid var(--line-strong); border-radius: var(--radius-sm); background: var(--surface); color: var(--text-body); padding: var(--space-2); font: inherit; box-sizing: border-box; }
.investigation-confirm { display: flex; align-items: flex-start; gap: var(--space-2); margin: var(--space-5) 0; line-height: 1.7; max-width: 840px; }
.investigation-confirm input { margin-top: 7px; accent-color: var(--accent); }
.investigation-heading { display: flex; justify-content: space-between; gap: var(--space-4); flex-wrap: wrap; }
.investigation-report-part { border-top: 1px solid var(--line); margin-top: var(--space-5); padding-top: var(--space-4); line-height: 1.8; }
.investigation-evidence { padding: var(--space-3) 0; overflow-wrap: anywhere; }
.investigation-events { line-height: 1.9; padding-left: var(--space-5); }
.investigation-events span, .investigation-events small, .investigation-events time { color: var(--text-muted); }
.investigation-events p { margin: 0 0 var(--space-2); }
details { margin-top: var(--space-4); }
summary { cursor: pointer; }
@media (max-width: 760px) { .investigation-fields { grid-template-columns: 1fr; } }
</style>

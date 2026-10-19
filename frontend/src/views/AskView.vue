<template>
  <div class="page ask-page" :aria-label="`课程问答：${courseTitle}`">
    <header class="page-heading">
      <h1>{{ session.user?.role === 'student' ? '把这个问题，读明白。' : '课程问答' }}</h1>
      <p class="page-description">在本课资料里寻找线索，再回到原文核对。</p>
    </header>

    <div class="workspace-grid">
      <section class="answer-column" aria-label="提问与回答">
        <div class="composer-panel">
          <div class="panel-heading"><h2 id="question-title">你想弄清楚什么？</h2><span class="subtle">一次聚焦一个疑问</span></div>
          <el-form class="ask-form" aria-labelledby="question-title" @submit.prevent="submitQuestion">
            <el-form-item>
              <el-input v-model="query" id="question-input" aria-label="课程问题" aria-describedby="question-help"
                type="textarea" :rows="3" maxlength="2000" show-word-limit
                placeholder="例如：这两个概念有什么区别？请结合课内资料说明。" />
            </el-form-item>
            <p v-if="query.length >= 2000" class="limit-hint" role="status">最多输入 2000 字，超出部分不会保留</p>
            <div class="composer-footer">
              <p id="question-help" class="subtle">基于本课资料回答 · 草稿与记录刷新后清空</p>
              <el-button type="primary" native-type="submit" :loading="asking" :disabled="asking || !query.trim()">
                {{ asking ? '正在查找依据…' : '查找课内依据' }}<StudyArrow v-if="!asking" />
              </el-button>
            </div>
          </el-form><div v-if="!history.rounds.length" class="question-starters"><span>试着这样问</span><button v-for="starter in starters" :key="starter" type="button" @click="query = starter; focusQuestion()">{{ starter }}</button></div>
        </div>

        <section v-if="history.rounds.length" class="history-panel" aria-labelledby="history-title">
          <div class="panel-heading"><h2 id="history-title">本课问答历史</h2><span class="subtle">选择轮次查看；新问题会携带上一轮上下文</span></div>
          <ol class="history-list">
            <li v-for="(round, index) in history.rounds" :key="round.id">
              <button type="button" :aria-pressed="history.selectedId === round.id" @click="selectRound(round.id)">
                <span class="history-question">{{ index + 1 }}. {{ round.question }}</span>
                <span class="status-label">{{ roundStatus(round) }}</span>
              </button>
            </li>
          </ol>
        </section>

        <section class="response-panel" :aria-busy="selectedRound?.pending || false" aria-labelledby="response-title">
          <div class="panel-heading"><h2 id="response-title">阅读回答</h2><span v-if="result?.answer" class="status-label">已返回回答</span></div>
          <div v-if="selectedRound?.pending" class="response-body">
            <p role="status" class="subtle">正在检索本课资料并组织回答，请稍候。</p>
            <p v-if="waitSeconds >= 3" role="status" class="subtle">仍在检索/组织回答，已等待 {{ waitSeconds }} 秒</p>
            <el-skeleton :rows="4" animated />
          </div>
          <div v-else-if="failure" class="response-body">
            <el-alert :title="failure" type="error" :closable="false" show-icon />
            <el-button :disabled="asking" @click="retryQuestion">重试本次问题</el-button>
          </div>
          <div v-else-if="result?.error_code === 'NO_EVIDENCE'" class="response-body">
            <el-alert title="课内资料依据不足，暂时无法据此回答。" type="warning" :closable="false" show-icon />
            <p class="subtle">这不表示系统故障。可核对课程资料是否齐全，或换一个更具体的问题。</p>
          </div>
          <div v-else-if="notice" class="response-body">
            <el-alert :title="notice.message" :type="notice.type" :closable="false" show-icon />
            <p v-if="notice.type === 'error'" class="subtle">本次回答未能完成，不能据此判断课内资料是否有答案。</p>
          </div>
          <div v-else-if="result?.answer" class="response-body"><p class="answered-question">{{ submittedQuery }}</p>
            <AnswerBody :answer="result.answer" :citations="result.citations" @citation="focusCitation" />
          </div>
          <div v-else class="workspace-empty">
            <h3>一个问题，一次深入。</h3>
            <p>提交问题后，在这里阅读回答。点击文中的引用标记，找到它对应的课件与页码。</p>
          </div>
        </section>
      </section>

      <aside class="evidence-panel" aria-labelledby="evidence-title">
        <div class="panel-heading"><h2 id="evidence-title">回到原文</h2><span class="count-label">{{ result?.citations?.length || 0 }} 条引用</span></div>
        <div class="evidence-scope">
          <p v-if="loadingContext" role="status">正在读取本课资料状态…</p>
          <template v-else-if="contextFailure"><p>{{ contextFailure }}</p><el-button text @click="loadContext">重新加载资料信息</el-button></template>
          <template v-else><p>当前 {{ readyDocumentCount }} 份资料已入库</p><p v-if="readyDocumentCount === 0">暂无成功入库资料，可先到“课程资料”核对。</p></template>
          <p>PDF 链接可定位到引用页。</p>
        </div>
        <ol v-if="result?.citations?.length" class="evidence-list">
          <li v-for="(citation, index) in result.citations" :key="citation.chunk_id" :id="`source-${citation.chunk_id}`" class="evidence-card" tabindex="-1" :aria-label="`引用 ${index + 1}：${filenameOf(citation.document_id)}`">
            <div class="source-heading"><span class="source-number">{{ String(index + 1).padStart(2, '0') }}</span><h3>{{ citationTitle(filenameOf(citation.document_id)) }}</h3></div>
            <small class="subtle source-filename">{{ filenameOf(citation.document_id) }}</small>
            <p v-if="citation.page != null" class="source-page">第 {{ citation.page }} 页</p>
            <blockquote class="citation-snippet">{{ cleanExcerpt(citation.snippet, citation.page) }}</blockquote>
            <el-link :href="citationUrl(citation)" target="_blank" rel="noopener" type="primary" :aria-label="`查看原资料：${filenameOf(citation.document_id)}（新窗口）`">查看原页 <StudyArrow diagonal /></el-link>
          </li>
        </ol>
        <div v-else class="workspace-empty evidence-empty">
          <h3>{{ result || failure ? '本次没有可展示的引用' : '引用会显示在这里' }}</h3>
          <p>有引用的回答会列出资料名称、可用页码与摘录，便于逐条核对。</p>
        </div>
      </aside>
    </div>
  </div>
</template>

<script setup>
import StudyArrow from "../components/StudyArrow.vue";
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { session } from "../session";
import { questionDraft } from "../drafts";
import { askHistory, answerNotice, roundStatus } from "../askHistory.js";
import { cleanExcerpt, citationTitle } from "../citationDisplay.js";
import AnswerBody from "../components/AnswerBody.vue";

const starters = ["请解释一个概念，并给出课件依据。", "这两个概念有什么区别？", "请梳理这一章节的知识联系。"];
function focusQuestion() { document.getElementById("question-input")?.focus(); }
const route = useRoute();
const courseId = computed(() => String(route.params.courseId));
const courseTitle = ref("");
const filenames = ref({});
const loadingContext = ref(true);
const contextFailure = ref("");
const documents = ref([]);
const readyDocumentCount = computed(() => documents.value.filter(doc => doc.job_status === "succeeded").length);
const userId = session.user.id;
const draftRevision = ref(0);
const query = computed({
  get() { draftRevision.value; return questionDraft(userId, courseId.value); },
  set(value) { questionDraft(userId, courseId.value, value); draftRevision.value++; },
});
const revision = ref(0);
const unsubscribe = askHistory.subscribe(() => revision.value++);
const history = computed(() => {
  revision.value;
  const state = askHistory.course(userId, courseId.value);
  return { ...state, rounds: state.rounds.map(round => ({ ...round })) };
});
const asking = computed(() => history.value.rounds.some(round => round.pending));
const selectedRound = computed(() => history.value.rounds.find(round => round.id === history.value.selectedId));
const result = computed(() => selectedRound.value?.result);
const failure = computed(() => selectedRound.value?.failure);
const submittedQuery = computed(() => selectedRound.value?.question);
const notice = computed(() => answerNotice(result.value));
const now = ref(Date.now());
const waitSeconds = computed(() => selectedRound.value?.pending
  ? Math.max(0, Math.floor((now.value - selectedRound.value.startedAt) / 1000)) : 0);
let waitTimer;
watch(() => selectedRound.value?.pending, pending => {
  clearInterval(waitTimer);
  now.value = Date.now();
  if (pending) waitTimer = setInterval(() => { now.value = Date.now(); }, 1000);
}, { immediate: true });
onUnmounted(() => { unsubscribe(); clearInterval(waitTimer); });
function selectRound(id) { askHistory.select(userId, courseId.value, id); }

let contextVersion = 0;
async function loadContext() {
  const version = ++contextVersion;
  const id = courseId.value;
  loadingContext.value = true;
  courseTitle.value = "";
  documents.value = [];
  filenames.value = {};
  contextFailure.value = "";
  try {
    const [course, rows] = await Promise.all([
      api(`/courses/${id}`),
      api(`/courses/${id}/documents`),
    ]);
    if (version !== contextVersion) return;
    courseTitle.value = course.title;
    documents.value = rows;
    const map = {};
    for (const doc of rows) {
      map[doc.id] = doc.filename;
    }
    filenames.value = map;
    contextFailure.value = "";
  } catch {
    if (version !== contextVersion) return;
    contextFailure.value = "暂时无法读取课程资料，请稍后重试。";
    ElMessage.error(contextFailure.value);
  } finally {
    if (version === contextVersion) loadingContext.value = false;
  }
}
watch(courseId, loadContext, { immediate: true });
onUnmounted(() => { contextVersion++; });

function filenameOf(documentId) {
  return filenames.value[documentId] || documentId;
}

function focusCitation(id) {
  if (!result.value?.citations?.some(item => item.chunk_id === id)) return;
  const card = document.getElementById(`source-${id}`);
  card?.focus({ preventScroll: true });
  card?.scrollIntoView({ block: 'nearest' });
}

function citationUrl(citation) {
  const filename = filenameOf(citation.document_id).toLowerCase();
  if (filename.endsWith(".pdf") && citation.page != null) {
    return `${citation.content_url}#page=${citation.page}`;
  }
  return citation.content_url;
}

function submitQuestion() {
  const text = query.value.trim();
  if (text) askQuestion(text);
}

function retryQuestion() {
  if (submittedQuery.value) askQuestion(submittedQuery.value);
}

function askQuestion(text) {
  return askHistory.ask(userId, courseId.value, text, api);
}
</script>

<style scoped>
.ask-page { padding-top: 2px; }
.workspace-grid { display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(300px, .85fr); gap: 28px; align-items: start; }
.answer-column { min-width: 0; display: grid; gap: 24px; }
.composer-panel, .response-panel, .evidence-panel { min-width: 0; background: #fff; border: 1px solid #dfe7e2; border-radius: 12px; overflow: hidden; box-shadow: var(--elev-1); }
.composer-panel { border-top: 4px solid #17675f; box-shadow: var(--elev-1); }
.history-panel { min-width: 0; background: #fff; border: 1px solid #dfe7e2; border-radius: 12px; }
.history-list { list-style: none; margin: 16px; padding: 0; display: grid; gap: 8px; max-height: 300px; overflow-y: auto; }
.history-list button { width: 100%; min-width: 0; display: flex; flex-wrap: wrap; gap: 6px 12px; justify-content: space-between; text-align: left; padding: 10px 12px; background: #f8faf9; border: 1px solid #dfe7e2; border-radius: 6px; color: #41564e; font: inherit; cursor: pointer; }
.history-list button[aria-pressed="true"] { border-color: #17675f; background: #eef6f2; }
.history-question { min-width: 0; overflow-wrap: anywhere; }
.limit-hint { color: #805b20; font-size: 12px; line-height: 1.7; }
.source-heading h3, .citation-snippet, .evidence-card .el-link { overflow-wrap: anywhere; }
.panel-heading { padding: 21px 22px 0; display: flex; flex-wrap: wrap; align-items: baseline; justify-content: space-between; gap: 6px 12px; }
.panel-heading h2 { margin: 0; font-size: 18px; font-weight: 700; }
.subtle, .count-label { font-size: 12px; color: var(--text-muted); line-height: 1.7; }
.status-label { font-size: 12px; color: #4d7165; }
.ask-form { margin: 18px 22px 22px; }
.ask-form :deep(.el-textarea__inner) { min-height: 118px !important; padding: 13px 14px; line-height: 1.7; border-radius: 9px; }
.composer-footer { display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.composer-footer p { margin: 0; max-width: 70%; }
.composer-footer .el-button { min-width: 94px; min-height: 40px; }
.response-panel { min-height: 300px; }
.response-body { padding: 10px 22px 24px; line-height: 1.8; }
.response-body > .subtle { margin: 8px 0 16px; }
.evidence-card:focus { outline: 2px solid #17675f; outline-offset: 3px; }
.workspace-empty { padding: 28px 24px 34px; }
.workspace-empty h3 { font-size: 15px; margin: 8px 0 8px; font-weight: 600; }
.workspace-empty p { margin: 0; max-width: 640px; font-size: 12.5px; color: var(--empty-text); line-height: 1.8; }
.evidence-panel { background: #f8faf9; border-color: #e3e9e6; position: sticky; top: 20px; max-height: calc(100vh - 40px); overflow-y: auto; }
.evidence-panel .panel-heading { padding-top: 19px; }
.evidence-panel .panel-heading h2 { font-size: 16px; font-weight: 650; }
.evidence-scope { margin: 14px 22px 16px; padding-bottom: 13px; border-bottom: 1px solid #e2e9e4; }
.evidence-scope p { margin: 5px 0; font-size: 12px; color: var(--text-muted); line-height: 1.7; }
.evidence-list { padding: 0 20px 22px; margin: 0; list-style: none; display: grid; gap: 12px; }
.evidence-card { padding: 14px 15px; background: rgba(255, 255, 255, .7); border: 0; border-left: 3px solid #b7cec5; border-radius: 0 7px 7px 0; min-width: 0; }
.source-heading { display: flex; align-items: flex-start; gap: 10px; }
.source-heading h3 { margin: 0; font-size: 14px; font-weight: 600; line-height: 1.6; }
.source-number { color: #487167; font-size: 11px; font-weight: 600; padding-top: 2px; flex-shrink: 0; }
.source-filename { display: block; margin: 4px 0 0 30px; overflow-wrap: anywhere; }
.source-page { margin: 7px 0 0 30px; color: var(--text-muted); font-size: 12px; }
.citation-snippet { margin: 12px 0; padding-left: 12px; border-left: 1px solid #ccd9d4; color: #53635d; font-size: 13px; line-height: 1.75; }
.evidence-card .el-link { font-size: 13px; }
.evidence-empty { padding-top: 8px; }
@media (max-width: 900px) { .workspace-grid { grid-template-columns: minmax(0, 1fr); gap: 20px; } .evidence-panel { position: static; max-height: none; overflow-y: visible; } }
@media (max-width: 500px) { .panel-heading { padding: 18px 16px 0; } .ask-form { margin: 16px; } .composer-footer { flex-direction: column; align-items: stretch; } .composer-footer p { max-width: none; } .composer-footer .el-button { width: 100%; } .response-body { padding: 6px 16px 20px; } .evidence-scope { margin: 14px 16px; } .evidence-list { padding: 0 14px 16px; } }
</style>

<template>
  <div class="reading-desk" :aria-label="`课程问答：${courseTitle}`">
    <header class="desk-heading"><h1>{{ history.rounds.length ? '沿着问题，继续阅读。' : '把没想明白的，写下来。' }}</h1><p>在{{ courseTitle || '本课' }}资料中找答案，每一条依据都可以翻回原页。</p></header>
    <section class="question-sheet" aria-labelledby="question-title">
      <div class="question-sheet-label"><h2 id="question-title">我想问</h2><span>{{ readyDocumentCount }} 份可检索资料</span></div>
      <el-form @submit.prevent="submitQuestion">
        <el-input v-model="query" id="question-input" aria-label="课程问题" aria-describedby="question-help" type="textarea" :rows="3" maxlength="2000" show-word-limit placeholder="写下一个概念、一处困惑，或想进一步理解的问题…"/>
        <div class="question-sheet-footer"><span id="question-help">一次聚焦一个疑问，回答更有方向。</span><el-button type="primary" native-type="submit" :loading="asking" :disabled="asking || !query.trim()">{{ asking ? '正在寻找依据' : '查阅并回答' }}<span class="button-glyph" aria-hidden="true">↗</span></el-button></div>
      </el-form>
    </section>
    <p class="desk-memory-note">本页保留本次问答与草稿，刷新后清空。新问题会携带上一轮上下文。</p>
    <details v-if="history.rounds.length" class="reading-history"><summary>本次问答 <span>{{ history.rounds.length }} 轮</span></summary><ol><li v-for="(round,index) in history.rounds" :key="round.id"><button :aria-pressed="history.selectedId === round.id" @click="selectRound(round.id)"><span class="round-index">{{ index + 1 }}</span><span>{{ round.question }}</span><small>{{ roundStatus(round) }}</small></button></li></ol></details>
    <article v-if="selectedRound" class="answer-sheet" :aria-busy="selectedRound.pending" aria-labelledby="response-title">
      <div class="answer-question"><span>你的问题</span><h2>{{ selectedRound.question }}</h2></div>
      <div class="answer-title"><span class="answer-emblem" aria-hidden="true">课</span><h3 id="response-title">课内回答</h3><span v-if="result?.answer" class="answer-reminder">请结合原文核对</span></div>
      <div v-if="selectedRound.pending" class="answer-content" role="status"><p>正在翻阅本课资料，整理与你的问题有关的依据…</p><p v-if="waitSeconds >= 3" class="desk-memory-note">已等待 {{ waitSeconds }} 秒，请保持页面打开。</p><el-skeleton :rows="4" animated/></div>
      <div v-else-if="failure" class="answer-content"><el-alert :title="failure" type="error" :closable="false"/><el-button :disabled="asking" @click="retryQuestion">重试本次问题</el-button></div>
      <div v-else-if="notice" class="answer-content"><el-alert :title="notice.message" :type="notice.type" :closable="false"/><p>{{ notice.type === 'error' ? '本次回答未能完成，请稍后重试。' : '试着补充概念名称、章节或更具体的描述，也可以先浏览课程资料。' }}</p><router-link :to="`/courses/${courseId}/documents`">浏览课程资料</router-link></div>
      <div v-else-if="result?.answer" class="answer-content"><AnswerBody :answer="result.answer" :citations="result.citations || []" @citation="focusCitation"/></div>
      <section v-if="!selectedRound.pending" class="source-section" aria-labelledby="evidence-title"><div class="source-section-heading"><h3 id="evidence-title">回答从哪里来</h3><span>{{ result?.citations?.length || 0 }} 条资料依据</span></div>
        <ol v-if="result?.citations?.length" class="source-list"><li v-for="(citation,index) in result.citations" :key="citation.chunk_id" :id="`source-${citation.chunk_id}`" tabindex="-1" class="source-slip"><div class="source-slip-top"><span class="source-cite-number">[{{ index + 1 }}]</span><h4>{{ citationTitle(filenameOf(citation.document_id)) }}</h4><a :href="citationUrl(citation)" target="_blank" rel="noopener" class="source-page-link" :aria-label="`打开${filenameOf(citation.document_id)}${citation.page != null ? '第'+citation.page+'页' : ''}（新窗口）`">{{ citation.page != null ? '第 '+citation.page+' 页' : '原资料' }} <span aria-hidden="true">↗</span></a></div><blockquote>{{ cleanExcerpt(citation.snippet, citation.page) }}</blockquote><small>{{ filenameOf(citation.document_id) }}</small></li></ol>
        <p v-else class="source-empty">本次没有可展示的引用，请调整问题或核对课程资料。</p>
      </section>
    </article>
    <section v-else class="before-reading"><span class="open-book-icon" aria-hidden="true">⌑</span><div><h2>答案之后，还有原文。</h2><p>回答中的引用连接着课程资料。<br>点开页码，看看原文是怎样说的。</p></div></section>
    <div class="desk-context"><p v-if="loadingContext" role="status">正在读取资料状态…</p><p v-else-if="contextFailure">{{ contextFailure }} <button class="text-button" @click="loadContext">重新加载</button></p><p v-else-if="!readyDocumentCount">本课还没有可检索资料。请先<router-link :to="`/courses/${courseId}/documents`">查看课程资料</router-link>，或联系教师。</p></div>
  </div>
</template>
<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../api";
import { session } from "../session";
import { questionDraft } from "../drafts";
import { askHistory, answerNotice, roundStatus } from "../askHistory.js";
import { cleanExcerpt, citationTitle } from "../citationDisplay.js";
import AnswerBody from "../components/AnswerBody.vue";

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
  if (citation.page != null) {
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

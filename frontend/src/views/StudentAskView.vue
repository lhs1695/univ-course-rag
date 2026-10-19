<template>
  <div class="study-page ask-study">
    <header class="study-page-title"><div><h1>课程问答</h1><p>在{{ courseTitle || '本课' }}的资料里，一起把问题想清楚。</p></div><router-link class="text-link" :to="`/courses/${courseId}/documents`">浏览课程资料 <StudyIcon name="arrow"/></router-link></header>
    <div class="ask-reading-layout">
      <div class="ask-reading-main">
        <section class="question-paper" aria-labelledby="question-title"><div class="paper-heading"><StudyIcon name="chat"/><h2 id="question-title">今天，想弄懂什么？</h2></div><form @submit.prevent="submitQuestion"><label class="sr-only" for="question-input">课程问题</label><textarea id="question-input" v-model="query" maxlength="2000" placeholder="写下一个具体的问题，或描述让你困惑的概念…" aria-describedby="question-help"/><div class="question-tools"><span>{{ query.length }} / 2000</span><el-button native-type="submit" type="primary" :loading="asking" :disabled="asking || !query.trim()">{{ asking ? '正在寻找依据' : '查找课内答案' }}<StudyIcon v-if="!asking" name="arrow"/></el-button></div></form></section>
        <p id="question-help" class="composer-note">仅依据本课资料作答。问句草稿与历史在刷新后清空。</p>
        <section v-if="selectedRound" class="answer-paper" :aria-busy="selectedRound.pending" aria-labelledby="answer-title"><div class="answer-question"><span>你的问题</span><h2>{{ selectedRound.question }}</h2></div><div class="answer-heading"><span class="answer-mark"><StudyIcon name="book"/></span><h2 id="answer-title">课内回答</h2><span v-if="result?.answer && !notice" class="answer-status">{{ result.citations?.length ? '已附资料依据' : '已返回回答' }}</span></div><div v-if="selectedRound.pending" class="answer-content"><p role="status">正在阅读本课资料、整理回答…<span v-if="waitSeconds >= 3"> 已等待 {{ waitSeconds }} 秒</span></p><el-skeleton :rows="4"/></div><div v-else-if="failure" class="answer-content"><el-alert :title="failure" type="error" :closable="false"/><button class="secondary-button" :disabled="asking" @click="retryQuestion">重试本次问题</button></div><div v-else-if="notice" class="answer-content"><el-alert :title="notice.message" :type="notice.type" :closable="false"/><p class="muted">{{ result?.error_code === 'NO_EVIDENCE' ? '试着补充概念名称或资料范围，也可以先浏览课程资料。' : '请根据提示调整问题，或稍后重试。' }}</p></div><div v-else-if="result?.answer" class="answer-content"><AnswerBody :answer="result.answer" :citations="result.citations || []" @citation="focusCitation"/></div>
          <section v-if="result?.citations?.length" class="answer-sources" aria-labelledby="evidence-title"><div class="sources-title"><h3 id="evidence-title">回答依据</h3><span>{{ result.citations.length }} 条引用 · 点击打开原文</span></div><ol><li v-for="(citation, index) in result.citations" :key="citation.chunk_id" :id="`source-${citation.chunk_id}`" tabindex="-1" class="source-paper"><div class="source-title"><span class="citation-number">{{ index + 1 }}</span><strong>{{ citationTitle(filenameOf(citation.document_id)) }}</strong><span v-if="citation.page != null" class="page-tag">第 {{ citation.page }} 页</span></div><blockquote>{{ cleanExcerpt(citation.snippet, citation.page) }}</blockquote><div class="source-bottom"><span>{{ filenameOf(citation.document_id) }}</span><a class="text-link" :href="citationUrl(citation)" target="_blank" rel="noopener">{{ citation.page != null ? `查看第 ${citation.page} 页原文` : '查看原资料' }}<StudyIcon name="external"/></a></div></li></ol><p class="muted source-disclaimer">AI 回答可能有误，请结合原文核对。</p></section>
          <div v-else-if="!selectedRound.pending && !failure" class="no-sources">本次没有可展示的资料引用。</div>
        </section>
        <section v-else class="ask-welcome"><div class="welcome-glyph" aria-hidden="true">“</div><h2>好问题，是理解的开始。</h2><p>可以问一个概念的含义、两种观点的区别，<br>也可以请它梳理课内知识的联系。</p><div class="question-patterns"><button @click="usePrompt('请解释「」的含义，并指出课内依据。')">理解一个概念 <span>+</span></button><button @click="usePrompt('「」与「」有什么区别？请结合本课资料说明。')">比较两个概念 <span>+</span></button><button @click="usePrompt('请梳理「」的主要观点与它们之间的联系。')">梳理知识联系 <span>+</span></button></div></section>
      </div>
      <aside class="learning-margin"><div class="margin-course" :style="{ background: identity.tint }"><span class="margin-symbol">{{ identity.symbol }}</span><strong>{{ courseTitle || '当前课程' }}</strong><p>把答案读懂，<br>也把依据看明白。</p></div><div class="margin-section"><h2>本课资料</h2><p v-if="loadingContext" role="status">正在读取资料…</p><template v-else-if="contextFailure"><p>{{ contextFailure }}</p><button class="quiet-button" @click="loadContext">重新加载</button></template><template v-else><p><strong>{{ readyDocumentCount }}</strong> 份资料可用于问答</p><router-link class="text-link" :to="`/courses/${courseId}/documents`">查看全部资料 <StudyIcon name="arrow"/></router-link></template></div><div class="margin-section"><h2>本次学习记录 <span>{{ history.rounds.length }}</span></h2><p v-if="!history.rounds.length">提问后，可在这里回看每一轮回答。</p><ol v-else class="study-history"><li v-for="round in [...history.rounds].reverse()" :key="round.id"><button :aria-pressed="history.selectedId === round.id" @click="selectRound(round.id)"><span>{{ round.question }}</span><small>{{ roundStatus(round) }}</small></button></li></ol></div><p class="margin-hint">新问题会携带上一轮上下文。<br>学习记录仅在当前会话保留。</p></aside>
    </div>
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
import StudyIcon from '../components/StudyIcon.vue';
import { courseIdentity } from '../courseIdentity';

const route = useRoute();
const courseId = computed(() => String(route.params.courseId));
const courseTitle = ref("");
const identity = computed(() => courseIdentity(courseTitle.value));
function usePrompt(text) { query.value = text; document.getElementById('question-input')?.focus(); }
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
  if ((filename.endsWith(".pdf") || documents.value.find(doc => doc.id === citation.document_id)?.filename?.toLowerCase().endsWith('.pdf')) && citation.page != null) {
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

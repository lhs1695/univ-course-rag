<template>
  <div class="study-workspace">
    <header class="study-top"><div class="study-breadcrumb"><router-link to="/courses">课程知识库</router-link><span>/</span><strong>{{ courseTitle || '课程问答' }}</strong></div><router-link class="text-button" :to="`/courses/${courseId}/documents`">课程资料 ↗</router-link></header>
    <div class="notebook-layout">
      <aside class="notebook-index" aria-label="本课问答记录">
        <div class="index-heading"><h2>学习记录</h2><button class="quiet-button" :disabled="asking" @click="newQuestion">新提问 +</button></div>
        <p class="study-meta">{{ history.rounds.length }} 次提问 · 本次会话</p>
        <ol v-if="history.rounds.length" class="notebook-rounds"><li v-for="round in history.rounds" :key="round.id"><button :aria-pressed="!composingNew && history.selectedId === round.id" @click="composingNew = false; selectRound(round.id)"><span>{{ round.question }}</span><small>{{ roundStatus(round) }}</small></button></li></ol>
        <p v-else class="index-empty">留下你的第一个问题。<br>每次探索，都可以回来接着读。</p>
        <div class="index-source"><h3>本课依据</h3><p v-if="loadingContext" role="status">正在读取资料…</p><template v-else-if="contextFailure"><p>{{ contextFailure }}</p><button class="quiet-button" @click="loadContext">重新加载</button></template><template v-else><p>{{ readyDocumentCount }} 份资料可用于问答</p><router-link :to="`/courses/${courseId}/documents`">查看资料目录 ↗</router-link></template><p class="study-meta">草稿和记录仅保存在本次会话，刷新页面后清空。</p></div>
      </aside>
      <main class="notebook-page">
        <header class="notebook-title"><h1>课程问答</h1><span>阅读 · 思考 · 核对</span></header>
        <div v-if="!composingNew && selectedRound" class="question-receipt"><span class="study-meta">你的问题</span><p>{{ selectedRound.question }}</p></div>
        <section v-if="!composingNew && selectedRound" class="notebook-answer" :aria-busy="selectedRound.pending" aria-labelledby="answer-heading">
          <div class="answer-heading"><h2 id="answer-heading">课内回答</h2><span class="study-meta">{{ selectedRound.pending ? '正在查找依据' : '请结合原文阅读' }}</span></div>
          <div v-if="selectedRound.pending" class="answer-wait" role="status"><span class="search-pulse" aria-hidden="true"></span><p>正在检索本课资料，组织回答…</p><small v-if="waitSeconds >= 3">已等待 {{ waitSeconds }} 秒，问题已保留</small></div>
          <div v-else-if="failure" class="study-error" role="alert"><p>{{ failure }}</p><button class="quiet-button" :disabled="asking" @click="retryQuestion">重试本次问题</button></div>
          <div v-else-if="result?.error_code === 'NO_EVIDENCE'" class="answer-message"><h3>课内依据还不足</h3><p>试着补充具体概念或章节，也可以先查看课程资料。本次没有足够依据支持回答。</p><router-link :to="`/courses/${courseId}/documents`">查看本课资料 ↗</router-link></div>
          <div v-else-if="notice" class="answer-message" role="status"><p>{{ notice.message }}</p></div>
          <AnswerBody v-else-if="result?.answer" :answer="result.answer" :citations="result.citations" @citation="focusCitation" />
        </section>
        <div v-else class="notebook-start"><svg class="open-book" viewBox="0 0 80 64" aria-hidden="true"><path d="M8 8h22c5 0 10 4 10 8 0-4 5-8 10-8h22v44H50c-5 0-10 3-10 6 0-3-5-6-10-6H8zM40 16v42M16 20h14M16 28h14M16 36h10M50 20h14M50 28h14M50 36h10" /></svg><h2>把不理解的地方，问清楚。</h2><p>提出一个具体问题。我们从本课资料中寻找依据，<br class="desktop-break">你可以沿着引用，回到原文继续阅读。</p><div class="question-guides"><span>比较两个概念</span><span>理解一段论述</span><span>梳理知识联系</span></div></div>
        <form class="notebook-composer" @submit.prevent="submitFromComposer"><label for="study-question">{{ selectedRound && !composingNew ? '继续追问' : '写下你的问题' }}</label><textarea id="study-question" ref="questionInput" v-model="query" required maxlength="2000" rows="3" placeholder="你想弄懂本课的哪个问题？" :disabled="asking" @keydown.ctrl.enter.prevent="submitFromComposer" @keydown.meta.enter.prevent="submitFromComposer"></textarea><div class="notebook-composer-foot"><span>{{ query.length }} / 2000 <span class="shortcut">· Ctrl + Enter 发送</span></span><button class="ink-button" type="submit" :disabled="asking || !query.trim()">{{ asking ? '正在寻找依据…' : '发送问题' }} <span aria-hidden="true">↑</span></button></div></form>
        <p class="answer-caution">回答仅基于本课资料，仍需核对原文。{{ history.rounds.length ? '继续提问会携带上一轮上下文。' : '' }}</p>
      </main>
      <aside class="source-drawer" aria-labelledby="sources-title"><div class="source-drawer-title"><h2 id="sources-title">原文依据</h2><span>{{ !composingNew ? result?.citations?.length || 0 : 0 }} 条</span></div>
        <ol v-if="!composingNew && result?.citations?.length" class="source-stack"><li v-for="(citation, index) in result.citations" :id="`source-${citation.chunk_id}`" :key="citation.chunk_id" tabindex="-1" class="source-leaf"><div class="source-leaf-top"><span>引用 {{ index + 1 }}</span><a :href="citationUrl(citation)" target="_blank" rel="noopener" :aria-label="`打开${filenameOf(citation.document_id)}第${citation.page || '未知'}页`">{{ citation.page != null ? `第 ${citation.page} 页 ↗` : '打开原文 ↗' }}</a></div><h3>{{ citationTitle(filenameOf(citation.document_id)) }}</h3><p class="source-file">{{ filenameOf(citation.document_id) }}</p><blockquote>{{ cleanExcerpt(citation.snippet, citation.page) }}</blockquote><a class="source-open" :href="citationUrl(citation)" target="_blank" rel="noopener">{{ citation.page != null ? `阅读 PDF 第 ${citation.page} 页` : '阅读原资料' }} <span aria-hidden="true">↗</span></a></li></ol>
        <div v-else class="source-await"><div class="page-glyph" aria-hidden="true">页</div><h3>{{ !composingNew && result ? '本次没有可展示的引用' : '每一个依据，都有出处' }}</h3><p>回答中的引用会在这里展开，包含资料名、原文摘录与页码。</p><p>点击页码，在新标签页核对原 PDF。</p></div>
      </aside>
    </div>
  </div>
</template>
<script setup>
import { computed, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { api } from "../../api";
import { session } from "../../session";
import { questionDraft } from "../../drafts";
import { askHistory, answerNotice, roundStatus } from "../../askHistory.js";
import { cleanExcerpt, citationTitle } from "../../citationDisplay.js";
import AnswerBody from "../../components/AnswerBody.vue";

const composingNew = ref(false);
const questionInput = ref(null);
function newQuestion() { composingNew.value = true; questionInput.value?.focus(); }
function submitFromComposer() {
  if (asking.value || !query.value.trim()) return;
  composingNew.value = false;
  const text = query.value.trim();
  askQuestion(text);
  query.value = '';
}
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

function focusCitation(id) { composingNew.value = false;
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


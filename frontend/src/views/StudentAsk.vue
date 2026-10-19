<template>
  <div class="study-ask-layout">
    <section class="study-reading">
      <header class="study-ask-heading"><p class="study-kicker">{{ courseAccess.course?.title }} / 课程问答</p><h1>把疑问，变成理解。</h1><p>聚焦一个问题，在本课资料中寻找答案。</p></header>
      <form class="study-composer" @submit.prevent="submit"><label for="study-question">你想了解什么？</label><textarea id="study-question" v-model="query" rows="4" maxlength="2000" placeholder="写下你的问题，可以补充概念、章节或不理解的地方…" aria-describedby="study-question-help" @keydown.ctrl.enter.prevent="submit" @keydown.meta.enter.prevent="submit" /><div class="study-composer-footer"><span id="study-question-help">{{ query.length }} / 2000 字 · Ctrl / ⌘ + Enter 提问</span><button class="study-button study-primary" :disabled="asking || !query.trim()" type="submit">{{ asking ? '正在查找依据…' : '发送问题' }}<StudyIcon name="arrow" /></button></div></form>
      <p class="study-footnote">仅依据本课资料作答。新问题会携带上一轮上下文；草稿与历史在刷新后清空。</p>
      <div v-if="!selected" class="study-start"><div class="study-page-corner">问</div><h2>从一个具体的问题开始</h2><p>你可以询问一个概念、比较两种观点，<br>或补充章节与条件，让问题更明确。</p><div class="study-example">阅读回答 <span>→</span> 查看依据 <span>→</span> 回到原文</div></div>
      <section v-else class="study-response" :aria-busy="selected.pending" aria-labelledby="study-response-title">
        <div class="study-question-summary"><span class="study-kicker">本次问题</span><p>{{ selected.question }}</p></div>
        <div class="study-response-title"><h2 id="study-response-title">课内回答</h2><span class="study-muted">{{ roundStatus(selected) }}</span></div>
        <div v-if="selected.pending" role="status"><p>正在检索课内资料并组织回答，已等待 {{ seconds }} 秒…</p><el-skeleton :rows="4" animated /></div>
        <div v-else-if="selected.failure" class="study-error" role="alert">{{ selected.failure }}<button class="study-button" :disabled="asking" @click="ask(selected.question)">重试本次问题</button></div>
        <div v-else><p v-if="notice" class="study-notice" role="status">{{ notice.message }} <span v-if="result?.error_code === 'NO_EVIDENCE'">请检查资料范围，或补充更具体的问题。</span></p><AnswerBody v-if="result?.answer && (!notice || notice.type !== 'error')" :answer="result.answer" :citations="result.citations || []" @citation="focusCitation" /><p v-else-if="!notice" class="study-notice">本次未返回回答，请稍后重试。</p></div>
        <section v-if="!selected.pending" class="study-evidence" aria-labelledby="study-evidence-title"><div class="study-response-title"><h2 id="study-evidence-title">回答依据</h2><span class="study-muted">{{ result?.citations?.length || 0 }} 条引用</span></div><p class="study-muted">点开原文页码，对照上下文核对回答。</p><ol v-if="result?.citations?.length" class="study-sources"><li v-for="(citation, index) in result.citations" :id="`study-source-${citation.chunk_id}`" :key="citation.chunk_id" tabindex="-1"><div class="study-source-head"><span class="study-source-number">{{ String(index + 1).padStart(2, '0') }}</span><div><h3>{{ citationTitle(filename(citation.document_id)) }}</h3><small>{{ filename(citation.document_id) }}</small></div><a :href="citationUrl(citation)" target="_blank" rel="noopener" class="study-page-link">{{ citation.page != null ? `第 ${citation.page} 页` : '原资料' }} ↗<span class="study-sr">（新标签页）</span></a></div><blockquote>{{ cleanExcerpt(citation.snippet, citation.page) }}</blockquote></li></ol><p v-else class="study-notice">本次没有可展示的引用。请勿将无依据的回答作为定论。</p></section>
      </section>
    </section>
    <aside class="study-learning-aside"><div class="study-session-label">本次学习</div><h2>问题记录 <span>{{ history.rounds.length }}</span></h2><p v-if="!history.rounds.length" class="study-muted">提问后，你可以在这里回顾本次学习中的每一轮问答。</p><ol v-else class="study-history"><li v-for="(round, index) in history.rounds" :key="round.id"><button :aria-pressed="history.selectedId === round.id" @click="select(round.id)"><span>{{ String(index + 1).padStart(2, '0') }}</span><span>{{ round.question }}<small>{{ roundStatus(round) }}</small></span></button></li></ol><div class="study-aside-source"><StudyIcon name="book" /><h3>学习范围</h3><p v-if="contextLoading" role="status">正在读取资料…</p><template v-else-if="contextFailure"><p>{{ contextFailure }}</p><button class="study-button" @click="loadContext">重试读取</button></template><p v-else>本课 {{ documents.filter(d => d.job_status === 'succeeded').length }} 份资料已入库。<br>回答可能不完整，请以原文为准。</p><router-link :to="`/courses/${courseId}/documents`" class="study-text-link">浏览课程资料 →</router-link></div></aside>
  </div>
</template>
<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { api } from '../api';
import { session } from '../session';
import { courseAccess } from '../courseAccess';
import { questionDraft } from '../drafts';
import { askHistory, answerNotice, roundStatus } from '../askHistory';
import { cleanExcerpt, citationTitle } from '../citationDisplay';
import AnswerBody from '../components/AnswerBody.vue';
import StudyIcon from '../components/StudyIcon.vue';
const courseId = String(useRoute().params.courseId), userId = session.user.id;
const documents = ref([]), contextLoading = ref(true), contextFailure = ref(''), revision = ref(0), draftRevision = ref(0), now = ref(Date.now());
const query = computed({ get() { draftRevision.value; return questionDraft(userId, courseId); }, set(v) { questionDraft(userId, courseId, v); draftRevision.value++; } });
const unsubscribe = askHistory.subscribe(() => revision.value++);
const history = computed(() => { revision.value; const s = askHistory.course(userId, courseId); return { ...s, rounds: s.rounds.map(r => ({ ...r })) }; });
const selected = computed(() => history.value.rounds.find(r => r.id === history.value.selectedId));
const asking = computed(() => history.value.rounds.some(r => r.pending));
const result = computed(() => selected.value?.result);
const notice = computed(() => answerNotice(result.value));
const seconds = computed(() => Math.max(0, Math.floor((now.value - (selected.value?.startedAt || now.value)) / 1000)));
let active = true;
const timer = setInterval(() => { if (asking.value) now.value = Date.now(); }, 1000);
async function loadContext() { contextLoading.value = true; contextFailure.value = ''; try { const rows = await api(`/courses/${courseId}/documents`); if (active) documents.value = rows; } catch (e) { if (active) contextFailure.value = e.message; } finally { if (active) contextLoading.value = false; } }
function filename(id) { return documents.value.find(d => d.id === id)?.filename || '课程资料'; }
function citationUrl(c) { const doc = documents.value.find(d => d.id === c.document_id); return c.page != null && (!doc || doc.filename.toLowerCase().endsWith('.pdf')) ? `${c.content_url.split('#')[0]}#page=${Math.max(1, Number(c.page) || 1)}` : c.content_url; }
function select(id) { askHistory.select(userId, courseId, id); }
function ask(text) { now.value = Date.now(); return askHistory.ask(userId, courseId, text, api); }
function submit() { if (query.value.trim() && !asking.value) ask(query.value.trim()); }
async function focusCitation(id) { await nextTick(); const el = document.getElementById(`study-source-${id}`); el?.focus({ preventScroll: true }); el?.scrollIntoView({ block: 'center', behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth' }); }
onMounted(loadContext); onUnmounted(() => { active = false; unsubscribe(); clearInterval(timer); });
</script>

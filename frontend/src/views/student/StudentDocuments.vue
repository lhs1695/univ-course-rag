<template>
  <div class="study-documents">
    <header class="study-top"><div class="study-breadcrumb"><router-link to="/courses">课程知识库</router-link><span>/</span><router-link :to="`/courses/${courseId}`">{{ courseAccess.course?.title }}</router-link><span>/ 资料</span></div><router-link class="text-button" :to="`/courses/${courseId}`">回到问答 ↗</router-link></header>
    <main class="document-canvas">
      <header class="study-title"><div><h1>课程资料</h1><p>回答的出处，也是你阅读的起点。</p></div><button class="quiet-button" :disabled="loading" @click="loadDocuments">{{ loading ? '加载中…' : '刷新资料' }}</button></header>
      <div class="library-tools"><label class="study-search"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10" cy="10" r="6"/><path d="m15 15 5 5"/></svg><input v-model="search" type="search" aria-label="查找资料" placeholder="按文件名查找资料" /></label><span class="study-meta">{{ filtered.length }} 份资料</span></div>
      <p v-if="failure" class="study-error" role="alert">{{ failure }} <button class="quiet-button" @click="loadDocuments">重试</button></p>
      <p v-else-if="loading && !documents.length" class="study-state" role="status">正在读取本课资料…</p>
      <div v-else-if="filtered.length" class="document-ledger">
        <div class="document-labels" aria-hidden="true"><span>资料名称</span><span>阅读范围</span><span>打开原文</span></div>
        <article v-for="row in filtered" :key="row.id" class="document-row">
          <div class="document-identity"><span class="file-format">{{ isPdfDocument(row) ? 'PDF' : row.filename.split('.').pop().toUpperCase() }}</span><div><h2>{{ row.filename }}</h2><span class="study-meta">{{ documentCoverage(row).label }}</span></div></div>
          <div class="document-extent">{{ documentPageLabel(row) }}</div>
          <form v-if="row.job_status === 'succeeded'" class="document-open" @submit.prevent="openDocument(row)"><template v-if="isPdfDocument(row)"><label :for="`page-${row.id}`">第</label><input :id="`page-${row.id}`" v-model="pages[row.id]" :aria-label="`${row.filename}的页码`" inputmode="numeric" @blur="normalizePage(row)" /><span>页</span></template><button class="quiet-button" type="submit">打开原文 ↗</button></form>
          <span v-else class="study-meta">资料尚未就绪</span>
        </article>
      </div>
      <div v-else class="study-state"><h2>{{ search ? '没有匹配的资料' : '本课尚无资料' }}</h2><p>{{ search ? '试试更短的文件名。' : '教师上传资料后，会显示在这里。' }}</p><button v-if="search" class="quiet-button" @click="search = ''">清除搜索</button></div>
      <div class="reading-note"><h2>让阅读接上回答</h2><p>在问答中点击引用，可回到这份资料的指定 PDF 页。这里也可以输入页码，直接开始阅读。</p><span>原文在新标签页打开，当前学习进度会保留。</span></div>
    </main>
  </div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { api } from '../../api';
import { courseAccess } from '../../courseAccess';
import { clampDocumentPage, documentContentUrl, documentCoverage, documentPageLabel, isPdfDocument } from '../../documentDisplay';
const route = useRoute();
const courseId = computed(() => String(route.params.courseId));
const documents = ref([]), pages = ref({}), search = ref(''), loading = ref(false), failure = ref('');
const filtered = computed(() => documents.value.filter(row => row.filename.toLowerCase().includes(search.value.trim().toLowerCase())));
let active = true, timer;
async function loadDocuments() {
  if (loading.value || !active) return;
  loading.value = true;
  try {
    const rows = await api(`/courses/${courseId.value}/documents`);
    if (!active) return;
    documents.value = rows;
    rows.forEach(row => { pages.value[row.id] ??= 1; });
    failure.value = '';
    clearTimeout(timer);
    if (rows.some(row => ['pending', 'running'].includes(row.job_status))) timer = setTimeout(loadDocuments, 3000);
  } catch (error) { if (active) failure.value = error.message; }
  finally { loading.value = false; }
}
function normalizePage(row) { pages.value[row.id] = clampDocumentPage(pages.value[row.id], row); }
function openDocument(row) { normalizePage(row); window.open(documentContentUrl(courseId.value, row, pages.value[row.id]), '_blank', 'noopener'); }
onMounted(loadDocuments);
onUnmounted(() => { active = false; clearTimeout(timer); });
</script>

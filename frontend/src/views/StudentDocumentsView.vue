<template>
  <div class="study-page documents-study">
    <header class="study-page-title"><div><h1>课程资料</h1><p>阅读原文，也是核对答案的起点。</p></div><router-link class="secondary-button" :to="`/courses/${courseId}`"><StudyIcon name="chat"/>带着问题去提问</router-link></header>
    <div class="library-banner"><StudyIcon name="book"/><div><strong>{{ courseAccess.course?.title }}的资料库</strong><p>回答中的引用来自这里。选择页码，可以直接打开 PDF 对应页。</p></div><span v-if="!loading">{{ documents.length }} 份资料</span></div>
    <div class="section-toolbar"><label class="study-search"><StudyIcon name="search"/><input v-model="search" placeholder="按文件名查找" aria-label="按文件名查找资料"/></label><button class="quiet-button" :disabled="loading" @click="load">{{ loading ? '正在刷新…' : '刷新列表' }}</button></div>
    <div v-if="failure" class="study-empty" role="alert"><p>{{ failure }}</p><button class="secondary-button" @click="load">重新加载</button></div>
    <el-skeleton v-else-if="loading && !documents.length" :rows="5"/>
    <div v-else-if="!filtered.length" class="study-empty"><h3>{{ search ? '没有匹配的资料' : '资料正在等你' }}</h3><p>{{ search ? '试试其他文件名，或清空搜索。' : '本课还没有资料，请联系本课教师。' }}</p><button v-if="search" class="quiet-button" @click="search = ''">清空搜索</button></div>
    <div v-else class="document-library"><div class="library-columns"><span>资料名称</span><span>阅读状态</span><span>打开原文</span></div><article v-for="doc in filtered" :key="doc.id" class="library-row"><div class="document-identity"><StudyIcon name="file"/><div><h2>{{ doc.filename }}</h2><p>{{ isPdfDocument(doc) ? 'PDF 文档' : '课程文档' }} <span>·</span> {{ documentPageLabel(doc) }}</p></div></div><span class="document-status" :class="doc.job_status === 'succeeded' && !doc.quality_warning ? 'ready' : 'limited'">{{ documentCoverage(doc).label }}</span><div v-if="doc.job_status === 'succeeded'" class="document-open"><label v-if="isPdfDocument(doc)">第 <input v-model="pages[doc.id]" type="number" min="1" :max="doc.source_unit_count || undefined" :aria-label="`${doc.filename}的打开页码`" @blur="correctPage(doc)"/> 页</label><a class="secondary-button" :href="documentContentUrl(courseId, doc, pages[doc.id] || 1)" target="_blank" rel="noopener" @click="correctPage(doc)">打开<StudyIcon name="external"/></a></div><span v-else class="muted">暂不可打开</span></article></div>
    <div class="reading-note"><span>阅读提示</span><p>若资料标记为“文本较少”，回答依据可能不完整，请以原始课件为准。PDF 在新标签页打开。</p></div>
  </div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { api } from '../api';
import { courseAccess } from '../courseAccess';
import { clampDocumentPage, documentContentUrl, documentCoverage, documentPageLabel, isPdfDocument } from '../documentDisplay';
import StudyIcon from '../components/StudyIcon.vue';
const route = useRoute(), courseId = String(route.params.courseId);
const documents = ref([]), pages = ref({}), search = ref(''), loading = ref(true), failure = ref('');
const filtered = computed(() => documents.value.filter(row => row.filename.toLowerCase().includes(search.value.trim().toLowerCase())));
let active = true, timer;
function correctPage(doc) { pages.value[doc.id] = clampDocumentPage(pages.value[doc.id], doc); }
async function load() { clearTimeout(timer); loading.value = true; try { const rows = await api(`/courses/${courseId}/documents`); if (!active) return; documents.value = rows; failure.value = ''; if (rows.some(row => ['pending', 'running'].includes(row.job_status))) timer = setTimeout(load, 3000); } catch (error) { if (active) failure.value = error.message; } finally { if (active) loading.value = false; } }
onMounted(load); onUnmounted(() => { active = false; clearTimeout(timer); });
</script>

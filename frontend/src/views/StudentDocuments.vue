<template>
  <div class="study-content">
    <div class="study-page-heading"><div><p class="study-kicker">{{ courseAccess.course?.title }} / 资料书架</p><h1>每一次回答的出处。</h1><p>阅读课程原资料，也可以直接前往你想核对的一页。</p></div><button class="study-button" :disabled="loading" @click="load"><StudyIcon name="file" />{{ loading ? '加载中…' : '刷新资料' }}</button></div>
    <div class="study-toolbar"><h2>课程资料 <span class="study-muted">{{ documents.length }}</span></h2><label class="study-search"><StudyIcon name="search" /><input v-model="search" aria-label="查找资料" placeholder="按文件名称查找" type="search" /></label></div>
    <p v-if="failure" class="study-error" role="alert">{{ failure }} 请点击刷新资料重试。</p>
    <div v-else-if="loading" class="study-empty" role="status">正在读取本课资料…<el-skeleton :rows="4" animated /></div>
    <div v-else-if="!documents.length" class="study-empty"><h2>本课还没有资料</h2><p>教师上传后，资料会出现在这里。你可以稍后刷新。</p></div>
    <p v-else-if="!filtered.length" class="study-empty">没有匹配的资料，请调整查找内容。</p>
    <ul v-else class="study-doc-list">
      <li v-for="doc in filtered" :key="doc.id" class="study-doc-row"><div class="study-doc-symbol"><StudyIcon name="file" /><small>{{ isPdfDocument(doc) ? 'PDF' : doc.filename.split('.').at(-1).toUpperCase() }}</small></div><div class="study-doc-info"><h2>{{ doc.filename }}</h2><p>{{ documentPageLabel(doc) }}<span>·</span>{{ documentCoverage(doc).label }}<span v-if="doc.quality_warning"> · 请结合原文核对</span></p></div><div v-if="doc.job_status === 'succeeded'" class="study-doc-open"><label v-if="isPdfDocument(doc)" :for="`page-${doc.id}`">前往第 <input :id="`page-${doc.id}`" v-model="pages[doc.id]" type="number" min="1" :max="doc.source_unit_count || undefined" :aria-label="`${doc.filename} 打开页码`" @blur="correct(doc)" /> 页</label><a :href="url(doc)" target="_blank" rel="noopener" class="study-button" @click="correct(doc)">打开原文<StudyIcon name="arrow" /><span class="study-sr">（新标签页）</span></a></div><span v-else class="study-muted">资料暂不可打开</span></li>
    </ul>
    <p class="study-footnote">资料仅供本课学习。PDF 在新标签页打开，页码以原文件为准。</p>
  </div>
</template>
<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute } from 'vue-router';
import { api } from '../api';
import { courseAccess } from '../courseAccess';
import { clampDocumentPage, documentContentUrl, documentCoverage, documentPageLabel, isPdfDocument } from '../documentDisplay';
import StudyIcon from '../components/StudyIcon.vue';
const courseId = String(useRoute().params.courseId);
const documents = ref([]), loading = ref(true), failure = ref(''), search = ref(''), pages = ref({});
const filtered = computed(() => documents.value.filter(d => d.filename.toLowerCase().includes(search.value.toLowerCase())));
let active = true, timer;
function correct(doc) { pages.value[doc.id] = clampDocumentPage(pages.value[doc.id], doc); }
function url(doc) { return documentContentUrl(courseId, doc, pages.value[doc.id] || 1); }
async function load() { clearTimeout(timer); loading.value = true; failure.value = ''; try { const rows = await api(`/courses/${courseId}/documents`); if (!active) return; documents.value = rows; if (rows.some(d => ['pending', 'running'].includes(d.job_status))) timer = setTimeout(load, 10000); } catch (e) { if (active) failure.value = e.message; } finally { if (active) loading.value = false; } }
onMounted(load); onUnmounted(() => { active = false; clearTimeout(timer); });
</script>

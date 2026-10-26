<template>
  <div class="document-library">
    <header class="library-heading"><div><p class="eyebrow">课程资料 / 阅读目录</p><h1>课程资料</h1><p>问答的依据都在这里。打开资料，也可以直接跳到某一页。</p></div><el-button :loading="loading" @click="$emit('refresh')">刷新资料</el-button></header>
    <el-alert v-if="failure" :title="failure" type="error" :closable="false"/>
    <div class="library-search"><label for="document-search">查找资料</label><el-input id="document-search" v-model="search" placeholder="按文件名搜索" clearable/><span>{{ filtered.length }} 份资料</span></div>
    <p v-if="loading" class="study-empty" role="status">正在整理课程资料…</p>
    <div v-else-if="!filtered.length" class="study-empty"><h2>{{ search ? '没有找到这份资料' : '本课资料还在准备中' }}</h2><p>{{ search ? '试着缩短文件名，或清空搜索查看全部资料。' : '请联系本课教师上传资料，稍后刷新查看。' }}</p></div>
    <ul v-else class="library-list"><li v-for="doc in filtered" :key="doc.id" class="library-document"><span class="file-fold" aria-hidden="true">{{ isPdfDocument(doc) ? 'PDF' : doc.filename.split('.').pop().toUpperCase().slice(0,4) }}</span><div class="library-file-info"><h2>{{ doc.filename }}</h2><p><span>{{ doc.retrieval_enabled ? '检索启用' : '检索停用' }}</span></p></div><div v-if="doc.job_status === 'succeeded'" class="library-file-actions"><label v-if="isPdfDocument(doc)" :for="`page-${doc.id}`">第 <input :id="`page-${doc.id}`" v-model="pages[doc.id]" type="number" min="1" :max="doc.source_unit_count || undefined" :aria-label="`${doc.filename} 打开页码`" @blur="correctPage(doc)"/> 页</label><a :href="url(doc)" target="_blank" rel="noopener" class="file-open" @click="correctPage(doc)" :aria-label="`打开${doc.filename}（新窗口）`">打开{{ isPdfDocument(doc) ? ' PDF' : '资料' }} <span aria-hidden="true">↗</span></a></div><span v-else class="unavailable-file">{{ doc.job_status === 'failed' ? '请联系教师处理' : '处理完成后可打开' }}</span></li></ul>
    <div class="library-note"><span aria-hidden="true">↳</span><p>想带着问题读？<router-link :to="`/courses/${courseId}`">回到课程提问</router-link><br><small>所有原资料均在新标签页打开。</small></p></div>
  </div>
</template>
<script setup>
import { computed, ref } from 'vue';
import { clampDocumentPage, documentContentUrl, isPdfDocument } from '../documentDisplay';
const props = defineProps({documents: {type:Array,default:()=>[]},loading:Boolean,failure:String,courseId:String});
defineEmits(['refresh']);
const search = ref('');
const pages = ref({});
const filtered = computed(()=>props.documents.filter(doc=>doc.filename.toLowerCase().includes(search.value.trim().toLowerCase())));
function correctPage(doc) { pages.value[doc.id] = clampDocumentPage(pages.value[doc.id],doc); }
function url(doc) { return documentContentUrl(props.courseId,doc,pages.value[doc.id] ?? 1); }
</script>

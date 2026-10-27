<template>
  <div class="document-library">
    <header class="library-heading"><div><p class="eyebrow">课程资料 / 阅读目录</p><h1>课程资料</h1><p>问答的依据都在这里。打开资料，也可以直接跳到某一页。</p></div><el-button :loading="loading" @click="$emit('refresh')">刷新资料</el-button></header>
    <el-alert v-if="failure" :title="failure" type="error" :closable="false"/>
    <FolderLibrary v-model="selectedFolderId" :documents="filtered" :folders="folders" :loading="loading">
      <template #default="{ group }">
        <h2 class="student-folder-title">{{ group.label }}</h2>
        <div class="library-search"><label for="document-search">查找资料</label><el-input id="document-search" v-model="search" placeholder="在当前夹按文件名搜索" clearable/><span>{{ group.documents.length }} 份资料</span></div>
        <p v-if="loading" class="study-empty" role="status">正在整理课程资料…</p>
        <el-empty v-else-if="!group.documents.length" :description="search.trim() ? '当前夹没有匹配资料' : '此夹暂无可阅读资料'" :image-size="80">
          <p class="subtle">{{ search.trim() ? '请缩短文件名，或选择其他资料夹。' : '可选择其他资料夹，或联系本课教师上传资料。' }}</p>
          <el-button v-if="search.trim()" @click="search = ''">清空搜索</el-button>
        </el-empty>
        <ul v-else class="library-list"><li v-for="doc in group.documents" :key="doc.id" class="library-document"><span class="file-fold" aria-hidden="true">{{ isPdfDocument(doc) ? 'PDF' : doc.filename.split('.').pop().toUpperCase().slice(0,4) }}</span><div class="library-file-info"><h2>{{ doc.filename }}</h2><p><span>{{ doc.retrieval_enabled ? '检索启用' : '检索停用' }}</span></p></div><div v-if="doc.job_status === 'succeeded'" class="library-file-actions"><label v-if="isPdfDocument(doc)" :for="`page-${doc.id}`">第 <input :id="`page-${doc.id}`" v-model="pages[doc.id]" type="number" min="1" :max="doc.source_unit_count || undefined" :aria-label="`${doc.filename} 打开页码`" @blur="correctPage(doc)"/> 页</label><a :href="url(doc)" target="_blank" rel="noopener" class="file-open" @click="correctPage(doc)" :aria-label="`打开${doc.filename}（新窗口）`">打开{{ isPdfDocument(doc) ? ' PDF' : '资料' }} <span aria-hidden="true">↗</span></a></div><span v-else class="unavailable-file">{{ doc.job_status === 'failed' ? '请联系教师处理' : '处理完成后可打开' }}</span></li></ul>
      </template>
    </FolderLibrary>
    <div class="library-note"><span aria-hidden="true">↳</span><p>想带着问题读？<router-link :to="`/courses/${courseId}`">回到课程提问</router-link><br><small>所有原资料均在新标签页打开。</small></p></div>
  </div>
</template>
<script setup>
import { computed, ref } from 'vue';
import FolderLibrary from './FolderLibrary.vue';
import { clampDocumentPage, documentContentUrl, isPdfDocument } from '../documentDisplay';
const props = defineProps({folders: {type:Array,default:()=>[]},documents: {type:Array,default:()=>[]},loading:Boolean,failure:String,courseId:String});
defineEmits(['refresh']);
const search = ref('');
const selectedFolderId = ref(null);
const pages = ref({});
const filtered = computed(()=>props.documents.filter(doc=>doc.filename.toLowerCase().includes(search.value.trim().toLowerCase())));
function correctPage(doc) { pages.value[doc.id] = clampDocumentPage(pages.value[doc.id],doc); }
function url(doc) { return documentContentUrl(props.courseId,doc,pages.value[doc.id] ?? 1); }
</script>

<style scoped>
.student-folder-title { font-size: 18px; margin: 0 0 16px; overflow-wrap: anywhere; }
.subtle { color: var(--text-muted); font-size: 13px; line-height: 1.7; }
</style>

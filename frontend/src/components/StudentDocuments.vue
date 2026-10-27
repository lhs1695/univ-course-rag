<template>
  <div class="document-library">
    <header class="library-heading"><div><h1>课程资料</h1><p>问答的依据都在这里。打开资料，也可以直接跳到某一页。</p></div></header>
    <el-alert v-if="failure" :title="failure" type="error" :closable="false"/>
    <FolderLibrary v-model="selectedFolderId" v-model:search="search" :documents="documents" :folders="folders" :loading="loading">
      <template #default="{ group }">
        <h2 class="student-folder-title">{{ group.label }}</h2>
        <p v-if="loading" class="study-empty" role="status">正在整理课程资料…</p>
        <el-empty v-else-if="!group.documents.length" :description="search.trim() ? '本课没有匹配资料' : '暂无可阅读资料'" :image-size="80">
          <p class="subtle">{{ search.trim() ? '试试更短的文件名关键词。' : '可选择其他资料夹，或联系本课教师上传资料。' }}</p>
          <el-button v-if="search.trim()" @click="search = ''">清空搜索</el-button>
        </el-empty>
        <ul v-else class="library-list">
          <li v-for="doc in group.documents" :key="doc.id" class="library-document">
            <span class="file-fold" aria-hidden="true">{{ isPdfDocument(doc) ? 'PDF' : doc.filename.split('.').pop().toUpperCase().slice(0,4) }}</span>
            <div class="library-file-info"><h3>{{ doc.filename }}</h3><p><span>{{ folderLabel(doc) }}</span><span v-if="isPdfDocument(doc) && doc.source_unit_count">{{ doc.source_unit_count }} 页</span></p></div>
            <div v-if="doc.job_status === 'succeeded'" class="library-file-actions">
              <label v-if="isPdfDocument(doc)" :for="`page-${doc.id}`">第 <input :id="`page-${doc.id}`" v-model="pages[doc.id]" type="number" min="1" :max="doc.source_unit_count || undefined" :aria-label="`${doc.filename} 打开页码`" @blur="correctPage(doc)"/> 页</label>
              <router-link :to="url(doc)" class="file-open" @click="correctPage(doc)" :aria-label="`打开${doc.filename}（页内预览）`">打开 <span aria-hidden="true">↗</span></router-link>
              <a :href="documentDownloadUrl(courseId, doc)" :download="doc.filename" class="file-download" :aria-label="`下载${doc.filename}`">下载</a>
            </div>
            <span v-else class="unavailable-file">{{ doc.job_status === 'failed' ? '请联系教师处理' : '处理完成后可打开' }}</span>
          </li>
        </ul>
      </template>
    </FolderLibrary>
    <div class="library-note"><span aria-hidden="true">↳</span><p>想带着问题读？<router-link :to="`/courses/${courseId}`">回到课程提问</router-link><br><small>所有原资料均在新标签页打开。</small></p></div>
  </div>
</template>
<script setup>
import { computed, ref } from 'vue';
import FolderLibrary from './FolderLibrary.vue';
import { clampDocumentPage, documentContentUrl, documentDownloadUrl, isPdfDocument } from '../documentDisplay';
import { folderOptions } from '../documentFolders';
const props = defineProps({folders: {type:Array,default:()=>[]},documents: {type:Array,default:()=>[]},loading:Boolean,failure:String,courseId:String});
const search = ref('');
const selectedFolderId = ref(null);
const pages = ref({});
const folderChoices = computed(() => folderOptions(props.folders));
function folderLabel(doc) { return folderChoices.value.find(folder => folder.id === doc.folder_id)?.label || doc.folder_name || '课程根目录'; }
function correctPage(doc) { pages.value[doc.id] = clampDocumentPage(pages.value[doc.id],doc); }
function url(doc) { return documentContentUrl(props.courseId,doc,pages.value[doc.id] ?? 1); }
</script>

<style scoped>
.student-folder-title { font-size: 18px; margin: 0 0 16px; overflow-wrap: anywhere; }
.library-heading { padding-top: 12px; padding-bottom: 8px; }
.library-list { margin-top: 0; }
.library-document { gap: 16px; padding: 20px 0; }
.library-document:last-child { border-bottom: 0; padding-bottom: 4px; }
.library-file-info h3 { font-size: 14px; font-weight: 600; line-height: 1.7; margin: 0; overflow-wrap: anywhere; }
.library-file-info p { font-size: 12px; flex-wrap: wrap; overflow-wrap: anywhere; }
.library-file-actions { gap: 12px; flex-wrap: wrap; }
.file-download { color: var(--el-color-primary); font-size: 12px; padding: 8px 4px; }
.file-download:hover { text-decoration: underline; }
.subtle { color: var(--text-muted); font-size: 13px; line-height: 1.7; }
@media (max-width: 1200px) {
  .library-document { flex-wrap: wrap; }
  .library-file-actions { margin-left: 58px; }
}
@media (max-width: 560px) {
  .library-file-actions { margin-left: 0; width: 100%; justify-content: flex-start; }
}
</style>

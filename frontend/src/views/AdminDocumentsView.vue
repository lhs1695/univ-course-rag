<template>
  <div class="page">
    <header class="page-heading"><p class="eyebrow">管理 / 课程资料</p><h1>启用资料检索</h1><p class="page-description">教师上传后默认待启用。核对资料，再启用检索；停用后检索与课程调查均不再引用。</p></header>
    <section class="panel-card" v-loading="busy">
      <div class="admin-document-toolbar">
      <el-select v-model="courseId" aria-label="选择课程" style="width:260px" :disabled="busy"><el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.id" /></el-select>
      <el-select v-model="retrievalFilter" aria-label="筛选检索状态" style="width:180px"><el-option label="全部检索状态" value="all"/><el-option label="待启用 / 已停用" value="disabled"/><el-option label="已启用" value="enabled"/></el-select>
      <span class="admin-document-count" role="status">{{ filteredDocuments.length }} 份资料</span>
      </div>
      <el-alert v-if="failure" :title="failure" type="error" :closable="false" />
      <el-table :data="filteredDocuments" :empty-text="documents.length ? '没有符合筛选条件的资料' : '本课暂无资料'">
        <el-table-column prop="filename" label="文件" min-width="200" />
        <el-table-column label="资料夹" min-width="130"><template #default="{row}">{{ row.folder_name || '课程根目录' }}</template></el-table-column>
        <el-table-column label="解析状态"><template #default="{row}">{{ {pending:'等待解析',running:'正在解析',succeeded:'已入库',failed:'解析失败'}[row.job_status] || row.job_status }}</template></el-table-column>
        <el-table-column label="检索" min-width="150"><template #default="{row}"><el-tag :type="row.retrieval_enabled ? 'success' : 'info'" effect="plain">{{ row.retrieval_enabled ? '已启用' : '待启用 / 已停用' }}</el-tag></template></el-table-column>
        <el-table-column label="操作" min-width="180"><template #default="{row}">
          <el-link :href="documentContentUrl(courseId, row, 1)" target="_blank" rel="noopener">打开原文</el-link>
          <el-button link type="primary" :disabled="busy" @click="toggle(row)">{{ row.retrieval_enabled ? '停用检索' : '启用检索' }}</el-button>
        </template></el-table-column>
      </el-table>
    </section>
  </div>
</template>
<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { api } from "../api";
import { documentContentUrl } from "../documentDisplay";
const courses = ref([]), courseId = ref(""), documents = ref([]), busy = ref(false), failure = ref("");
const retrievalFilter = ref('all');
const filteredDocuments = computed(() => documents.value.filter(row => retrievalFilter.value === 'all' || row.retrieval_enabled === (retrievalFilter.value === 'enabled')));
async function loadDocuments() {
  if (!courseId.value || busy.value) return;
  busy.value = true; failure.value = ""; documents.value = [];
  try { documents.value = await api(`/courses/${courseId.value}/documents`); } catch (error) { failure.value = error.message; } finally { busy.value = false; }
}
async function toggle(row) {
  if (busy.value) return;
  busy.value = true; failure.value = "";
  try { Object.assign(row, await api(`/courses/${courseId.value}/documents/${row.id}`, { method: "PATCH", json: { retrieval_enabled: !row.retrieval_enabled } })); } catch (error) { failure.value = error.message; } finally { busy.value = false; }
}
watch(courseId, loadDocuments);
onMounted(async () => { try { courses.value = await api("/admin/courses"); courseId.value = courses.value[0]?.id || ""; } catch (error) { failure.value = error.message; } });
</script>

<style scoped>
.admin-document-toolbar { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.admin-document-count { margin-left: auto; color: var(--text-muted); font-size: 12px; }
</style>

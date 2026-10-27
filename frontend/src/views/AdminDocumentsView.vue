<template>
  <div class="page">
    <header class="page-heading"><p class="eyebrow">管理 / 课程资料</p><h1>启用资料检索</h1><p class="page-description">教师上传后默认待启用。核对资料，再启用检索；停用后检索与课程调查均不再引用。</p></header>
    <section class="panel-card">
      <el-select v-model="courseId" aria-label="选择课程" style="width:260px" :disabled="busy"><el-option v-for="c in courses" :key="c.id" :label="c.title" :value="c.id" /></el-select>
      <el-button :loading="busy" @click="loadDocuments">刷新资料</el-button>
      <el-alert v-if="failure" :title="failure" type="error" :closable="false" />
      <el-table :data="documents" empty-text="本课暂无资料">
        <el-table-column prop="filename" label="文件" />
        <el-table-column label="资料夹"><template #default="{row}">{{ row.folder_name || '未分组' }}</template></el-table-column>
        <el-table-column label="解析状态"><template #default="{row}">{{ {pending:'等待解析',running:'正在解析',succeeded:'已入库',failed:'解析失败'}[row.job_status] || row.job_status }}</template></el-table-column>
        <el-table-column label="检索"><template #default="{row}">{{ row.retrieval_enabled ? '已启用' : '待启用 / 已停用' }}</template></el-table-column>
        <el-table-column label="操作" min-width="180"><template #default="{row}">
          <el-link :href="documentContentUrl(courseId, row, 1)" target="_blank" rel="noopener">打开原文</el-link>
          <el-button link type="primary" :disabled="busy" @click="toggle(row)">{{ row.retrieval_enabled ? '停用检索' : '启用检索' }}</el-button>
        </template></el-table-column>
      </el-table>
    </section>
  </div>
</template>
<script setup>
import { onMounted, ref, watch } from "vue";
import { api } from "../api";
import { documentContentUrl } from "../documentDisplay";
const courses = ref([]), courseId = ref(""), documents = ref([]), busy = ref(false), failure = ref("");
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

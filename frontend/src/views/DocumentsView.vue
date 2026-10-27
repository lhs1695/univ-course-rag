<template>
  <StudentDocuments v-if="session.user?.role === 'student'" :documents="documents" :folders="folders" :loading="loading" :failure="failure" :course-id="courseId" @refresh="refreshDocuments" />
  <div v-else class="page">
    <header class="page-heading"><p class="eyebrow">教学 / 课程资源</p><h1>课程资料</h1><p class="page-description">整理本课资料，检查入库与检索状态，打开原文核对。</p></header>

    <div class="doc-actions">
      <template v-if="canManage">
        <el-button :disabled="folderBusy" @click="createFolder()">新建根资料夹</el-button>
        <label for="upload-folder">上传到</label>
        <el-select id="upload-folder" v-model="uploadFolderId" :disabled="uploading" aria-label="上传目标资料夹" style="width:220px">
          <el-option label="未分组" value="" />
          <el-option v-for="folder in folderChoices" :key="folder.id" :label="folder.label" :value="folder.id" />
        </el-select>
      </template>
      <el-upload
        v-if="canManage"
        :http-request="onUpload"
        :show-file-list="false"
        :disabled="uploading"
        accept=".pdf,.pptx,.docx,.md,.markdown,.txt,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/markdown,text/plain"
      >
        <el-button type="primary" :loading="uploading">上传资料</el-button>
      </el-upload>
      <el-button :loading="loading" @click="refreshDocuments">刷新资料列表</el-button>
    </div>

    <el-alert v-if="failure" :title="failure" type="error" :closable="false" />
    <template v-if="failedUpload">
      <p>{{ failedUpload.name }}：{{ uploadUncertain ? '上传结果未确认，请先刷新列表核对。' : '文件仍在本页内存中，可显式重新上传。' }}</p>
      <el-button :disabled="uploading || uploadUncertain" @click="retryUpload">重新上传所选文件</el-button>
    </template>

    <section v-for="group in groups" :key="group.id || 'ungrouped'" class="folder-group" :class="{ 'child-folder': group.parent_id }">
      <div class="folder-heading">
        <h2>{{ group.label }} <small>（{{ group.documents.length }}）</small></h2>
        <template v-if="canManage && group.name">
          <el-button v-if="!group.parent_id" link :disabled="folderBusy" @click="createFolder(group.id)">新建子夹</el-button>
          <el-button link :disabled="folderBusy" @click="renameFolder(group)">改名</el-button>
          <el-button link type="danger" :disabled="folderBusy || group.documents.length > 0 || folders.some(folder => folder.parent_id === group.id)" @click="deleteFolder(group)">删除空夹</el-button>
        </template>
      </div>
    <el-table class="docs-table" :data="group.documents" v-loading="loading" empty-text="此夹暂无资料" style="width: 100%">
      <el-table-column prop="filename" label="文件" min-width="160" class-name="filename-cell" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.job_status)">{{ statusLabel(row.job_status) }}</el-tag>
          <p v-if="row.job_status === 'failed'" class="job-failure">{{ jobFailure(row.error_message) }}</p>
        </template>
      </el-table-column>
      <el-table-column label="参与检索" width="120">
        <template #default="{ row }">
          <el-tag :type="row.retrieval_enabled ? 'success' : 'info'">
            {{ row.retrieval_enabled ? '启用' : '停用' }}
          </el-tag>
          <el-button v-if="canManage && (row.retrieval_enabled || session.user?.role === 'admin')" :disabled="busyIds.has(row.id)" link type="primary" :aria-label="`${row.retrieval_enabled ? '停用检索' : '启用检索'}：${row.filename}`" @click="onToggleRetrieval(row)">
            {{ row.retrieval_enabled ? '停用' : '启用' }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="打开" width="150">
        <template #default="{ row }">
          <div v-if="row.job_status === 'succeeded'" class="student-open">
            <label v-if="isPdfDocument(row)" :for="`document-page-${row.id}`">页码</label>
            <el-input
              v-if="isPdfDocument(row)"
              :id="`document-page-${row.id}`"
              v-model="pageSelections[row.id]"
              inputmode="numeric"
              @blur="correctPage(row)"
              @keydown.enter="correctPage(row)"
              size="small"
              class="page-input"
              :aria-label="`打开页码：${row.filename}`"
            />
            <el-link :href="studentOpenUrl(row)" :title="isPdfDocument(row) ? '将在新窗口打开 PDF' : '将在新窗口打开资料'" target="_blank" rel="noopener" type="primary" :aria-label="`打开资料：${row.filename}（新窗口）`" @click="openStudentDocument(row, $event)">
              打开
            </el-link>
          </div>
          <span v-else class="subtle">暂不可打开</span>
        </template>
      </el-table-column>
      <el-table-column v-if="canManage" label="维护" width="110">
        <template #default="{ row }">
          <el-button v-if="row.job_status === 'failed'" :disabled="busyIds.has(row.id)" type="primary" link @click="onRetry(row)">
            重试
          </el-button>
          <el-button :disabled="busyIds.has(row.id) || !row.retrieval_enabled" type="danger" link @click="onDelete(row)">移出检索</el-button>
        </template>
      </el-table-column>
      <el-table-column v-if="canManage" label="移动到" min-width="180">
        <template #default="{ row }">
          <el-select :model-value="row.folder_id || ''" :disabled="busyIds.has(row.id)" :aria-label="`移动资料：${row.filename}`" @change="moveDocument(row, $event)">
            <el-option label="未分组" value="" />
            <el-option v-for="folder in folderChoices" :key="folder.id" :label="folder.label" :value="folder.id" />
          </el-select>
        </template>
      </el-table-column>
    </el-table>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import StudentDocuments from "../components/StudentDocuments.vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";
import { session } from "../session";
import { courseAccess } from "../courseAccess";
import { clampDocumentPage, documentContentUrl, isPdfDocument } from "../documentDisplay";
import { documentGroups, folderOptions } from "../documentFolders";

const route = useRoute();
const courseId = computed(() => String(route.params.courseId));
const courseTitle = ref("");
const documents = ref([]);
const folders = ref([]);
const uploadFolderId = ref("");
const folderBusy = ref(false);
const folderChoices = computed(() => folderOptions(folders.value));
const groups = computed(() => documentGroups(documents.value, folders.value));
const loading = ref(true);
const uploading = ref(false);
const failure = ref("");
const failedUpload = ref(null);
const uploadUncertain = ref(false);
const busyIds = ref(new Set());
const pageSelections = ref({});
const canManage = computed(() => courseAccess.course?.capabilities.can_manage_documents);
let pollTimer = null;
let active = true;
let fetchingDocuments = false;

function correctPage(row) {
  const raw = pageSelections.value[row.id];
  const page = clampDocumentPage(raw, row);
  pageSelections.value[row.id] = String(page);
  const entered = Number.parseInt(raw, 10);
  if (entered < 1 || entered > row.source_unit_count) {
    ElMessage.info(entered < 1 ? "页码已按第一页打开" : "页码已按最后一页打开");
  }
}

function studentOpenUrl(row) {
  return documentContentUrl(courseId.value, row, pageSelections.value[row.id] ?? 1);
}

function openStudentDocument(row, event) {
  if (!isPdfDocument(row)) return;
  correctPage(row);
  event.preventDefault();
  window.open(studentOpenUrl(row), "_blank", "noopener");
}

function jobFailure(code) {
  if (code === "UPSTREAM_TIMEOUT") return "向量服务超时，可显式重试入库。";
  if (code === "UPSTREAM_UNAVAILABLE") return "向量服务暂时不可用，请稍后重试。";
  if (code === "no extractable text") return "没有可抽取文本，请核对扫描件或空文件。";
  if (String(code).includes("resource limit")) return "资料超过解析资源限制，请拆分后上传。";
  return "资料解析或入库失败，请核对文件；可重试或联系管理员。";
}

function statusType(status) {
  if (status === "succeeded") {
    return "success";
  }
  if (status === "failed") {
    return "danger";
  }
  if (status === "running") {
    return "warning";
  }
  return "info";
}

function statusLabel(status) {
  const labels = {
    pending: "处理中",
    running: "处理中",
    succeeded: "已入库",
    failed: "暂不可用",
  };
  return labels[status] || status;
}

function needsPoll(rows) {
  return rows.some((row) => row.job_status === "pending" || row.job_status === "running");
}

async function loadDocuments() {
  if (fetchingDocuments || !active) return false;
  fetchingDocuments = true;
  let rows;
  try {
    const result = await Promise.all([
      api(`/courses/${courseId.value}/documents`),
      api(`/courses/${courseId.value}/folders`),
    ]);
    rows = result[0];
    if (active) {
      folders.value = result[1];
      if (!folders.value.some(folder => folder.id === uploadFolderId.value)) uploadFolderId.value = "";
    }
  }
  finally { fetchingDocuments = false; }
  if (!active) return false;
  documents.value = rows;
  for (const row of rows) {
    if (isPdfDocument(row) && pageSelections.value[row.id] == null) {
      pageSelections.value[row.id] = 1;
    }
  }
  if (needsPoll(documents.value)) {
    startPoll();
  } else {
    stopPoll();
  }
  return true;
}

async function refreshDocuments() {
  loading.value = true;
  try {
    if (await loadDocuments()) {
      failure.value = "";
      uploadUncertain.value = false;
    }
  } catch (error) { failure.value = error.message; }
  finally { loading.value = false; }
}

function startPoll() {
  if (pollTimer) {
    return;
  }
  pollTimer = window.setInterval(async () => {
    try {
      await loadDocuments();
    } catch (error) {
      failure.value = error.message;
      stopPoll();
    }
  }, 1500);
}

function stopPoll() {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

onMounted(async () => {
  try {
    const course = await api(`/courses/${courseId.value}`);
    courseTitle.value = course.title;
    await loadDocuments();
  } catch (error) {
    failure.value = error.message;
    if (error.status !== 401) ElMessage.error(error.message);
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  active = false;
  stopPoll();
});

async function onUpload({ file }) {
  if (uploading.value) return;
  uploading.value = true;
  const formData = new FormData();
  formData.append("file", file);
  if (uploadFolderId.value) formData.append("folder_id", uploadFolderId.value);
  try {
    await api(`/courses/${courseId.value}/documents`, { method: "POST", formData });
    failedUpload.value = null;
    uploadUncertain.value = false;
    failure.value = "";
    ElMessage.success("已提交入库，待管理员启用检索");
  } catch (error) {
    failedUpload.value = file;
    uploadUncertain.value = error.status === 0;
    failure.value = error.message;
    if (error.status !== 401) ElMessage.error(error.message);
  } finally {
    uploading.value = false;
  }
  // A later list failure must not turn an accepted upload into a retryable upload.
  if (!failedUpload.value) await refreshDocuments();
}

async function retryUpload() {
  if (!failedUpload.value || uploadUncertain.value || uploading.value) return;
  if (documents.value.some(row => row.filename === failedUpload.value.name)) {
    failure.value = "列表已有同名资料，请先核对；本次未重复上传。";
    return;
  }
  await onUpload({ file: failedUpload.value });
}

async function onDelete(row) {
  if (busyIds.value.has(row.id)) return;
  busyIds.value.add(row.id);
  try {
    await ElMessageBox.confirm(
      `将「${row.filename}」移出检索？原文与入库记录保留，本课问答和调查将不再引用；管理员可以重新启用。`,
      "移出检索",
      {
        type: "warning",
        confirmButtonText: "移出检索",
        cancelButtonText: "取消",
      },
    );
  } catch {
    busyIds.value.delete(row.id);
    return;
  }
  try {
    await api(`/courses/${courseId.value}/documents/${row.id}`, { method: "DELETE" });
    ElMessage.success("已移出检索，保留原文与入库记录");
    await loadDocuments();
  } catch (error) {
    failure.value = error.message;
    if (error.status !== 401) ElMessage.error(error.message);
  } finally {
    busyIds.value.delete(row.id);
  }
}

async function onToggleRetrieval(row) {
  if (busyIds.value.has(row.id)) return;
  busyIds.value.add(row.id);
  try {
    const updated = await api(`/courses/${courseId.value}/documents/${row.id}`, {
      method: "PATCH", json: { retrieval_enabled: !row.retrieval_enabled },
    });
    Object.assign(row, updated);
    failure.value = "";
    ElMessage.success(updated.retrieval_enabled ? "已启用检索" : "已停用检索，原文仍可预览");
  } catch (error) {
    failure.value = error.message;
    if (error.status !== 401) ElMessage.error(error.message);
  } finally {
    busyIds.value.delete(row.id);
  }
}

async function onRetry(row) {
  if (busyIds.value.has(row.id)) return;
  busyIds.value.add(row.id);
  try {
    await api(`/courses/${courseId.value}/documents/${row.id}/retry`, { method: "POST" });
    ElMessage.success("已重新提交入库");
    await loadDocuments();
  } catch (error) {
    failure.value = error.message;
    if (error.status !== 401) ElMessage.error(error.message);
  } finally {
    busyIds.value.delete(row.id);
  }
}

async function editFolder(action) {
  if (folderBusy.value) return;
  folderBusy.value = true;
  try {
    await action();
    await refreshDocuments();
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') failure.value = error.message;
  } finally { folderBusy.value = false; }
}

function createFolder(parentId = null) {
  return editFolder(async () => {
    const { value } = await ElMessageBox.prompt('资料夹名称（最多 100 字）', parentId ? '新建子夹' : '新建根资料夹', {
      inputValidator: value => Boolean(value?.trim() && value.trim().length <= 100) || '请输入 1～100 字名称',
    });
    await api(`/courses/${courseId.value}/folders`, { method: 'POST', json: { name: value.trim(), parent_id: parentId } });
  });
}

function renameFolder(folder) {
  return editFolder(async () => {
    const { value } = await ElMessageBox.prompt('资料夹名称（最多 100 字）', '资料夹改名', {
      inputValue: folder.name,
      inputValidator: value => Boolean(value?.trim() && value.trim().length <= 100) || '请输入 1～100 字名称',
    });
    await api(`/courses/${courseId.value}/folders/${folder.id}`, { method: 'PATCH', json: { name: value.trim() } });
  });
}

function deleteFolder(folder) {
  return editFolder(async () => {
    await ElMessageBox.confirm(`删除空资料夹「${folder.label}」？`, '删除资料夹', { type: 'warning' });
    await api(`/courses/${courseId.value}/folders/${folder.id}`, { method: 'DELETE' });
  });
}

async function moveDocument(row, folderId) {
  if (busyIds.value.has(row.id)) return;
  busyIds.value.add(row.id);
  try {
    Object.assign(row, await api(`/courses/${courseId.value}/documents/${row.id}`, {
      method: 'PATCH', json: { folder_id: folderId || null },
    }));
    failure.value = '';
  } catch (error) { failure.value = error.message; }
  finally { busyIds.value.delete(row.id); }
}
</script>

<style scoped>
.doc-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px;
  padding: 18px 20px;
  flex-wrap: wrap;
  background: var(--surface);
  border: 1px solid var(--line);
  border-radius: var(--radius-panel);
}

.doc-actions .el-button + .el-button { margin-left: 0; }


:deep(.filename-cell .cell) { color: var(--text-strong); font-weight: 600; overflow-wrap: anywhere; }
.job-failure { margin: 6px 0 0; font-size: 12px; line-height: 1.4; color: var(--el-color-danger); }
.student-open { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.student-open .el-link { font-weight: 600; }
.page-input { width: 48px; }
.subtle { font-size: 12px; color: var(--text-muted); }

.docs-table { width: 100%; }
.folder-group { margin-bottom: 24px; }
.folder-heading { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.folder-heading h2 { font-size: 18px; overflow-wrap: anywhere; }
.folder-heading small { color: var(--text-muted); font-weight: normal; }
.child-folder { margin-left: 18px; }
/* Preserve horizontal access to every column on narrow screens. */
:deep(.docs-table .el-scrollbar__wrap) { overflow-x: auto; }
</style>

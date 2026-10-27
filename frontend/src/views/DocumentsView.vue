<template>
  <StudentDocuments v-if="session.user?.role === 'student'" :documents="documents" :folders="folders" :loading="loading" :failure="failure" :course-id="courseId" />
  <div v-else class="page">
    <header class="page-heading"><p class="eyebrow">教学 / 课程资源</p><h1>课程资料</h1><p class="page-description">整理本课资料，检查入库与检索状态，打开原文核对。</p></header>

    <FolderLibrary v-model="selectedFolderId" v-model:search="search" :documents="documents" :folders="folders" :loading="loading">
      <template #actions><el-button v-if="canManage" :disabled="folderBusy" @click="openFolderDialog('create')">新建资料夹</el-button></template>
      <template #default="{ group }">
      <div class="folder-heading">
        <div><p class="eyebrow">{{ search.trim() ? '整课文件名匹配' : '课程资料目录' }}</p><h2>{{ group.label }}</h2></div>
        <div v-if="canManage && currentFolder && !search.trim()" class="folder-controls">
          <el-button v-if="!currentFolder.parent_id" link :disabled="folderBusy" @click="openFolderDialog('create', currentFolder)">新建子夹</el-button>
          <el-button link :disabled="folderBusy" @click="openFolderDialog('rename', currentFolder)">改名</el-button>
          <el-button link :disabled="folderBusy" @click="openFolderDialog('move', currentFolder)">更换父级</el-button>
          <el-tooltip content="仅能删除没有子夹和资料的空夹" :disabled="!currentFolderNonempty">
            <span><el-button link type="danger" :disabled="folderBusy || currentFolderNonempty" @click="deleteFolder(currentFolder)">删除空夹</el-button></span>
          </el-tooltip>
        </div>
      </div>
    <div class="doc-actions">
      <span v-if="canManage" class="upload-destination">上传到：{{ selectedFolderLabel }}</span>
      <el-upload
        v-if="canManage"
        :http-request="onUpload"
        :show-file-list="false"
        :disabled="uploading"
        accept=".pdf,.pptx,.docx,.md,.markdown,.txt,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/markdown,text/plain"
      >
        <el-button type="primary" :loading="uploading" :aria-label="`上传资料到${selectedFolderLabel}`">上传资料</el-button>
      </el-upload>
    </div>

    <el-alert v-if="failure" :title="failure" type="error" :closable="false" />
    <template v-if="failedUpload">
      <p>{{ failedUpload.name }}：{{ uploadUncertain ? '上传结果未确认，请重新进入本页核对后再试。' : '文件仍在本页内存中，可显式重新上传。' }}</p>
      <el-button :disabled="uploading || uploadUncertain" @click="retryUpload">重新上传所选文件</el-button>
    </template>

    <el-table class="docs-table" :data="group.documents" v-loading="loading" empty-text="此夹暂无资料" style="width: 100%">
      <template #empty><el-empty :description="loading ? '正在加载资料…' : search.trim() ? '本课没有匹配资料' : '暂无资料'" :image-size="72"><p class="subtle">{{ search.trim() ? '试试更短的文件名关键词。' : canManage ? '上传资料到当前夹，或从其他资料夹移动过来。' : '请稍后重新进入本页查看。' }}</p><p v-if="!search.trim() && group.id && !group.parent_id && folders.some(folder => folder.parent_id === group.id)" class="subtle">子夹内容请在左侧目录中选择查看。</p><el-button v-if="search.trim()" @click="search = ''">清空搜索</el-button></el-empty></template>
      <el-table-column label="文件" min-width="210" class-name="filename-cell">
        <template #default="{ row }"><div class="document-name">{{ row.filename }}<el-tag v-if="!row.retrieval_enabled" type="info" size="small" effect="plain">待启用</el-tag></div><p class="document-location">{{ folderChoices.find(folder => folder.id === row.folder_id)?.label || row.folder_name || '课程根目录' }}</p></template>
      </el-table-column>
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.job_status)">{{ statusLabel(row.job_status) }}</el-tag>
          <p v-if="row.job_status === 'failed'" class="job-failure">{{ jobFailure(row.error_message) }}</p>
        </template>
      </el-table-column>
      <el-table-column label="阅读与下载" width="200">
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
            <a :href="documentDownloadUrl(courseId, row)" :download="row.filename" class="document-download" :aria-label="`下载资料：${row.filename}`">下载</a>
          </div>
          <span v-else class="subtle">暂不可打开</span>
        </template>
      </el-table-column>
      <el-table-column v-if="canManage" label="维护" width="86" align="right">
        <template #default="{ row }">
          <el-dropdown trigger="click" :disabled="busyIds.has(row.id)" @command="command => onDocumentAction(command, row)">
            <el-button link :disabled="busyIds.has(row.id)" :aria-label="`维护资料：${row.filename}`">更多 ···</el-button>
            <template #dropdown><el-dropdown-menu>
              <el-dropdown-item command="move">移动资料</el-dropdown-item>
              <el-dropdown-item v-if="row.job_status === 'failed'" command="retry">重试入库</el-dropdown-item>
              <el-dropdown-item v-if="row.retrieval_enabled" command="disable" divided>移出检索</el-dropdown-item>
            </el-dropdown-menu></template>
          </el-dropdown>
        </template>
      </el-table-column>
    </el-table>
      </template>
    </FolderLibrary>

    <el-dialog v-model="folderDialog.visible" :title="folderDialogTitle" width="min(480px, 92vw)" :close-on-click-modal="false" :before-close="closeFolderDialog">
      <el-form label-position="top" @submit.prevent="saveFolder">
        <el-form-item v-if="folderDialog.mode !== 'move'" label="资料夹名称" :error="folderDialog.error">
          <el-input v-model="folderDialog.name" :disabled="folderBusy" maxlength="100" show-word-limit placeholder="例如：第一章 课程讲义" aria-label="资料夹名称" />
        </el-form-item>
        <p v-else class="dialog-description">为「{{ folderDialog.folder?.name }}」选择新的父级，夹内资料保持归属。</p>
        <el-form-item v-if="folderDialog.mode !== 'rename'" label="父级资料夹">
          <el-tree-select v-model="folderDialog.parentId" :data="parentTargets" node-key="value" :empty-values="[null, undefined]" check-strictly default-expand-all :render-after-expand="false" :disabled="folderBusy" aria-label="父级资料夹" style="width:100%" />
        </el-form-item>
        <p v-if="folderDialog.mode !== 'rename'" class="subtle">{{ folderDialogHasChildren ? '此夹含子夹，须保留在根目录。' : '选择根目录，或放入一个根资料夹。' }}</p>
        <el-alert v-if="folderDialog.failure" :title="folderDialog.failure" type="error" :closable="false" />
      </el-form>
      <template #footer><el-button :disabled="folderBusy" @click="folderDialog.visible = false">取消</el-button><el-button type="primary" :loading="folderBusy" @click="saveFolder">{{ folderDialog.mode === 'create' ? '创建资料夹' : '保存' }}</el-button></template>
    </el-dialog>

    <el-dialog v-model="documentMove.visible" title="移动资料" width="min(480px, 92vw)" :close-on-click-modal="false" :before-close="closeDocumentMove">
      <p class="dialog-description">将「{{ documentMove.row?.filename }}」从「{{ documentMove.source }}」移动到：</p>
      <el-tree-select v-model="documentMove.targetId" :data="documentTargets" node-key="value" :empty-values="[null, undefined]" check-strictly default-expand-all :render-after-expand="false" :disabled="documentMoving" aria-label="移动目标资料夹" style="width:100%" />
      <p class="subtle">仅调整资料归属，入库和检索状态保持不变。</p>
      <el-alert v-if="documentMove.failure" :title="documentMove.failure" type="error" :closable="false" />
      <template #footer><el-button :disabled="documentMoving" @click="documentMove.visible = false">取消</el-button><el-button type="primary" :loading="documentMoving" :disabled="documentMove.targetId === (documentMove.row?.folder_id || '')" @click="moveDocument">确认移动</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import StudentDocuments from "../components/StudentDocuments.vue";
import FolderLibrary from "../components/FolderLibrary.vue";
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";
import { session } from "../session";
import { courseAccess } from "../courseAccess";
import { clampDocumentPage, documentContentUrl, documentDownloadUrl, isPdfDocument } from "../documentDisplay";
import { documentFolderTargets, folderOptions, folderParentOptions } from "../documentFolders";

const route = useRoute();
const courseId = computed(() => String(route.params.courseId));
const courseTitle = ref("");
const documents = ref([]);
const folders = ref([]);
const selectedFolderId = ref(null);
const search = ref('');
const folderBusy = ref(false);
const folderChoices = computed(() => folderOptions(folders.value));
const selectedFolderLabel = computed(() => folderChoices.value.find(folder => folder.id === selectedFolderId.value)?.label || '课程根目录');
const currentFolder = computed(() => folders.value.find(folder => folder.id === selectedFolderId.value));
const currentFolderNonempty = computed(() => currentFolder.value && (
  documents.value.some(doc => doc.folder_id === currentFolder.value.id) ||
  folders.value.some(folder => folder.parent_id === currentFolder.value.id)
));
const folderDialog = ref({ visible: false, mode: 'create', folder: null, name: '', parentId: '', error: '', failure: '' });
const folderDialogTitle = computed(() => ({ create: '新建资料夹', rename: '资料夹改名', move: '更换父级' })[folderDialog.value.mode]);
const folderDialogHasChildren = computed(() => folderDialog.value.folder && folders.value.some(folder => folder.parent_id === folderDialog.value.folder.id));
const parentTargets = computed(() => [
  { value: '', label: '根目录' },
  ...folderParentOptions(folders.value, folderDialog.value.mode === 'move' ? folderDialog.value.folder : null).map(folder => ({ value: folder.id, label: folder.name })),
]);
const documentTargets = computed(() => documentFolderTargets(folders.value));
const documentMove = ref({ visible: false, row: null, targetId: '', source: '', failure: '' });
const documentMoving = computed(() => busyIds.value.has(documentMove.value.row?.id));
const loading = ref(true);
const uploading = ref(false);
const failure = ref("");
const failedUpload = ref(null);
const failedUploadFolderId = ref(null);
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
      if (!folders.value.some(folder => folder.id === selectedFolderId.value)) selectedFolderId.value = null;
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

async function onUpload({ file }, folderId = selectedFolderId.value) {
  if (uploading.value) return;
  uploading.value = true;
  const formData = new FormData();
  formData.append("file", file);
  if (folderId) formData.append("folder_id", folderId);
  try {
    await api(`/courses/${courseId.value}/documents`, { method: "POST", formData });
    failedUpload.value = null;
    uploadUncertain.value = false;
    failure.value = "";
    ElMessage.success("已提交入库，待管理员启用检索");
  } catch (error) {
    failedUpload.value = file;
    failedUploadFolderId.value = folderId;
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
  await onUpload({ file: failedUpload.value }, failedUploadFolderId.value);
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

function onDocumentAction(command, row) {
  if (busyIds.value.has(row.id)) return;
  if (command === 'move') openDocumentMove(row);
  if (command === 'retry') return onRetry(row);
  if (command === 'disable' && row.retrieval_enabled) return onDelete(row);
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

function openFolderDialog(mode, folder = null) {
  if (folderBusy.value) return;
  folderDialog.value = {
    visible: true, mode, folder: mode === 'create' ? null : folder,
    name: mode === 'create' ? '' : folder.name,
    parentId: mode === 'create' ? (folder?.id || '') : (folder.parent_id || ''),
    error: '', failure: '',
  };
}

function closeFolderDialog(done) { if (!folderBusy.value) done(); }
function closeDocumentMove(done) { if (!documentMoving.value) done(); }

async function saveFolder() {
  if (folderBusy.value) return;
  const dialog = folderDialog.value;
  dialog.error = '';
  dialog.failure = '';
  if (dialog.mode !== 'move' && !dialog.name.trim()) {
    dialog.error = '请输入 1～100 字名称';
    return;
  }
  folderBusy.value = true;
  try {
    const json = dialog.mode === 'move' ? { parent_id: dialog.parentId || null } : { name: dialog.name.trim() };
    if (dialog.mode === 'create') json.parent_id = dialog.parentId || null;
    const saved = await api(`/courses/${courseId.value}/folders${dialog.mode === 'create' ? '' : '/' + dialog.folder.id}`, {
      method: dialog.mode === 'create' ? 'POST' : 'PATCH', json,
    });
    // Update the local snapshot before refreshing so the new selection exists immediately.
    folders.value = [...folders.value.filter(folder => folder.id !== saved.id), saved];
    selectedFolderId.value = saved.id;
    search.value = '';
    dialog.visible = false;
    ElMessage.success(dialog.mode === 'create' ? '资料夹已创建' : '资料夹已更新');
    await refreshDocuments();
  } catch (error) {
    dialog.failure = error.status === 409 ? '该父级下已有同名资料夹，请修改名称或选择其他父级。' : error.message;
  } finally { folderBusy.value = false; }
}

async function deleteFolder(folder) {
  if (folderBusy.value) return;
  folderBusy.value = true;
  try {
    await ElMessageBox.confirm(`删除空资料夹「${folder.name}」？`, '删除资料夹', {
      type: 'warning', confirmButtonText: '删除空夹', cancelButtonText: '取消',
    });
    await api(`/courses/${courseId.value}/folders/${folder.id}`, { method: 'DELETE' });
    folders.value = folders.value.filter(item => item.id !== folder.id);
    selectedFolderId.value = folder.parent_id;
    ElMessage.success('空资料夹已删除');
    await refreshDocuments();
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      failure.value = error.status === 409 ? '资料夹仍有子夹或资料，请先移出后再删除。' : error.message;
    }
  } finally { folderBusy.value = false; }
}

function openDocumentMove(row) {
  documentMove.value = {
    visible: true, row, targetId: row.folder_id || '', failure: '',
    source: folderChoices.value.find(folder => folder.id === row.folder_id)?.label || row.folder_name || '课程根目录',
  };
}

async function moveDocument() {
  const dialog = documentMove.value;
  const row = dialog.row;
  if (!row || busyIds.value.has(row.id)) return;
  busyIds.value.add(row.id);
  dialog.failure = '';
  try {
    const updated = await api(`/courses/${courseId.value}/documents/${row.id}`, {
      method: 'PATCH', json: { folder_id: dialog.targetId || null },
    });
    // Polling can replace the list while this dialog is open; update the current snapshot.
    documents.value = documents.value.map(document => document.id === updated.id ? updated : document);
    selectedFolderId.value = updated.folder_id;
    search.value = '';
    dialog.visible = false;
    failure.value = '';
    ElMessage.success('资料已移动，正在查看目标资料夹');
  } catch (error) { dialog.failure = error.message; }
  finally { busyIds.value.delete(row.id); }
}
</script>

<style scoped>
.doc-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 16px 0;
  padding: 0;
  flex-wrap: wrap;
  background: var(--surface);

}

.doc-actions .el-button + .el-button { margin-left: 0; }


:deep(.filename-cell .cell) { color: var(--text-strong); font-weight: 600; overflow-wrap: anywhere; }
.job-failure { margin: 6px 0 0; font-size: 12px; line-height: 1.4; color: var(--el-color-danger); }
.student-open { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.student-open .el-link { font-weight: 600; }
.document-download { color: var(--el-color-primary); font-size: 13px; }
.document-download:hover { text-decoration: underline; }
.document-name { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.document-location { margin: 4px 0 0; color: var(--text-muted); font-weight: 400; font-size: 12px; }
.page-input { width: 48px; }
.subtle { font-size: 12px; color: var(--text-muted); }

.docs-table { width: 100%; }
.folder-controls { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.upload-destination { color: var(--text-muted); font-size: 13px; overflow-wrap: anywhere; }
.dialog-description { overflow-wrap: anywhere; line-height: 1.7; }
.folder-heading { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.folder-heading h2 { margin: 4px 0 0; font-size: 18px; overflow-wrap: anywhere; }

/* Preserve horizontal access to every column on narrow screens. */
:deep(.docs-table .el-scrollbar__wrap) { overflow-x: auto; }
</style>

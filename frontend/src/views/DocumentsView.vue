<template>
  <StudentDocuments v-if="session.user?.role === 'student'" :documents="documents" :loading="loading" :failure="failure" :course-id="courseId" @refresh="refreshDocuments" />
  <div v-else class="page">
    <header class="page-heading"><p class="eyebrow">课程资源</p><h1>课程资料</h1></header>

    <div class="doc-actions">
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

    <el-table :data="documents" v-loading="loading" empty-text="还没有资料">
      <el-table-column prop="filename" label="文件" min-width="220" class-name="filename-cell" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.job_status)">{{ statusLabel(row.job_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="失败原因" min-width="240">
        <template #default="{ row }">
          {{ row.job_status === "failed" ? jobFailure(row.error_message) : "—" }}
        </template>
      </el-table-column>
      <el-table-column label="参与问答检索" min-width="200">
        <template #default="{ row }">
          <el-tag :type="row.retrieval_enabled ? 'success' : 'info'">
            {{ row.retrieval_enabled ? '已启用' : '已停用 · 仍可预览' }}
          </el-tag>
          <el-button v-if="canManage" :disabled="busyIds.has(row.id)" link type="primary" :aria-label="`${row.retrieval_enabled ? '停用检索' : '启用检索'}：${row.filename}`" @click="onToggleRetrieval(row)">
            {{ row.retrieval_enabled ? '停用检索' : '启用检索' }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="入库质量" min-width="260">
        <template #default="{ row }">
          <template v-if="row.job_status === 'succeeded' && row.extracted_char_count != null">
            <div>
              {{ documentQualityLabel(row) }}
            </div>
            <el-tag
              v-if="documentCoverage(row).type === 'warning'"
              :type="documentCoverage(row).type"
              size="small"
              class="coverage-tag"
              style="margin-top: 6px"
            >
              {{ documentCoverage(row).label }}
            </el-tag>
            <p v-if="documentCoverageHint(row)" class="subtle" style="margin: 6px 0 0; line-height: 1.4">
              {{ documentCoverageHint(row) }}
            </p>
          </template>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="打开原文" min-width="280">
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
              {{ isPdfDocument(row) ? '打开 PDF' : '打开资料' }}
            </el-link>
            <small v-if="isPdfDocument(row)" class="subtle">新窗口打开，可调整页码</small>
          </div>
          <span v-else class="subtle">暂不可打开</span>
        </template>
      </el-table-column>
      <el-table-column v-if="canManage" label="维护" width="140">
        <template #default="{ row }">
          <el-button v-if="row.job_status === 'failed'" :disabled="busyIds.has(row.id)" type="primary" link @click="onRetry(row)">
            重试
          </el-button>
          <el-button :disabled="busyIds.has(row.id)" type="danger" link @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
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
import { clampDocumentPage, documentCoverage, documentCoverageHint, documentQualityLabel, documentContentUrl, isPdfDocument } from "../documentDisplay";

const route = useRoute();
const courseId = computed(() => String(route.params.courseId));
const courseTitle = ref("");
const documents = ref([]);
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
  try { rows = await api(`/courses/${courseId.value}/documents`); }
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
  try {
    await api(`/courses/${courseId.value}/documents`, { method: "POST", formData });
    failedUpload.value = null;
    uploadUncertain.value = false;
    failure.value = "";
    ElMessage.success("已提交入库");
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
      `删除资料「${row.filename}」后不可恢复，本课问答将失去该依据。`,
      "确认删除",
      {
        type: "warning",
        confirmButtonText: "删除",
        cancelButtonText: "取消",
      },
    );
  } catch {
    busyIds.value.delete(row.id);
    return;
  }
  try {
    await api(`/courses/${courseId.value}/documents/${row.id}`, { method: "DELETE" });
    ElMessage.success("已删除");
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
</script>

<style scoped>
.doc-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 16px;
  padding: 18px 20px;
  flex-wrap: wrap;
  background: #fff;
  border: 1px solid #e6ebe8;
  border-radius: 12px;
}

.doc-actions .el-button + .el-button { margin-left: 0; }


:deep(.filename-cell .cell) { color: #29463d; font-weight: 600; }
.student-open { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.student-open small { flex-basis: 100%; }
.student-open .el-link { font-weight: 600; }
.page-input { width: 118px; }
.subtle { font-size: 12px; color: var(--text-muted); }
</style>

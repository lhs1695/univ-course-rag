<template>
  <div class="page">
    <header class="page-heading"><p class="eyebrow">课程资源</p><h1>课程资料</h1><p class="page-description">{{ canManage ? '上传、检查入库状态，维护本课问答的资料依据。' : '只读查看本课资料；PDF 可输入页码后打开到对应页，回答引用也可回到原资料核对。' }}</p></header>

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
      <el-text v-if="canManage" type="info" size="small">
        支持 PDF、PPTX、DOCX、Markdown 和纯文本；不支持旧版 PPT/DOC
      </el-text>
      <el-button :loading="loading" @click="refreshDocuments">刷新资料列表</el-button>
    </div>

    <el-alert v-if="failure" :title="failure" type="error" :closable="false" />
    <template v-if="failedUpload">
      <p>{{ failedUpload.name }}：{{ uploadUncertain ? '上传结果未确认，请先刷新列表核对。' : '文件仍在本页内存中，可显式重新上传。' }}</p>
      <el-button :disabled="uploading || uploadUncertain" @click="retryUpload">重新上传所选文件</el-button>
    </template>

    <p v-if="canManage" class="scope-note">入库质量只说明文本是否被抽取和切片，不代表问答一定正确。文本较少的资料仍会保留，请结合引用核对原文。</p>

    <el-table v-if="!canManage" :data="documents" v-loading="loading" empty-text="本课还没有可查看的资料">
      <el-table-column prop="filename" label="文件名" min-width="220" class-name="filename-cell" />
      <el-table-column label="页数" width="100">
        <template #default="{ row }">{{ documentPageLabel(row) }}</template>
      </el-table-column>
      <el-table-column label="状态" width="130">
        <template #default="{ row }">
          <el-tag :type="documentCoverage(row).type">{{ documentCoverage(row).label }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="280">
        <template #default="{ row }">
          <div v-if="row.job_status === 'succeeded'" class="student-open">
            <el-input
              v-if="isPdfDocument(row)"
              v-model="pageSelections[row.id]"
              inputmode="numeric"
              @blur="correctPage(row)"
              @keydown.enter="correctPage(row)"
              size="small"
              class="page-input"
              :aria-label="`打开页码：${row.filename}`"
            />
            <el-link :href="studentOpenUrl(row)" :title="isPdfDocument(row) ? '将在新窗口打开 PDF' : '将在新窗口打开资料'" target="_blank" rel="noopener" type="primary" :aria-label="`打开资料：${row.filename}（新窗口）`" @click="openStudentDocument(row, $event)">
              {{ isPdfDocument(row) ? '打开该页 ↗' : '打开资料 ↗' }}
            </el-link>
            <small v-if="isPdfDocument(row)" class="subtle">页码范围看左侧页数；将在新窗口打开 PDF</small>
          </div>
          <span v-else class="subtle">暂不可打开</span>
        </template>
      </el-table-column>
    </el-table>

    <el-table v-else :data="documents" v-loading="loading" empty-text="还没有资料">
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
      <el-table-column label="入库质量" min-width="260">
        <template #default="{ row }">
          <template v-if="row.job_status === 'succeeded' && row.extracted_char_count != null">
            <div>
              {{ documentQualityLabel(row) }}
            </div>
            <el-text v-if="row.quality_warning === 'LOW_EXTRACTED_TEXT'" type="warning">
              抽取文本较少，问答依据可能不完整
            </el-text>
          </template>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="canManage" label="操作" width="140">
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
import { useRoute } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";
import { courseAccess } from "../courseAccess";
import { clampDocumentPage, documentQualityLabel, documentContentUrl, documentCoverage, documentPageLabel, isPdfDocument } from "../documentDisplay";

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
    pending: "等待中",
    running: "处理中",
    succeeded: "成功",
    failed: "失败",
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
    ElMessage.error(error.message);
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
    ElMessage.error(error.message);
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
    ElMessage.error(error.message);
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
    ElMessage.error(error.message);
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

.scope-note {
  margin: 16px 0;
  padding-left: 12px;
  border-left: 2px solid #c7d5d0;
  color: #65736e;
  font-size: 12px;
  line-height: 1.75;
}

:deep(.filename-cell .cell) { color: #29463d; font-weight: 600; }
.student-open { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.student-open .el-link { font-weight: 600; }
.page-input { width: 118px; }
.subtle { font-size: 12px; color: #65736e; }
</style>

<template>
  <div class="page">
    <el-page-header @back="router.push('/courses')">
      <template #content>{{ courseTitle || "资料" }}</template>
    </el-page-header>

    <div class="doc-actions">
      <el-upload
        v-if="canManage"
        :http-request="onUpload"
        :show-file-list="false"
        accept=".pdf,.pptx,.docx,.md,.markdown,.txt,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/markdown,text/plain"
      >
        <el-button type="primary" :loading="uploading">上传资料</el-button>
      </el-upload>
      <el-text v-if="canManage" type="info" size="small">
        支持 PDF、PPTX、DOCX、Markdown 和纯文本；不支持旧版 PPT/DOC
      </el-text>
      <el-button @click="router.push(`/courses/${courseId}`)">进入问答</el-button>
      <el-button v-if="canManage" text @click="router.push(`/courses/${courseId}/members`)">
        本课学生
      </el-button>
      <el-button v-if="canManage" text @click="router.push(`/courses/${courseId}/insights`)">学情</el-button>
    </div>

    <el-table :data="documents" v-loading="loading" empty-text="还没有资料">
      <el-table-column prop="filename" label="文件" min-width="180" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tag :type="statusType(row.job_status)">{{ statusLabel(row.job_status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="失败原因" min-width="240">
        <template #default="{ row }">
          {{ row.job_status === "failed" ? row.error_message || "入库失败" : "—" }}
        </template>
      </el-table-column>
      <el-table-column v-if="canManage" label="" width="100">
        <template #default="{ row }">
          <el-button type="danger" link @click="onDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";
import { session } from "../session";

const route = useRoute();
const router = useRouter();
const courseId = computed(() => String(route.params.courseId));
const courseTitle = ref("");
const documents = ref([]);
const loading = ref(true);
const uploading = ref(false);
const canManage = computed(() => session.user?.role === "teacher");
let pollTimer = null;

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
  documents.value = await api(`/courses/${courseId.value}/documents`);
  if (needsPoll(documents.value)) {
    startPoll();
  } else {
    stopPoll();
  }
}

function startPoll() {
  if (pollTimer) {
    return;
  }
  pollTimer = window.setInterval(async () => {
    try {
      await loadDocuments();
    } catch {
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
    ElMessage.error(error.message);
  } finally {
    loading.value = false;
  }
});

onUnmounted(() => {
  stopPoll();
});

async function onUpload({ file }) {
  uploading.value = true;
  const formData = new FormData();
  formData.append("file", file);
  try {
    await api(`/courses/${courseId.value}/documents`, { method: "POST", formData });
    ElMessage.success("已提交入库");
    await loadDocuments();
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    uploading.value = false;
  }
}

async function onDelete(row) {
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
    return;
  }
  try {
    await api(`/courses/${courseId.value}/documents/${row.id}`, { method: "DELETE" });
    ElMessage.success("已删除");
    await loadDocuments();
  } catch (error) {
    ElMessage.error(error.message);
  }
}
</script>

<style scoped>
.doc-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
  flex-wrap: wrap;
}
</style>

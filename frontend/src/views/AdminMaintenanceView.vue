<template>
  <div class="page">
    <h2>提问日志维护</h2>
    <el-alert
      title="提问日志包含问题原文，只用于留存窗口内的课程学情。维护操作不会展示问题或提问者。"
      type="info"
      :closable="false"
      show-icon
    />

    <el-card class="maintenance-card" shadow="never">
      <template #header>到期记录</template>
      <p class="explanation">
        先预览当前最旧的一批，再显式删除。每次操作受服务器批量上限约束，不会扫描或一次删除全部记录。
      </p>

      <el-descriptions v-if="result" :column="2" border class="result-grid">
        <el-descriptions-item label="留存窗口">{{ result.retention_days }} 天</el-descriptions-item>
        <el-descriptions-item label="单批上限">{{ result.batch_limit }} 条</el-descriptions-item>
        <el-descriptions-item :label="result.mode === 'delete' ? '上次删除' : '本批到期'">
          {{ result.mode === "delete" ? result.deleted_count : result.matched_count }} 条
        </el-descriptions-item>
        <el-descriptions-item label="仍有下一批">{{ result.has_more ? "是" : "否" }}</el-descriptions-item>
      </el-descriptions>

      <div class="maintenance-actions">
        <el-button type="primary" plain :loading="previewing" @click="previewExpired">
          {{ result?.mode === "delete" && result.has_more ? "预览下一批" : "预览到期记录" }}
        </el-button>
        <el-button
          v-if="previewReady"
          type="danger"
          :loading="deleting"
          :disabled="!result?.matched_count"
          @click="deleteExpired"
        >
          删除本批 {{ result?.matched_count || 0 }} 条
        </el-button>
      </div>
    </el-card>

    <el-alert
      title="这里只删除当前应用数据库中的记录，不能立即从已有备份、快照或其他外部副本中抹除。"
      type="warning"
      :closable="false"
      show-icon
    />
  </div>
</template>

<script setup>
import { ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { api } from "../api";

const result = ref(null);
const previewReady = ref(false);
const previewing = ref(false);
const deleting = ref(false);

async function previewExpired() {
  previewing.value = true;
  try {
    result.value = await api("/admin/query-logs/retention", {
      method: "POST",
      json: { mode: "dry_run" },
    });
    previewReady.value = true;
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    previewing.value = false;
  }
}

async function deleteExpired() {
  const count = result.value?.matched_count || 0;
  if (!previewReady.value || !count) {
    return;
  }
  try {
    await ElMessageBox.confirm(
      `将删除当前数据库中最旧的 ${count} 条到期提问日志。该操作不能撤销，也不会同步删除外部备份。`,
      "确认删除本批日志",
      {
        type: "warning",
        confirmButtonText: "删除本批",
        cancelButtonText: "取消",
      },
    );
  } catch {
    return;
  }

  deleting.value = true;
  try {
    result.value = await api("/admin/query-logs/retention", {
      method: "POST",
      json: { mode: "delete" },
    });
    previewReady.value = false;
    ElMessage.success(`已删除 ${result.value.deleted_count} 条到期日志`);
  } catch (error) {
    ElMessage.error(error.message);
  } finally {
    deleting.value = false;
  }
}
</script>

<style scoped>
.maintenance-card {
  margin: 16px 0;
}

.explanation {
  margin: 0 0 16px;
  color: #606266;
  font-size: 14px;
  line-height: 1.6;
}

.result-grid {
  margin-bottom: 16px;
}

.maintenance-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>

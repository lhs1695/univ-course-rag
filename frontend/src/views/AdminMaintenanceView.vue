<template>
  <div class="page">
    <header class="page-heading"><h1>提问日志</h1></header>

    <el-card class="maintenance-card panel-card" shadow="never">
      <template #header>日志清理</template>

      <el-descriptions v-if="result" :column="2" border class="result-grid">
        <el-descriptions-item label="保留最近">{{ result.retention_days }} 天</el-descriptions-item>
        <el-descriptions-item :label="result.mode === 'delete' ? '本批已删除' : '本批到期'">
          {{ result.mode === "delete" ? result.deleted_count : result.matched_count }} 条
        </el-descriptions-item>
        <el-descriptions-item v-if="result.has_more" label="后续记录">还有</el-descriptions-item>
      </el-descriptions>
      <p v-if="previewReady && !result?.matched_count" class="empty-expired">没有到期记录</p>

      <div class="maintenance-actions">
        <el-button type="primary" plain :loading="previewing" @click="previewExpired">
          {{ result?.mode === "delete" && result.has_more ? "预览下一批" : "预览到期" }}
        </el-button>
        <el-button
          v-if="previewReady && result?.matched_count"
          type="danger"
          :loading="deleting"
          :disabled="!result?.matched_count"
          @click="deleteExpired"
        >
          删除本批 {{ result?.matched_count || 0 }} 条
        </el-button>
      </div>
    </el-card>
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
  if (previewing.value || deleting.value) return;
  previewing.value = true;
  try {
    result.value = await api("/admin/query-logs/retention", {
      method: "POST",
      json: { mode: "dry_run" },
    });
    previewReady.value = true;
  } catch (error) {
    if (error.status !== 401) ElMessage.error(error.message);
  } finally {
    previewing.value = false;
  }
}

async function deleteExpired() {
  if (deleting.value || previewing.value) return;
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
    if (error.status !== 401) ElMessage.error(error.message);
  } finally {
    deleting.value = false;
  }
}
</script>

<style scoped>
.maintenance-card {
  margin: 20px 0;
  border-color: var(--line);
  border-radius: var(--radius-panel);
}

.empty-expired { color: var(--text-muted); margin: 12px 0; }

.result-grid {
  margin-bottom: 16px;
}

.maintenance-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
</style>

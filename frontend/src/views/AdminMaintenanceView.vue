<template>
  <div class="page">
    <header class="page-heading"><p class="eyebrow">管理后台</p><h1>提问日志维护 · 高级</h1><p class="page-description">演示时请勿当场删除。日常维护可按留存窗口预览并处理到期记录，每次仅操作受限的一批。</p></header>
    <p class="scope-note">提问日志包含问题原文，只用于留存窗口内的课程学情。维护操作不会展示问题或提问者。</p>

    <el-card class="maintenance-card panel-card" shadow="never">
      <template #header>到期记录</template>
      <p class="explanation">
        先预览最早到期的一批，核对后再删除。每次仅处理服务器允许的一批，不会扫描或一次删除全部记录。
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

.scope-note {
  margin: 0;
  padding-left: 12px;
  border-left: 2px solid var(--el-color-primary-light-5);
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.75;
}

.explanation {
  margin: 0 0 16px;
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.7;
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

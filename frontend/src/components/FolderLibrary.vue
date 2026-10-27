<template>
  <div class="folder-library">
    <aside class="folder-sidebar" aria-label="课程资料目录">
      <div class="directory-heading"><span class="directory-mark" aria-hidden="true">册</span><h2>资料目录</h2></div>
      <el-tree
        :data="tree" node-key="key" :current-node-key="modelValue ?? 'all'"
        :expand-on-click-node="false" default-expand-all highlight-current
        aria-label="资料夹" @node-click="selectFolder"
      >
        <template #default="{ data }">
          <span class="directory-node"><span class="directory-label" :title="data.label">{{ data.label }}</span><span class="directory-count">{{ data.count }}</span></span>
        </template>
      </el-tree>
      <div v-if="$slots.actions" class="directory-actions"><slot name="actions" /></div>
    </aside>
    <section class="folder-content" :aria-label="group.label" v-loading="loading">
      <div class="folder-search">
        <el-input :model-value="search" placeholder="搜索整课文件名" clearable aria-label="搜索整课文件名" @update:model-value="$emit('update:search', $event)" />
        <span class="folder-result-count" role="status">{{ search.trim() ? '整课匹配' : '共' }} {{ group.documents.length }} 份资料</span>
      </div>
      <slot :group="group" />
    </section>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue';
import { documentGroups, folderTree, libraryGroup } from '../documentFolders';

const props = defineProps({
  documents: { type: Array, default: () => [] },
  folders: { type: Array, default: () => [] },
  modelValue: { type: String, default: null },
  search: { type: String, default: '' },
  loading: Boolean,
});
const emit = defineEmits(['update:modelValue', 'update:search']);
const groups = computed(() => documentGroups(props.documents, props.folders));
const tree = computed(() => folderTree(groups.value));
const group = computed(() => libraryGroup(props.documents, props.folders, props.modelValue, props.search));
watch(groups, () => {
  if (!groups.value.some(item => item.id === props.modelValue)) emit('update:modelValue', null);
});
function selectFolder(node) { emit('update:modelValue', node.id); }
</script>

<style scoped>
.folder-library { display: grid; grid-template-columns: 220px minmax(0, 1fr); gap: 20px; align-items: start; margin-top: 20px; }
.folder-sidebar, .folder-content { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-panel); padding: 20px; min-width: 0; }
.folder-sidebar { position: sticky; top: 20px; }
.directory-heading { display: flex; align-items: center; gap: 10px; margin-bottom: 16px; }
.directory-heading h2 { font-size: 16px; margin: 0; }
.directory-mark { color: var(--el-color-primary); font-weight: 700; font-size: 24px; }
.folder-search { display: flex; align-items: center; gap: 16px; padding-bottom: 20px; margin-bottom: 20px; border-bottom: 1px solid var(--line); }
.folder-search .el-input { max-width: 400px; }
.folder-result-count { margin-left: auto; white-space: nowrap; color: var(--text-muted); font-size: 12px; }
.directory-node { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; min-width: 0; padding-right: 8px; }
.directory-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.directory-count { color: var(--text-muted); font-size: 12px; font-variant-numeric: tabular-nums; }
.directory-actions { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line); }
:deep(.el-tree) { background: transparent; max-height: calc(100vh - 280px); overflow: auto; }
:deep(.el-tree-node__content) { height: 38px; border-radius: 6px; }
:deep(.el-tree-node.is-current > .el-tree-node__content) { color: var(--el-color-primary); font-weight: 600; }
@media (max-width: 900px) {
  .folder-library { grid-template-columns: minmax(0, 1fr); }
  .folder-sidebar { position: static; }
  .folder-sidebar :deep(.el-tree) { max-height: 260px; overflow: auto; }
  .folder-sidebar, .folder-content { padding: 16px; }
}
@media (max-width: 560px) {
  .folder-search { flex-wrap: wrap; gap: 8px; }
  .folder-search .el-input { max-width: none; }
}
</style>

<template>
  <div class="folder-library">
    <aside class="folder-sidebar" aria-label="课程资料目录">
      <div class="directory-heading"><span class="directory-mark" aria-hidden="true">册</span><h2>资料目录</h2></div>
      <p class="directory-hint">按资料夹浏览 · 最多两层</p>
      <el-tree
        :data="tree" node-key="key" :current-node-key="modelValue ?? 'ungrouped'"
        :expand-on-click-node="false" default-expand-all highlight-current
        aria-label="资料夹" @node-click="selectFolder"
      >
        <template #default="{ data }">
          <span class="directory-node"><span class="directory-label" :title="data.label">{{ data.label }}</span><span class="directory-count">{{ data.count }}</span></span>
        </template>
      </el-tree>
      <div v-if="$slots.actions" class="directory-actions"><slot name="actions" /></div>
      <p class="directory-hint">目录仅用于整理资料，课程问答仍检索整课。</p>
    </aside>
    <section class="folder-content" :aria-label="group.label" v-loading="loading">
      <slot :group="group" />
    </section>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue';
import { documentGroups, folderTree } from '../documentFolders';

const props = defineProps({
  documents: { type: Array, default: () => [] },
  folders: { type: Array, default: () => [] },
  modelValue: { type: String, default: null },
  loading: Boolean,
});
const emit = defineEmits(['update:modelValue']);
const groups = computed(() => documentGroups(props.documents, props.folders));
const tree = computed(() => folderTree(groups.value));
const group = computed(() => groups.value.find(item => item.id === props.modelValue) || groups.value.find(item => item.id === null));
watch(groups, () => {
  if (!groups.value.some(item => item.id === props.modelValue)) emit('update:modelValue', null);
});
function selectFolder(node) { emit('update:modelValue', node.id); }
</script>

<style scoped>
.folder-library { display: grid; grid-template-columns: 240px minmax(0, 1fr); gap: 20px; align-items: start; margin-top: 20px; }
.folder-sidebar, .folder-content { background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius-panel); padding: 20px; min-width: 0; }
.directory-heading { display: flex; align-items: center; gap: 10px; }
.directory-heading h2 { font-size: 16px; margin: 0; }
.directory-mark { color: var(--el-color-primary); font-weight: 700; font-size: 24px; }
.directory-hint { font-size: 12px; color: var(--text-muted); line-height: 1.7; margin: 12px 0; }
.directory-node { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; min-width: 0; padding-right: 8px; }
.directory-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.directory-count { color: var(--text-muted); font-size: 12px; }
.directory-actions { margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--line); }
:deep(.el-tree) { background: transparent; }
:deep(.el-tree-node__content) { height: 38px; border-radius: 6px; }
@media (max-width: 900px) {
  .folder-library { grid-template-columns: minmax(0, 1fr); }
  .folder-sidebar :deep(.el-tree) { max-height: 260px; overflow: auto; }
  .folder-sidebar, .folder-content { padding: 16px; }
}
</style>

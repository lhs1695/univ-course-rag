<template>
  <div class="runtime-overview">
    <el-alert :title="verdict.title" :type="verdict.type" :closable="false" show-icon />
    <p>{{ verdict.description }}</p>
    <details class="runtime-status">
      <summary>运行状态详情</summary>
      <div class="runtime-details"><p>{{ message }}</p></div>
    </details>
    <el-button text :loading="loading" @click="loadStatus">刷新运行状态</el-button>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
const state = ref(null);
const failure = ref("");
const loading = ref(false);
const label = (value) => ({ fake: "Fake 演示", configured: "已填写配置（本页不做连通性验证）", unavailable: "配置不可用" }[value] || "未知");
const verdict = computed(() => {
  if (failure.value) return { type: "error", title: "当前不可演示：状态检查失败", description: failure.value };
  if (!state.value) return { type: "info", title: "正在检查运行状态…", description: "请等待配置与数据库检查。" };
  const statuses = [state.value.embedding?.status, state.value.generation?.status];
  if (state.value.database !== "available" || statuses.includes("unavailable")) return { type: "error", title: "当前不可演示提问", description: "数据库或模型配置不可用，请先处理后刷新状态。" };
  if (statuses.every(value => value === "fake")) return { type: "success", title: "可尝试 Fake 演示", description: "数据库可用；当前使用 Fake，不代表真实模型效果。" };
  return { type: "warning", title: "配置已填，请在问答页实测", description: "数据库可用；本页未验证模型连通，尚不能确认真实问答可演示。" };
});
const message = computed(() => failure.value || (state.value
  ? `进程运行中；数据库${state.value.database === 'available' ? '可连接' : '不可连接'}；向量：${label(state.value.embedding.status)}；生成：${label(state.value.generation.status)}。本页检查配置与数据库状态；要确认模型可用，请在问答页实际提问验证。迁移与索引请结合运维记录核对。`
  : "正在检查本机运行状态…"));
async function loadStatus() {
  if (loading.value) return;
  loading.value = true;
  try {
    state.value = await api("/runtime");
    failure.value = "";
  } catch (error) {
    state.value = null;
    failure.value = error.message;
  } finally { loading.value = false; }
}
onMounted(loadStatus);
</script>

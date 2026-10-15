<template>
  <details class="runtime-status" :class="{ 'runtime-warning': !healthy }">
    <summary><span class="status-dot" aria-hidden="true"></span><span>{{ summary }}</span><span class="runtime-hint">运行状态</span></summary>
    <div class="runtime-details"><p>{{ message }}</p><el-button text :loading="loading" @click="loadStatus">刷新运行状态</el-button></div>
  </details>
</template>
<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
const state = ref(null);
const failure = ref("");
const loading = ref(false);
const label = (value) => ({ fake: "Fake 演示", configured: "已配置（未验证连通）", unavailable: "配置不可用" }[value] || "未知");
const healthy = computed(() => state.value?.database === "available" &&
  [state.value.embedding.status, state.value.generation.status].every(value => value !== "unavailable"));
const summary = computed(() => failure.value ? "运行状态检查失败"
  : !state.value ? "正在检查运行状态…"
  : `向量：${label(state.value.embedding.status)} · 生成：${label(state.value.generation.status)}${state.value.database !== 'available' ? ' · 数据库不可连接' : ''}`);
const message = computed(() => failure.value || (state.value
  ? `进程运行中；数据库${state.value.database === 'available' ? '可连接' : '不可连接'}；向量：${label(state.value.embedding.status)}；生成：${label(state.value.generation.status)}。迁移、索引和真实模型连通性未验证。`
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

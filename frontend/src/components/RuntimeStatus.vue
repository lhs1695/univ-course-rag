<template>
  <div class="runtime-overview">
    <div class="runtime-heading">
      <el-alert :title="verdict.title" :type="verdict.type" :closable="false" show-icon />
      <el-button text :loading="loading" @click="loadStatus">刷新</el-button>
    </div>
    <el-descriptions v-if="state" :column="1" border>
      <el-descriptions-item label="数据库">{{ state.database === "available" ? "可连接" : "不可用" }}</el-descriptions-item>
      <el-descriptions-item label="向量模型">{{ label(state.embedding?.status) }}</el-descriptions-item>
      <el-descriptions-item label="生成模型">{{ label(state.generation?.status) }}</el-descriptions-item>
    </el-descriptions>
    <p v-if="failure" class="runtime-action">请检查服务后刷新状态。</p>
    <p v-else-if="state" class="runtime-action">{{ verdict.action }}</p>
    <p v-else class="runtime-action">正在检查运行状态…</p>
  </div>
</template>
<script setup>
import { computed, onMounted, ref } from "vue";
import { api } from "../api";
const state = ref(null);
const failure = ref("");
const loading = ref(false);
const label = (value) => ({ fake: "演示用假模型", configured: "已配置，未探测", unavailable: "不可用" }[value] || "未知");
const verdict = computed(() => {
  if (failure.value) return { type: "error", title: "当前不可用", action: "请检查服务后刷新状态。" };
  if (!state.value) return { type: "info", title: "正在检查运行状态…", action: "" };
  const statuses = [state.value.embedding?.status, state.value.generation?.status];
  if (state.value.database !== "available" || statuses.includes("unavailable")) return { type: "error", title: "当前不可用", action: "请检查系统状态后再尝试提问。" };
  if (statuses.every(value => value === "fake")) return { type: "success", title: "可演示（假模型）", action: "到任一课程提问页验证。" };
  return { type: "warning", title: "配置已就绪，待实测", action: "到任一课程提问页验证。" };
});
async function loadStatus() {
  if (loading.value) return;
  loading.value = true;
  try { state.value = await api("/runtime"); failure.value = ""; }
  catch (error) { state.value = null; failure.value = error.message; }
  finally { loading.value = false; }
}
onMounted(loadStatus);
</script>

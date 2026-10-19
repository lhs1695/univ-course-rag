<template>
  <div class="runtime-overview">
    <div class="runtime-heading">
      <el-button text :loading="loading" @click="loadStatus">刷新</el-button>
    </div>
    <el-descriptions v-if="state" :column="1" border>
      <el-descriptions-item label="数据库">{{ state.database === "available" ? "可连接" : "不可用" }}</el-descriptions-item>
      <el-descriptions-item label="向量模型">{{ label(state.embedding?.status) }}</el-descriptions-item>
      <el-descriptions-item label="生成模型">{{ label(state.generation?.status) }}</el-descriptions-item>
    </el-descriptions>
    <p v-else-if="failure" class="runtime-action">{{ failure }}</p>
  </div>
</template>
<script setup>
import { onMounted, ref } from "vue";
import { api } from "../api";
const state = ref(null);
const failure = ref("");
const loading = ref(false);
const label = (value) => ({ fake: "演示用假模型", configured: "已配置", unavailable: "不可用" }[value] || "未知");
async function loadStatus() {
  if (loading.value) return;
  loading.value = true;
  try { state.value = await api("/runtime"); failure.value = ""; }
  catch (error) { state.value = null; failure.value = error.message; }
  finally { loading.value = false; }
}
onMounted(loadStatus);
</script>
<template>
  <div class="page">
    <header class="page-heading">
      <p class="eyebrow">管理后台</p>
      <h1>系统状态</h1>
      <p class="page-description">本页用于运维诊断。配置状态不代表已验证连通，运行状态也不代表问答正确性。</p>
    </header>
    <RuntimeStatus />
  </div>
</template>

<script setup>
import RuntimeStatus from "../components/RuntimeStatus.vue";
</script>

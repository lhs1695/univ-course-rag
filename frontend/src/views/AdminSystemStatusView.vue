<template>
  <div class="page">
    <header class="page-heading">
      <p class="eyebrow">管理后台</p>
      <h1>系统状态</h1>
      <p class="page-description">本页展示运行与配置状态；要确认模型可用，请在问答页实际提问验证。运行状态不代表问答正确性。</p>
    </header>
    <section class="panel-card"><RuntimeStatus /></section>
  </div>
</template>

<script setup>
import RuntimeStatus from "../components/RuntimeStatus.vue";
</script>

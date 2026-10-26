<template>
  <div class="page">
    <header class="page-heading">
      <p class="eyebrow">管理 / 服务状态</p><h1>系统状态</h1><p class="page-description">查看数据库连接与问答模型配置状态。</p>
    </header>
    <section class="panel-card"><RuntimeStatus /></section>
  </div>
</template>

<script setup>
import RuntimeStatus from "../components/RuntimeStatus.vue";
</script>

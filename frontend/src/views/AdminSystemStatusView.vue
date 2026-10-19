<template>
  <div class="page">
    <header class="page-heading">
      <h1>系统状态</h1>
      <p class="page-description">查看数据库与模型配置，判断当前演示准备情况。</p>
    </header>
    <section class="panel-card"><RuntimeStatus /></section>
  </div>
</template>

<script setup>
import RuntimeStatus from "../components/RuntimeStatus.vue";
</script>

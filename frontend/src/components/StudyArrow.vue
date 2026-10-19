<template>
  <svg class="study-arrow" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
    <path :d="diagonal ? 'M6 18 18 6M6 6h12v12' : 'M5 12h14m-6-6 6 6-6 6'" />
  </svg>
</template>

<script setup>
defineProps({ diagonal: Boolean });
</script>

<style scoped>
.study-arrow { flex-shrink: 0; vertical-align: middle; }
</style>

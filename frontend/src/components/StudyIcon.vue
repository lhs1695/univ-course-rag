<template><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name] || paths.book" /></svg></template>
<script setup>
defineProps({ name: { type: String, default: 'book' } });
const paths = {
  book: 'M12 5c-3-2-7-2-10-1v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1Zm0 0v15',
  grid: 'M3 3h7v7H3V3Zm11 0h7v7h-7V3ZM3 14h7v7H3v-7Zm11 0h7v7h-7v-7Z',
  ask: 'M4 4h16v12H9l-5 4V4Zm4 5h8m-8 3h5',
  file: 'M6 2h8l4 4v16H6V2Zm8 0v5h4M9 12h6m-6 4h6',
  arrow: 'M4 12h16m-6-6 6 6-6 6',
  search: 'M10.5 18a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15Zm5.5-2 5 5',
  exit: 'M10 4H4v16h6m-1-8h12m-4-4 4 4-4 4',
  check: 'm5 12 4 4L19 6',
};
</script>

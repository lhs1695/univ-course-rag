<template>
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <template v-if="name === 'book'"><path d="M3 4.5c3-1 6-.5 9 1.5 3-2 6-2.5 9-1.5v15c-3-1-6-.5-9 1.5-3-2-6-2.5-9-1.5z"/><path d="M12 6v15M6 8l3 1M15 9l3-1"/></template>
    <template v-else-if="name === 'chat'"><path d="M20 11a8 8 0 0 1-8 8H5l-3 3V11a9 9 0 0 1 18 0Z"/><path d="M7 9h8M7 13h5"/></template>
    <template v-else-if="name === 'file'"><path d="M14 3H5v18h14V8zM14 3v5h5M8 12h8M8 16h6"/></template>
    <template v-else-if="name === 'search'"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/></template>
    <template v-else-if="name === 'arrow'"><path d="M5 12h14m-5-5 5 5-5 5"/></template>
    <template v-else-if="name === 'external'"><path d="M14 3h7v7M21 3l-11 11M10 5H3v16h16v-7"/></template>
    <template v-else-if="name === 'grid'"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></template>
    <template v-else-if="name === 'menu'"><path d="M4 6h16M4 12h16M4 18h16"/></template>
    <template v-else><path d="m5 12 4 4L19 6"/></template>
  </svg>
</template>
<script setup>defineProps({ name: { type: String, default: 'book' } });</script>

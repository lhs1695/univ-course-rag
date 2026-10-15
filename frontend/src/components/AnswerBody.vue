<template>
  <div class="answer-markdown" v-html="html" @click="onCitation" />
</template>

<script setup>
import { computed } from 'vue';
import { renderAnswer } from '../answerMarkdown';

const props = defineProps({ answer: { type: String, required: true }, citations: { type: Array, required: true } });
const emit = defineEmits(['citation']);
const html = computed(() => renderAnswer(props.answer, props.citations));
function onCitation(event) {
  const link = event.target.closest('a[data-source-id]');
  if (!link || !event.currentTarget.contains(link)) return;
  event.preventDefault();
  emit('citation', link.dataset.sourceId);
}
</script>

<style scoped>
.answer-markdown { overflow-wrap: anywhere; line-height: 1.95; font-size: 15px; }
.answer-markdown :deep(pre) { overflow-x: auto; background: #f3f6f4; padding: 12px; border-radius: 6px; line-height: 1.6; }
.answer-markdown :deep(code) { white-space: pre-wrap; }
.answer-markdown :deep(table) { display: block; overflow-x: auto; border-collapse: collapse; }
.answer-markdown :deep(th), .answer-markdown :deep(td) { border: 1px solid #dfe7e2; padding: 6px 10px; }
.answer-markdown :deep(.inline-citation) { color: #17675f; font-weight: 600; margin: 0 3px; text-decoration: underline; }
.answer-markdown :deep(.unknown-citation) { color: #805b20; font-size: 12px; }
.answer-markdown :deep(h1), .answer-markdown :deep(h2), .answer-markdown :deep(h3) { font-size: 17px; }
</style>

<template>
  <div class="answer-markdown" v-html="html" @click="onCitation" />
</template>

<script setup>
import { computed } from 'vue';
import 'katex/dist/katex.min.css';
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
.answer-markdown { min-width: 0; max-width: 100%; overflow-wrap: anywhere; color: var(--text-body); line-height: 1.9; font-size: 16px; }
.answer-markdown :deep(.katex-display) { max-width: 100%; overflow-x: auto; overflow-y: hidden; padding: .2em 0; }
.answer-markdown :deep(.katex) { max-width: 100%; }
.answer-markdown :deep(.katex:not(.katex-display .katex)) { display: inline-block; overflow-x: auto; vertical-align: middle; }
.answer-markdown :deep(p) { margin: 0 0 1em; }
.answer-markdown :deep(p:last-child) { margin-bottom: 0; }
.answer-markdown :deep(pre) { overflow-x: auto; background: var(--surface-subtle); padding: 12px; border-radius: 6px; line-height: 1.6; }
.answer-markdown :deep(code) { white-space: pre-wrap; }
.answer-markdown :deep(table) { display: block; overflow-x: auto; border-collapse: collapse; }
.answer-markdown :deep(th), .answer-markdown :deep(td) { border: 1px solid var(--line); padding: 6px 10px; }
.answer-markdown :deep(.inline-citation) { color: var(--accent); font-weight: 600; margin: 0 3px; text-decoration: underline; }
.answer-markdown :deep(.unknown-citation) { color: var(--warning); font-size: 12px; }
.answer-markdown :deep(h1), .answer-markdown :deep(h2), .answer-markdown :deep(h3) { margin: 1.35em 0 .6em; font-size: 18px; }
</style>

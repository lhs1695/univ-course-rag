<template>
  <section ref="reader" class="document-reader" :class="{ 'reader-fullscreen': fullscreen }" aria-label="资料预览">
    <header class="reader-heading">
      <router-link :to="libraryPath">← 课程资料</router-link>
      <h1>{{ source?.filename || '资料预览' }}</h1>
      <button type="button" @click="fullscreen = !fullscreen">{{ fullscreen ? '退出全屏' : '全屏阅读' }}</button>
      <a v-if="source" :href="contentUrl" :download="source.filename">下载</a>
    </header>
    <div class="reader-toolbar" aria-label="阅读工具">
      <button :disabled="loading || page <= 1" @click="go(page - 1)">上一页</button>
      <label>第 <input aria-label="预览页码" type="number" min="1" :max="count || 1" :value="page" :disabled="loading || !count" @change="go($event.target.value)" /> / {{ count || '—' }} {{ format === 'pptx' ? '张' : '页' }}</label>
      <button :disabled="loading || page >= count" @click="go(page + 1)">下一页</button>
      <span class="reader-toolbar-spacer"></span>
      <button :disabled="zoom <= 50" aria-label="缩小" @click="zoom -= 10">−</button>
      <output aria-label="缩放比例">{{ zoom }}%</output>
      <button :disabled="zoom >= 200" aria-label="放大" @click="zoom += 10">＋</button>
      <button @click="zoom = 100">重置缩放</button>
    </div>
    <p v-if="loading" class="reader-message" role="status">正在打开资料…</p>
    <div v-if="failure" class="reader-message" role="alert"><p>{{ failure }}</p><button @click="load">重新加载</button></div>
    <div v-show="!failure" class="reader-body">
      <nav v-if="count > 1" class="reader-pages" :aria-label="format === 'pptx' ? '幻灯片列表' : '页面列表'">
        <button v-for="number in count" :key="number" :aria-current="page === number ? 'page' : undefined" @click="go(number)">{{ format === 'pptx' ? '幻灯片' : '第' }} {{ number }}{{ format === 'pptx' ? '' : ' 页' }}</button>
      </nav>
      <div ref="scrollArea" class="reader-scroll" tabindex="0" aria-label="资料内容，可滚动" @scroll.passive="trackPage">
        <div class="reader-paper" :style="{ zoom: zoom / 100 }">
          <canvas v-if="format === 'pdf'" ref="canvas" :aria-label="`PDF 第 ${page} 页`"></canvas>
          <div v-else-if="format === 'docx' || format === 'pptx'" ref="officeRoot">
            <component :is="officeComponent" v-if="officeComponent && binary" :src="binary" :options="officeOptions" @rendered="officeReady" @error="officeFailed" />
          </div>
          <template v-else>
            <article v-for="(part, index) in textPages" :key="index" :data-reader-page="index + 1" class="reader-text">
              <div v-if="format === 'md'" v-html="renderDocumentMarkdown(part)"></div>
              <pre v-else>{{ part }}</pre>
            </article>
          </template>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, markRaw, nextTick, onMounted, onUnmounted, ref, shallowRef, watch } from "vue";
import { useRoute } from "vue-router";
import { api } from "../api";
import { documentDownloadUrl } from "../documentDisplay";
import { previewFormat, previewPage, renderDocumentMarkdown, textPreviewPages } from "../documentPreview";

const route = useRoute();
// Admin document management already permits cross-course access without membership.
// Its separate parameter keeps the course-membership navigation guard scoped to course pages.
const courseId = String(route.params.courseId || route.params.previewCourseId);
const libraryPath = route.meta?.admin ? '/admin/documents' : `/courses/${courseId}/documents`;
const source = ref(null), format = ref(''), loading = ref(true), failure = ref('');
const fullscreen = ref(false), zoom = ref(100), page = ref(1), count = ref(0);
const reader = ref(null), canvas = ref(null), scrollArea = ref(null), officeRoot = ref(null);
const officeComponent = shallowRef(null), binary = shallowRef(null), textPages = ref([]);
const officeOptions = computed(() => format.value === 'pptx' ? { width: 960, height: 540 } : { breakPages: true, useBase64URL: true });
const contentUrl = computed(() => source.value ? documentDownloadUrl(courseId, source.value) : '');
let controller, pdfTask, pdf, renderTask, version = 0, renderVersion = 0, alive = true;
let pageNodes = [];

function officeFailed() {
  loading.value = false;
  failure.value = '资料暂时无法预览，可重新加载或下载原文件。';
}

async function load() {
  const current = ++version;
  controller?.abort();
  controller = new AbortController();
  renderTask?.cancel();
  await pdfTask?.destroy();
  pdf = null; pdfTask = null;
  loading.value = true; failure.value = ''; count.value = 0;
  binary.value = null; officeComponent.value = null; textPages.value = []; pageNodes = [];
  try {
    const metadata = await api(`/courses/${courseId}/documents/${route.params.documentId}`, { signal: controller.signal });
    if (!alive || current !== version) return;
    source.value = metadata;
    format.value = previewFormat(metadata.filename);
    if (!['pdf', 'pptx', 'docx', 'md', 'txt'].includes(format.value)) throw new Error('unsupported');
    const response = await fetch(contentUrl.value, { credentials: 'same-origin', signal: controller.signal });
    if (!response.ok) throw new Error('unavailable');
    const data = await response.arrayBuffer();
    if (!alive || current !== version) return;
    if (format.value === 'pdf') {
      const { getDocument, GlobalWorkerOptions } = await import('pdfjs-dist');
      const { default: workerUrl } = await import('pdfjs-dist/build/pdf.worker.min.mjs?url');
      if (!alive || current !== version) return;
      GlobalWorkerOptions.workerSrc = workerUrl;
      pdfTask = getDocument({ data, isEvalSupported: false, cMapUrl: '/pdfjs/cmaps/', cMapPacked: true, standardFontDataUrl: '/pdfjs/standard_fonts/', wasmUrl: '/pdfjs/wasm/' });
      pdf = await pdfTask.promise;
      if (!alive || current !== version) return;
      count.value = pdf.numPages;
      page.value = previewPage(route.query.page, count.value);
      await nextTick();
      await drawPdf();
    } else if (format.value === 'docx' || format.value === 'pptx') {
      const component = format.value === 'docx'
        ? await import('@vue-office/docx/lib/v3/index.js')
        : await import('@vue-office/pptx/lib/v3/index.js');
      if (format.value === 'docx') await import('@vue-office/docx/lib/v3/index.css');
      if (!alive || current !== version) return;
      officeComponent.value = markRaw(component.default);
      binary.value = data;
      return; // The component's rendered/error event finishes loading.
    } else {
      textPages.value = textPreviewPages(new TextDecoder().decode(data));
      count.value = Math.max(1, textPages.value.length);
      await nextTick();
      pageNodes = [...reader.value.querySelectorAll('[data-reader-page]')];
      await go(route.query.page || 1);
    }
    if (current === version) loading.value = false;
  } catch {
    if (alive && current === version) officeFailed();
  }
}

async function officeReady() {
  if (!alive) return;
  await nextTick();
  const selector = format.value === 'pptx' ? '.pptx-preview-slide-wrapper' : 'section.docx';
  pageNodes = [...officeRoot.value.querySelectorAll(selector)];
  count.value = Math.max(1, pageNodes.length);
  loading.value = false;
  await go(route.query.page || 1);
}

async function drawPdf() {
  const current = ++renderVersion;
  const previous = renderTask;
  previous?.cancel();
  try {
    await previous?.promise.catch(() => {});
    if (!alive || current !== renderVersion || !pdf) return;
    const pdfPage = await pdf.getPage(page.value);
    if (!alive || current !== renderVersion) return;
    // CSS zoom handles interactive resizing without allocating enormous canvases.
    const viewport = pdfPage.getViewport({ scale: 1.4 });
    const target = canvas.value;
    target.width = Math.ceil(viewport.width); target.height = Math.ceil(viewport.height);
    target.style.width = `${viewport.width}px`; target.style.height = `${viewport.height}px`;
    renderTask = pdfPage.render({ canvasContext: target.getContext('2d'), viewport });
    await renderTask.promise;
  } catch (error) {
    if (alive && current === renderVersion && error.name !== 'RenderingCancelledException') officeFailed();
  }
}

async function go(value) {
  page.value = previewPage(value, count.value);
  if (pdf) {
    await drawPdf();
    scrollArea.value?.scrollTo({ top: 0, left: 0 });
  } else {
    const node = pageNodes[page.value - 1];
    if (node && scrollArea.value) {
      const container = scrollArea.value;
      container.scrollTop += node.getBoundingClientRect().top - container.getBoundingClientRect().top - 20;
    }
  }
}

function trackPage() {
  if (pdf || !pageNodes.length || !scrollArea.value) return;
  const top = scrollArea.value.getBoundingClientRect().top + 40;
  const index = pageNodes.findIndex(node => node.getBoundingClientRect().bottom > top);
  if (index >= 0) page.value = index + 1;
}
function escapeFullscreen(event) { if (event.key === 'Escape') fullscreen.value = false; }
watch(fullscreen, value => { document.body.style.overflow = value ? 'hidden' : ''; });
onMounted(() => { window.addEventListener('keydown', escapeFullscreen); load(); });
onUnmounted(() => {
  alive = false; version++; renderVersion++; controller?.abort(); renderTask?.cancel(); pdfTask?.destroy();
  window.removeEventListener('keydown', escapeFullscreen); document.body.style.overflow = '';
});
</script>

<style scoped>
.document-reader { background: var(--surface, #fff); color: var(--text-body, #202a32); border: 1px solid var(--line, #ddd); border-radius: 12px; overflow: hidden; }
.reader-fullscreen { position: fixed; inset: 0; z-index: 2200; border-radius: 0; display: flex; flex-direction: column; }
.reader-heading, .reader-toolbar { display: flex; align-items: center; gap: 12px; padding: 14px 18px; border-bottom: 1px solid var(--line, #d7dce0); flex-wrap: wrap; background: var(--surface, #fff); }
.reader-heading h1 { font-size: 17px; flex: 1; margin: 0; overflow-wrap: anywhere; }
.reader-heading a { font-size: 13px; }
.reader-toolbar { gap: 8px; font-size: 13px; }
.reader-toolbar-spacer { flex: 1; }
.reader-toolbar label { display: flex; align-items: center; gap: 5px; }
.reader-toolbar input { width: 65px; padding: 6px; color: inherit; background: transparent; border: 1px solid #adb8bf; border-radius: 4px; }
button { padding: 7px 10px; border: 1px solid #adb8bf; border-radius: 5px; background: transparent; color: inherit; cursor: pointer; }
button:disabled { opacity: .4; cursor: default; }
.reader-body { display: flex; height: 72vh; min-height: 400px; }
.reader-fullscreen .reader-body { height: auto; min-height: 0; flex: 1; }
.reader-pages { flex: 0 0 112px; overflow: auto; padding: 12px 8px; border-right: 1px solid #d7dce0; }
.reader-pages button { display: block; width: 100%; margin-bottom: 8px; font-size: 12px; }
.reader-pages [aria-current] { background: #234b69; color: #fff; border-color: #234b69; }
.reader-scroll { overflow: auto; flex: 1; min-width: 0; padding: 20px; background: #e6e9ed; color: #222; }
.reader-paper { width: max-content; min-width: 100%; --text-strong: #222; --text-body: #222; --accent: #234b69; --accent-hover: #123149; }
.reader-paper canvas { display: block; background: #fff; box-shadow: 0 2px 10px #0002; margin: 0 auto; }
.reader-message { padding: 20px; margin: 0; }
.reader-text { width: 760px; box-sizing: border-box; background: #fff; padding: 40px 48px; margin: 0 auto 20px; line-height: 1.85; overflow-wrap: anywhere; box-shadow: 0 2px 10px #0001; }
.reader-text pre { white-space: pre-wrap; font: inherit; }
.reader-text :deep(table) { border-collapse: collapse; max-width: 100%; }
.reader-text :deep(td), .reader-text :deep(th) { border: 1px solid #bbb; padding: 5px 10px; }
.reader-text :deep(pre) { overflow-x: auto; }
.reader-paper :deep(.pptx-preview-wrapper) { height: auto !important; overflow: visible !important; background: transparent !important; }
.reader-paper :deep(.pptx-preview-slide-wrapper) { margin-bottom: 20px; }
.reader-paper :deep(.docx-wrapper) { background: transparent; padding: 0; }
.reader-paper :deep(.vue-office-docx) { height: auto; overflow: visible; }
@media (max-width: 640px) { .reader-pages { flex-basis: 80px; } .reader-heading, .reader-toolbar { padding: 10px; } .reader-scroll { padding: 10px; } }
</style>

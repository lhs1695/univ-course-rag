import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc';
import * as vue from 'vue';
import * as preview from '../src/documentPreview.js';
import * as display from '../src/documentDisplay.js';
import { sortCoursesForDisplay } from '../src/courseDisplay.js';

test('course priority is stable, matches titles containing the names and never mutates API rows', () => {
  const rows = ['教育学', '智能移动机器人（秋季）', '线性代数', '机器学习基础', '其他', '机器学习实验'].map(title => ({ title }));
  assert.deepEqual(sortCoursesForDisplay(rows).map(row => row.title), ['机器学习基础', '机器学习实验', '智能移动机器人（秋季）', '教育学', '线性代数', '其他']);
  assert.equal(rows[0].title, '教育学');
});

test('preview normalizes formats and page bounds; text sections preserve source text', () => {
  for (const filename of ['课件.PDF', '课件.pptx', '教案.docx', '笔记.md', '笔记.markdown', '备注.txt']) {
    assert.match(display.documentContentUrl('course', { id: 'doc', filename }, 3), /\/preview\?page=3$/);
  }
  assert.equal(preview.previewFormat('笔记.MARKDOWN'), 'md');
  assert.equal(preview.previewPage('invalid', 3), 1);
  assert.equal(preview.previewPage(-5, 3), 1);
  assert.equal(preview.previewPage(100, 3), 3);
  assert.deepEqual(preview.textPreviewPages('一\f二\n# 第三节\n三'), ['一', '二', '# 第三节\n三']);
  const paragraphs = Array.from({ length: 20 }, (_, i) => `${i}:` + '文'.repeat(600)).join('\n\n');
  assert.equal(preview.textPreviewPages(paragraphs).join('\n\n'), paragraphs);
  assert.ok(preview.textPreviewPages(paragraphs).length > 1);
});

test('Markdown keeps tables and headings but escapes executable HTML and blocks remote images', () => {
  const html = preview.renderDocumentMarkdown('# 标题\n\n| A | B |\n|---|---|\n|1|2|\n\n<script>alert(1)</script>\n\n![图](https://example.org/private.png)\n\n[危险](javascript:alert(1))');
  assert.match(html, /<h1>标题<\/h1>/);
  assert.match(html, /<table>/);
  assert.doesNotMatch(html, /<script|<img|href="javascript:/);
});

const flush = async () => { for (let i = 0; i < 5; i++) await new Promise(resolve => setImmediate(resolve)); };

async function readerHarness({ filename = '课件.pdf', page = 1, fetchStatus = 200, metadata, admin = false } = {}) {
  const saved = { fetch: globalThis.fetch, window: globalThis.window, document: globalThis.document };
  const calls = [], renderedPages = [], events = new Map();
  let destroyed = false;
  globalThis.window = { addEventListener: (name, handler) => events.set(name, handler), removeEventListener: name => events.delete(name) };
  globalThis.document = { body: { style: { overflow: '' } } };
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return { ok: fetchStatus === 200, arrayBuffer: async () => new TextEncoder().encode('第一页\f第二页').buffer };
  };
  const fakePdf = { numPages: 3, getPage: async number => ({
    getViewport: () => ({ width: 600, height: 800 }),
    render: () => { renderedPages.push(number); return { promise: Promise.resolve(), cancel() {} }; },
  }) };
  const dependencies = {
    vue,
    'vue-router': { useRoute: () => ({ params: { [admin ? 'previewCourseId' : 'courseId']: 'course', documentId: 'doc' }, query: { page }, meta: { admin } }) },
    '../api': { api: async path => {
      assert.equal(path, '/courses/course/documents/doc');
      return metadata ? await metadata : ({ id: 'doc', filename });
    } },
    '../documentDisplay': display, '../documentPreview': preview,
  };
  const { descriptor } = parse(readFileSync(new URL('../src/views/DocumentPreviewView.vue', import.meta.url), 'utf8'));
  const script = compileScript(descriptor, { id: 'reader', genDefaultAs: 'component' });
  const template = compileTemplate({ source: descriptor.template.content, filename: 'DocumentPreviewView.vue', id: 'reader', compilerOptions: { bindingMetadata: script.bindings } });
  assert.deepEqual(template.errors, []);
  const imports = Object.entries(script.imports);
  const component = new Function(...imports.map(([local]) => local), 'loadModule',
    script.content.replace(/^import .+ from ["'].+["'];?$/gm, '').replaceAll('import(', 'loadModule(') + '\nreturn component;',
  )(...imports.map(([, entry]) => dependencies[entry.source][entry.imported]), async name => {
    if (name === 'pdfjs-dist') return { GlobalWorkerOptions: {}, getDocument: () => ({ promise: Promise.resolve(fakePdf), destroy: async () => { destroyed = true; } }) };
    return { default: name.includes('worker') ? '/assets/pdf.worker.mjs' : { render: () => null } };
  });
  component.render = () => null;
  const renderer = vue.createRenderer({ createComment: () => ({}), insert() {}, remove() {}, parentNode() {}, nextSibling() {} });
  const app = renderer.createApp(component);
  const state = app.mount({}).$.setupState;
  state.canvas = { style: {}, getContext: () => ({}) };
  state.scrollArea = { scrollTop: 0, scrollTo() {}, getBoundingClientRect: () => ({ top: 0 }) };
  state.reader = { querySelectorAll: () => [] };
  await flush();
  return { state, calls, renderedPages, events,
    setFetchStatus(status) { fetchStatus = status; },
    get destroyed() { return destroyed; },
    cleanup() {
      app.unmount();
      for (const [key, value] of Object.entries(saved)) {
        if (value === undefined) delete globalThis[key]; else globalThis[key] = value;
      }
    },
  };
}

test('PDF citation opens the requested page, clamps navigation, and releases the worker on leave', async () => {
  const harness = await readerHarness({ page: 2 });
  try {
    assert.equal(harness.state.failure, '');
    assert.equal(harness.state.loading, false);
    assert.equal(harness.state.count, 3);
    assert.deepEqual(harness.renderedPages, [2]);
    await harness.state.go(99);
    await harness.state.go(-5);
    assert.deepEqual(harness.renderedPages, [2, 3, 1]);
    assert.equal(harness.calls[0].url, '/courses/course/documents/doc/content');
    assert.equal(harness.calls[0].options.credentials, 'same-origin');
    harness.state.fullscreen = true;
    await vue.nextTick();
    assert.equal(document.body.style.overflow, 'hidden');
    harness.events.get('keydown')({ key: 'Escape' });
    assert.equal(harness.state.fullscreen, false);
  } finally { harness.cleanup(); }
  assert.equal(harness.destroyed, true);
});

for (const filename of ['课件.pptx', '教案.docx']) {
  test(`${filename} renders in the office component with a navigable page list`, async () => {
    const harness = await readerHarness({ filename, page: 2 });
    try {
      assert.ok(harness.state.binary instanceof ArrayBuffer);
      assert.ok(harness.state.officeComponent);
      const nodes = [0, 500, 1000].map(top => ({ getBoundingClientRect: () => ({ top, bottom: top + 490 }) }));
      harness.state.officeRoot = { querySelectorAll: selector => {
        assert.equal(selector, filename.endsWith('pptx') ? '.pptx-preview-slide-wrapper' : 'section.docx');
        return nodes;
      } };
      await harness.state.officeReady();
      assert.equal(harness.state.count, 3);
      assert.equal(harness.state.page, 2);
      assert.equal(harness.state.scrollArea.scrollTop, 480);
      assert.equal(harness.state.loading, false);
    } finally { harness.cleanup(); }
  });
}

test('TXT pages render as text; denied content displays a retryable failure', async () => {
  const harness = await readerHarness({ filename: '备注.txt', fetchStatus: 403 });
  try {
    assert.match(harness.state.failure, /无法预览/);
    assert.equal(harness.state.binary, null);
    harness.setFetchStatus(200);
    await harness.state.load();
    assert.equal(harness.state.failure, '');
    assert.deepEqual(harness.state.textPages, ['第一页', '第二页']);
    assert.equal(harness.state.count, 2);
  } finally { harness.cleanup(); }
});

test('leaving before metadata returns discards the response without fetching source content', async () => {
  let release;
  const metadata = new Promise(resolve => { release = resolve; });
  const harness = await readerHarness({ metadata });
  harness.cleanup();
  release({ id: 'doc', filename: 'private.pdf' });
  await flush();
  assert.equal(harness.calls.length, 0);
});

test('admin preview uses the existing document API without requiring course membership', async () => {
  assert.equal(display.documentContentUrl('course', { id: 'doc' }, 1, { admin: true }), '/admin/documents/course/doc/preview?page=1');
  const harness = await readerHarness({ admin: true, filename: '备注.txt' });
  try {
    assert.equal(harness.state.libraryPath, '/admin/documents');
    assert.equal(harness.state.failure, '');
    assert.equal(harness.calls[0].url, '/courses/course/documents/doc/content');
  } finally { harness.cleanup(); }
});

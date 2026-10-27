import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc';
import * as vue from 'vue';
import { renderToString } from '@vue/server-renderer';
import * as documentDisplay from './documentDisplay.js';
import { documentGroups, folderOptions, folderTree, folderParentOptions, libraryGroup, documentFolderTargets } from './documentFolders.js';

const folders = [
  { id: 'child', parent_id: 'root', name: '第一章' },
  { id: 'root', parent_id: null, name: '讲义' },
  { id: 'empty', parent_id: null, name: '练习' },
];

test('folders preserve two-level order and distinguish matching child names', () => {
  assert.deepEqual(folderOptions(folders).map(folder => folder.label), ['讲义', '讲义 / 第一章', '练习']);
});

test('all documents includes root files while each folder lists its direct files', () => {
  const documents = [
    { id: 'd1', folder_id: 'child' },
    { id: 'd2', folder_id: null },
    { id: 'd3', folder_id: 'root' },
  ];
  const groups = documentGroups(documents, folders);
  assert.deepEqual(groups.map(group => [group.label, group.documents.map(doc => doc.id)]), [
    ['讲义', ['d3']], ['讲义 / 第一章', ['d1']], ['练习', []], ['全部资料', ['d1', 'd2', 'd3']],
  ]);
});

test('a list refresh race retains documents whose folder was not in the folder snapshot', () => {
  const groups = documentGroups([{ id: 'd', folder_id: 'new', folder_name: '新夹' }], []);
  assert.equal(groups.find(group => group.id === 'new').label, '新夹');
  assert.equal(groups.find(group => group.id === null).documents.length, 1);
  assert.equal(groups.find(group => group.id === 'new').documents.length, 1);
});

test('sidebar tree keeps two levels, direct counts, empty folders and refresh-race documents', () => {
  const tree = folderTree(documentGroups([
    { id: 'd1', folder_id: 'child' }, { id: 'd2', folder_id: null },
    { id: 'd3', folder_id: 'unknown', folder_name: '新资料夹' },
  ], folders));
  assert.deepEqual(tree.map(node => [node.value, node.label, node.count]), [
    ['', '全部资料', 3], ['root', '讲义', 0], ['empty', '练习', 0], ['unknown', '新资料夹', 1],
  ]);
  assert.deepEqual(tree[1].children.map(node => [node.value, node.label, node.count]), [['child', '第一章', 1]]);
  assert.ok(tree[1].children.every(node => !node.children));
  assert.equal(new Set(tree.flatMap(node => [node.key, ...(node.children || []).map(child => child.key)])).size, 5);
});

test('search matches filenames across the course regardless of selected folder', () => {
  const documents = [
    { id: 'a', filename: '第一章.PDF', folder_id: 'child' },
    { id: 'b', filename: '第一章笔记.pdf', folder_id: null },
    { id: 'c', filename: '练习.txt', folder_id: 'root' },
  ];
  for (const folderId of ['root', 'child', 'empty', null]) {
    assert.deepEqual(libraryGroup(documents, folders, folderId, '  第一章  ').documents.map(doc => doc.id), ['a', 'b']);
    assert.deepEqual(libraryGroup(documents, folders, folderId, '.pDf').documents.map(doc => doc.id), ['a', 'b']);
    assert.equal(libraryGroup(documents, folders, folderId, 'missing').documents.length, 0);
    // Clearing search restores the folder's direct contents, not its subfolders.
    assert.deepEqual(libraryGroup(documents, folders, folderId, ' ').documents,
      folderId === null ? documents : documents.filter(doc => doc.folder_id === folderId));
  }
  assert.deepEqual(libraryGroup(documents, folders, 'deleted').documents, documents);
  assert.equal(libraryGroup([{ filename: 'other.txt', folder_id: 'root' }], folders, 'root', '讲义').documents.length, 0);
});

test('move targets distinguish the course root from the all-documents browsing view', () => {
  const targets = documentFolderTargets(folders);
  assert.equal(targets[0].label, '课程根目录');
  assert.equal(targets[0].value, '');
  assert.deepEqual(targets[1].children.map(node => node.value), ['child']);
  assert.equal(targets.some(node => node.label === '全部资料'), false);
});

test('parent targets exclude self and children; folders with children must stay at root', () => {
  assert.deepEqual(folderParentOptions(folders).map(folder => folder.id), ['root', 'empty']);
  assert.deepEqual(folderParentOptions(folders, folders[0]).map(folder => folder.id), ['root', 'empty']);
  assert.deepEqual(folderParentOptions(folders, folders[1]), []);
  assert.deepEqual(folderParentOptions(folders, folders[2]).map(folder => folder.id), ['root']);
});

// Exercise the real setup actions without a DOM or any real backend/ingest services.
async function documentsHarness(request) {
  const source = readFileSync(new URL('views/DocumentsView.vue', import.meta.url), 'utf8');
  const { descriptor } = parse(source);
  const script = compileScript(descriptor, { id: 'folders-actions', genDefaultAs: 'component' });
  const dependencies = {
    vue,
    '../api': { api: request },
    '../session': { session: { user: { role: 'teacher' } } },
    '../courseAccess': { courseAccess: { course: { capabilities: { can_manage_documents: true } } } },
    '../documentDisplay': { clampDocumentPage: () => 1, documentContentUrl: () => '', documentDownloadUrl: () => '', isPdfDocument: () => false },
    '../documentFolders': { documentGroups, folderOptions, folderTree, folderParentOptions, libraryGroup, documentFolderTargets },
    'vue-router': { useRoute: () => ({ params: { courseId: 'course' } }) },
    'element-plus': { ElMessage: { success() {}, error() {}, info() {} }, ElMessageBox: { confirm: async () => {} } },
    '../components/StudentDocuments.vue': { default: {} },
    '../components/FolderLibrary.vue': { default: {} },
  };
  const imports = Object.entries(script.imports);
  const component = new Function(...imports.map(([local]) => local),
    script.content.replace(/^import .+ from ["'].+["'];?$/gm, '') + '\nreturn component;',
  )(...imports.map(([, entry]) => dependencies[entry.source][entry.imported]));
  return setupHarness(component);
}

async function setupHarness(component) {
  component.render = () => null;
  const renderer = vue.createRenderer({ createComment: () => ({}), insert() {}, remove() {}, parentNode() {}, nextSibling() {} });
  const app = renderer.createApp(component);
  const instance = app.mount({});
  await new Promise(resolve => setImmediate(resolve));
  return { state: instance.$.setupState, unmount: () => app.unmount() };
}

test('upload uses the selected folder and an explicit retry retains its original target', async () => {
  const uploads = [];
  const harness = await documentsHarness(async (path, options) => {
    if (options?.formData) {
      uploads.push(options.formData.get('folder_id'));
      throw Object.assign(new Error('isolated upload failure'), { status: 503 });
    }
    if (path.endsWith('/documents')) return [];
    if (path.endsWith('/folders')) return folders;
    return { title: '本课' };
  });
  try {
    harness.state.selectedFolderId = 'child';
    await harness.state.onUpload({ file: new File(['fake'], 'lesson.txt') });
    harness.state.selectedFolderId = 'empty';
    await harness.state.retryUpload();
    assert.deepEqual(uploads, ['child', 'child']);
  } finally { harness.unmount(); }
});

test('moving a document after polling updates the live list and opens the target folder', async () => {
  const original = { id: 'doc', filename: 'lesson.txt', folder_id: 'child', job_status: 'succeeded', retrieval_enabled: false };
  const harness = await documentsHarness(async (path, options) => {
    if (options?.method === 'PATCH') {
      assert.deepEqual(options.json, { folder_id: 'empty' });
      return { ...original, folder_id: 'empty' };
    }
    if (path.endsWith('/documents')) return [{ ...original }];
    if (path.endsWith('/folders')) return folders;
    return { title: '本课' };
  });
  try {
    harness.state.openDocumentMove(harness.state.documents[0]);
    harness.state.search = 'lesson';
    harness.state.documents = [{ ...original }]; // A poll replaces the row while the dialog is open.
    harness.state.documentMove.targetId = 'empty';
    await harness.state.moveDocument();
    assert.equal(harness.state.documents[0].folder_id, 'empty');
    assert.equal(harness.state.documents[0].retrieval_enabled, false);
    assert.equal(harness.state.selectedFolderId, 'empty');
    assert.equal(harness.state.documentMove.visible, false);
    assert.equal(harness.state.search, '');
  } finally { harness.unmount(); }
});

test('teacher maintenance menu can remove enabled files from retrieval but cannot enable files', async () => {
  const writes = [];
  const documents = [{ id: 'doc', filename: 'lesson.txt', retrieval_enabled: true }];
  const harness = await documentsHarness(async (path, options) => {
    if (options?.method) writes.push([path, options]);
    if (path.endsWith('/documents')) return documents;
    if (path.endsWith('/folders')) return folders;
    return { title: '本课' };
  });
  try {
    await harness.state.onDocumentAction('disable', documents[0]);
    assert.equal(writes.length, 1);
    assert.equal(writes[0][1].method, 'DELETE');
    await harness.state.onDocumentAction('disable', { ...documents[0], retrieval_enabled: false });
    await harness.state.onDocumentAction('enable', documents[0]);
    assert.equal(writes.length, 1);
  } finally { harness.unmount(); }
});

test('changing a folder parent keeps its selection and does not touch document retrieval', async () => {
  const writes = [];
  let currentFolders = [...folders];
  const harness = await documentsHarness(async (path, options) => {
    if (options?.method === 'PATCH') {
      writes.push([path, options.json]);
      const moved = { ...folders[0], parent_id: options.json.parent_id };
      currentFolders = currentFolders.map(folder => folder.id === moved.id ? moved : folder);
      return moved;
    }
    if (path.endsWith('/documents')) return [];
    if (path.endsWith('/folders')) return currentFolders;
    return { title: '本课' };
  });
  try {
    harness.state.openFolderDialog('move', folders[0]);
    harness.state.folderDialog.parentId = 'empty';
    harness.state.search = 'lesson';
    await harness.state.saveFolder();
    assert.deepEqual(writes, [['/courses/course/folders/child', { parent_id: 'empty' }]]);
    assert.equal(harness.state.selectedFolderId, 'child');
    assert.equal(harness.state.search, '');
    assert.equal(harness.state.folderDialog.visible, false);
    assert.equal(harness.state.folders.find(folder => folder.id === 'child').parent_id, 'empty');
  } finally { harness.unmount(); }
});

function renderedComponent(file, dependencies) {
  const source = readFileSync(new URL(file, import.meta.url), 'utf8');
  const { descriptor } = parse(source);
  const script = compileScript(descriptor, { id: file, genDefaultAs: 'component' });
  const imports = Object.entries(script.imports);
  const component = new Function(...imports.map(([local]) => local),
    script.content.replace(/^import .+ from ["'].+["'];?$/gm, '') + '\nreturn component;',
  )(...imports.map(([, entry]) => dependencies[entry.source][entry.imported]));
  const template = compileTemplate({
    source: descriptor.template.content, filename: file, id: file,
    compilerOptions: { mode: 'function', bindingMetadata: script.bindings },
  });
  assert.deepEqual(template.errors, []);
  component.render = new Function('Vue', template.code)(vue);
  return component;
}

test('admin status filter retains explicit enable and disable operations', async () => {
  const writes = [];
  const documents = [
    { id: 'ready', retrieval_enabled: false },
    { id: 'active', retrieval_enabled: true },
  ];
  const component = renderedComponent('views/AdminDocumentsView.vue', {
    vue, '../documentDisplay': documentDisplay,
    '../api': { api: async (path, options) => {
      if (options?.method === 'PATCH') {
        writes.push([path, options.json]);
        return { id: path.split('/').at(-1), ...options.json };
      }
      return path === '/admin/courses' ? [{ id: 'course', title: '课程' }] : documents;
    } },
  });
  const harness = await setupHarness(component);
  try {
    harness.state.retrievalFilter = 'disabled';
    assert.deepEqual(harness.state.filteredDocuments.map(doc => doc.id), ['ready']);
    await harness.state.toggle(harness.state.filteredDocuments[0]);
    assert.equal(harness.state.filteredDocuments.length, 0);
    harness.state.retrievalFilter = 'enabled';
    assert.equal(harness.state.filteredDocuments.length, 2);
    await harness.state.toggle(harness.state.filteredDocuments.find(doc => doc.id === 'ready'));
    assert.deepEqual(writes, [
      ['/courses/course/documents/ready', { retrieval_enabled: true }],
      ['/courses/course/documents/ready', { retrieval_enabled: false }],
    ]);
  } finally { harness.unmount(); }
});

test('student rendering hides retrieval state and provides same-origin named downloads', async () => {
  const folderModule = { documentGroups, folderOptions, folderTree, folderParentOptions, libraryGroup, documentFolderTargets };
  const library = renderedComponent('components/FolderLibrary.vue', {
    vue, '../documentFolders': folderModule,
  });
  const student = renderedComponent('components/StudentDocuments.vue', {
    vue, './FolderLibrary.vue': { default: library },
    '../documentDisplay': documentDisplay, '../documentFolders': folderModule,
  });
  const documents = [
    { id: 'enabled', filename: '讲义.pdf', retrieval_enabled: true, folder_id: 'child', job_status: 'succeeded', source_unit_count: 12 },
    { id: 'disabled', filename: '补充材料.txt', retrieval_enabled: false, folder_id: null, job_status: 'succeeded' },
    { id: 'pending', filename: '待处理.pdf', retrieval_enabled: false, folder_id: 'root', job_status: 'pending' },
  ];
  const app = vue.createSSRApp(student, { documents, folders, courseId: 'course' });
  app.directive('loading', {});
  app.component('ElTree', { render: () => null });
  app.component('ElInput', { render: () => null });
  for (const name of ['ElAlert', 'ElButton', 'ElEmpty']) app.component(name, { render: () => null });
  app.component('RouterLink', { render() { return vue.h('a', null, this.$slots.default?.()); } });
  const html = await renderToString(app);
  assert.doesNotMatch(html, /检索|启用|停用|刷新资料/);
  assert.match(html, /全部资料/);
  assert.match(html, /讲义 \/ 第一章/);
  assert.match(html, /href="\/courses\/course\/documents\/enabled\/content#page=1"/);
  assert.match(html, /href="\/courses\/course\/documents\/enabled\/content" download="讲义.pdf"/);
  assert.match(html, /href="\/courses\/course\/documents\/disabled\/content" download="补充材料.txt"/);
  assert.doesNotMatch(html, /download="待处理.pdf"/);
});

test('shared library rendering searches the whole course and leaves folder selection intact', async () => {
  const library = renderedComponent('components/FolderLibrary.vue', {
    vue, '../documentFolders': { documentGroups, folderTree, libraryGroup },
  });
  const documents = [
    { id: 'match', filename: 'outside.PDF', folder_id: 'child' },
    { id: 'other', filename: 'other.txt', folder_id: 'root' },
  ];
  const render = async search => {
    const app = vue.createSSRApp({ render: () => vue.h(library,
      { documents, folders, modelValue: 'empty', search },
      { default: ({ group }) => vue.h('p', group.documents.map(doc => doc.filename).join(',') || 'empty') },
    ) });
    app.directive('loading', {});
    app.component('ElTree', { props: ['currentNodeKey'], render() { return vue.h('span', { 'data-selected': this.currentNodeKey }); } });
    app.component('ElInput', { render: () => null });
    return renderToString(app);
  };
  const searching = await render('.pdf');
  assert.match(searching, /outside.PDF/);
  assert.match(searching, /data-selected="empty"/);
  assert.match(searching, /整课匹配 1 份资料/);
  assert.doesNotMatch(await render(''), /outside.PDF/);
});

for (const file of ['views/DocumentsView.vue', 'components/StudentDocuments.vue', 'views/AdminDocumentsView.vue', 'components/FolderLibrary.vue']) {
  test(`${file} compiles its script and template`, () => {
    const source = readFileSync(new URL(file, import.meta.url), 'utf8');
    const { descriptor, errors } = parse(source, { filename: file });
    assert.deepEqual(errors, []);
    const script = compileScript(descriptor, { id: file });
    const template = compileTemplate({
      source: descriptor.template.content, filename: file, id: file,
      compilerOptions: { bindingMetadata: script.bindings },
    });
    assert.deepEqual(template.errors, []);
  });
}

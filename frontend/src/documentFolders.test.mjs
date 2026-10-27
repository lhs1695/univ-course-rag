import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc';
import * as vue from 'vue';
import { documentGroups, folderOptions, folderTree, folderParentOptions } from './documentFolders.js';

const folders = [
  { id: 'child', parent_id: 'root', name: '第一章' },
  { id: 'root', parent_id: null, name: '讲义' },
  { id: 'empty', parent_id: null, name: '练习' },
];

test('folders preserve two-level order and distinguish matching child names', () => {
  assert.deepEqual(folderOptions(folders).map(folder => folder.label), ['讲义', '讲义 / 第一章', '练习']);
});

test('grouped documents include empty folders and ungrouped documents exactly once', () => {
  const documents = [
    { id: 'd1', folder_id: 'child' },
    { id: 'd2', folder_id: null },
    { id: 'd3', folder_id: 'root' },
  ];
  const groups = documentGroups(documents, folders);
  assert.deepEqual(groups.map(group => [group.label, group.documents.map(doc => doc.id)]), [
    ['讲义', ['d3']], ['讲义 / 第一章', ['d1']], ['练习', []], ['未分组', ['d2']],
  ]);
});

test('a list refresh race retains documents whose folder was not in the folder snapshot', () => {
  const groups = documentGroups([{ id: 'd', folder_id: 'new', folder_name: '新夹' }], []);
  assert.equal(groups.find(group => group.id === 'new').label, '新夹');
  assert.equal(groups.flatMap(group => group.documents).length, 1);
});

test('sidebar tree keeps two levels, direct counts, empty folders and refresh-race documents', () => {
  const tree = folderTree(documentGroups([
    { id: 'd1', folder_id: 'child' }, { id: 'd2', folder_id: null },
    { id: 'd3', folder_id: 'unknown', folder_name: '新资料夹' },
  ], folders));
  assert.deepEqual(tree.map(node => [node.value, node.label, node.count]), [
    ['', '未分组', 1], ['root', '讲义', 0], ['empty', '练习', 0], ['unknown', '新资料夹', 1],
  ]);
  assert.deepEqual(tree[1].children.map(node => [node.value, node.label, node.count]), [['child', '第一章', 1]]);
  assert.ok(tree[1].children.every(node => !node.children));
  assert.equal(new Set(tree.flatMap(node => [node.key, ...(node.children || []).map(child => child.key)])).size, 5);
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
    '../documentDisplay': { clampDocumentPage: () => 1, documentContentUrl: () => '', isPdfDocument: () => false },
    '../documentFolders': { documentGroups, folderOptions, folderTree, folderParentOptions },
    'vue-router': { useRoute: () => ({ params: { courseId: 'course' } }) },
    'element-plus': { ElMessage: { success() {}, error() {}, info() {} }, ElMessageBox: { confirm: async () => {} } },
    '../components/StudentDocuments.vue': { default: {} },
    '../components/FolderLibrary.vue': { default: {} },
  };
  const imports = Object.entries(script.imports);
  const component = new Function(...imports.map(([local]) => local),
    script.content.replace(/^import .+ from ["'].+["'];?$/gm, '') + '\nreturn component;',
  )(...imports.map(([, entry]) => dependencies[entry.source][entry.imported]));
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
    harness.state.documents = [{ ...original }]; // A poll replaces the row while the dialog is open.
    harness.state.documentMove.targetId = 'empty';
    await harness.state.moveDocument();
    assert.equal(harness.state.documents[0].folder_id, 'empty');
    assert.equal(harness.state.documents[0].retrieval_enabled, false);
    assert.equal(harness.state.selectedFolderId, 'empty');
    assert.equal(harness.state.documentMove.visible, false);
  } finally { harness.unmount(); }
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

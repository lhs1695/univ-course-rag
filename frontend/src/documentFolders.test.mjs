import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc';
import { documentGroups, folderOptions } from './documentFolders.js';

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

for (const file of ['views/DocumentsView.vue', 'components/StudentDocuments.vue', 'views/AdminDocumentsView.vue']) {
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

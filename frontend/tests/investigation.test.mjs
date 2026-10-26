import assert from 'node:assert/strict';
import { test } from 'node:test';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { runInNewContext } from 'node:vm';
import { investigationApi } from '../src/api.js';
import { citationUrl } from '../src/citationDisplay.js';

const require = createRequire(new URL('../package.json', import.meta.url));
const { parse, compileScript, compileTemplate } = require('@vue/compiler-sfc');
const view = readFileSync(new URL('../src/views/InvestigationView.vue', import.meta.url), 'utf8');

test('read preserves safe event metadata from the course-scoped events endpoint', async () => {
  const original = globalThis.fetch;
  const paths = [];
  const events = [{ sequence: 1, attempt: 2, step_no: 3, event_type: 'step_finished', tool_name: 'read_evidence', duration_ms: 0, safe_summary: 'Evidence checked', error_code: null, created_at: '2026-10-26T02:00:00Z', evidence_refs: [{ page: 3 }] }];
  globalThis.fetch = async path => {
    paths.push(path);
    return { ok: true, status: 200, json: async () => path.endsWith('/events') ? events : { task_id: 't' } };
  };
  try {
    assert.deepEqual(await investigationApi.read('c', 't'), { task_id: 't', events });
    assert.deepEqual(paths, ['/courses/c/agent-tasks/t', '/courses/c/agent-tasks/t/events']);
  } finally { globalThis.fetch = original; }
});

test('investigation SFC compiles the read-only timeline and formats local event times', () => {
  const { descriptor, errors } = parse(view);
  assert.deepEqual(errors, []);
  const script = compileScript(descriptor, { id: 'investigation-test' });
  const template = compileTemplate({ source: descriptor.template.content, filename: 'InvestigationView.vue', id: 'investigation-test', compilerOptions: { bindingMetadata: script.bindings } });
  assert.deepEqual(template.errors, []);
  for (const field of ['attempt', 'step_no', 'event_type', 'tool_name', 'duration_ms', 'safe_summary', 'error_code', 'created_at']) {
    assert.ok(descriptor.template.content.includes(`event.${field}`), field);
  }
  assert.match(descriptor.template.content, /event\.duration_ms != null/);
  const source = view.match(/function eventTime\(value\) \{[\s\S]*?\n\}/)[0];
  const format = runInNewContext(`(${source})`);
  assert.equal(format(null), '时间未知');
  assert.equal(format('invalid'), '时间未知');
  assert.equal(format('2026-10-26T02:00:00Z'), new Date('2026-10-26T02:00:00Z').toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }));
});

test('unconfirmed creation/resume/retry reject before fetch; external calls remain zero', async () => {
  const original = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls++; throw new Error('must not fetch'); };
  try {
    await assert.rejects(investigationApi.create('course', { confirm_external_processing: false }), /勾选/);
    await assert.rejects(investigationApi.action('course', 'task', 'resume', false), /勾选/);
    await assert.rejects(investigationApi.action('course', 'task', 'retry', false), /勾选/);
    assert.equal(calls, 0);
  } finally { globalThis.fetch = original; }
});

test('PDF references keep authorized content_url and exact page fragment', () => {
  assert.equal(citationUrl({ content_url: '/courses/c/documents/d/content', page: 3 }), '/courses/c/documents/d/content#page=3');
  assert.equal(citationUrl({ content_url: '/courses/c/documents/d/content', page: null }), '/courses/c/documents/d/content');
});

test('retry and run use explicit endpoints and cookies', async () => {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options) => {
    calls.push([path, options]);
    return { ok: true, status: 200, json: async () => ({ status: 'queued' }) };
  };
  try {
    await investigationApi.action('c', 't', 'retry', true);
    await investigationApi.action('c', 't', 'run', true, 'replay');
    assert.deepEqual(calls.map(c => c[0]), ['/courses/c/agent-tasks/t/retry', '/courses/c/agent-tasks/t/run']);
    assert.equal(calls[0][1].credentials, 'include');
    assert.equal(JSON.parse(calls[1][1].body).mode, 'replay');
  } finally { globalThis.fetch = original; }
});

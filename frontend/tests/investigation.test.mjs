import assert from 'node:assert/strict';
import { test } from 'node:test';
import { investigationApi } from '../src/api.js';
import { citationUrl } from '../src/citationDisplay.js';

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

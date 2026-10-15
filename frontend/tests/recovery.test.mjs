import assert from 'node:assert/strict';
import { test } from 'node:test';

globalThis.window = new EventTarget();
const { api, ApiError } = await import('../src/api.js');
const { session, refreshMe, logout } = await import('../src/session.js');
const { courseAccess } = await import('../src/courseAccess.js');
const { questionDraft, clearDrafts } = await import('../src/drafts.js');
const { default: viteConfig } = await import('../vite.config.js');
const reply = (body, status = 200) => new Response(JSON.stringify(body), { status });
const user = { id: 'synthetic-user', role: 'teacher' };

test('HTTP errors use safe categories and never display arbitrary server details', async () => {
  for (const status of [400, 401, 403, 404, 409, 413, 422, 500, 503, 504]) {
    globalThis.fetch = async () => reply({ detail: 'private-path-and-provider-secret' }, status);
    await assert.rejects(api('/not-a-course'), error => error.status === status && !error.message.includes('private'));
  }
  globalThis.fetch = async () => reply({ error_code: 'MODEL_NOT_CONFIGURED', message: 'raw-secret' }, 503);
  await assert.rejects(api('/test'), error => error.code === 'MODEL_NOT_CONFIGURED' && !error.message.includes('raw-secret'));
});

test('question grouping limit is not reported as an oversized upload', async () => {
  globalThis.fetch = async () => reply({ error_code: 'QUESTION_GROUPING_LIMIT', message: 'raw-provider-detail' }, 413);
  await assert.rejects(
    api('/courses/course-one/insights/groups', { method: 'POST', json: { min_similarity: 0.5 } }),
    error => error.code === 'QUESTION_GROUPING_LIMIT'
      && error.message.includes('缩小时间范围')
      && !error.message.includes('15 MB')
      && !error.message.includes('raw-provider'),
  );
  globalThis.fetch = async () => reply({ detail: 'stored-path' }, 413);
  await assert.rejects(
    api('/courses/course-one/documents', { method: 'POST' }),
    error => error.message.includes('15 MB') && !error.message.includes('stored-path'),
  );
  globalThis.fetch = async () => reply({ error_code: 'QUESTION_GROUPING_DISABLED', message: 'raw' }, 503);
  await assert.rejects(
    api('/courses/course-one/insights/groups', { method: 'POST', json: {} }),
    error => error.code === 'QUESTION_GROUPING_DISABLED' && error.message.includes('尚未启用') && !error.message.includes('raw'),
  );
});

test('network failure and request timeout are distinct', async () => {
  globalThis.fetch = async () => { throw new TypeError('raw network details'); };
  await assert.rejects(api('/test'), error => error.code === 'NETWORK_ERROR' && error.status === 0);
  globalThis.fetch = async (url, { signal }) => new Promise((resolve, reject) => {
    signal.addEventListener('abort', () => reject(new Error('aborted')), { once: true });
  });
  await assert.rejects(api('/test', { timeoutMs: 5 }), error => error.code === 'REQUEST_TIMEOUT');
  globalThis.fetch = async (url, { signal }) => ({
    ok: true, status: 200,
    json: () => new Promise((resolve, reject) => {
      signal.addEventListener('abort', () => reject(new Error('body interrupted')), { once: true });
    }),
  });
  await assert.rejects(api('/test', { timeoutMs: 5 }), error => error.code === 'REQUEST_TIMEOUT');
});

test('in-flight writes are blocked; completion releases the lock for explicit retry', async () => {
  let finish;
  let calls = 0;
  globalThis.fetch = async () => { calls++; return new Promise(resolve => { finish = resolve; }); };
  const first = api('/write', { method: 'POST', json: {} });
  await assert.rejects(api('/write', { method: 'POST', json: {} }), error => error.code === 'REQUEST_IN_PROGRESS');
  assert.equal(calls, 1);
  finish(reply({ done: true }));
  await first;
  globalThis.fetch = async () => reply({ done: true });
  assert.deepEqual(await api('/write', { method: 'POST' }), { done: true });
});

test('transport failure during identity refresh preserves session and course state', async () => {
  session.user = user;
  courseAccess.course = { id: 'course-one', membership_role: 'teacher' };
  globalThis.fetch = async () => { throw new Error('offline'); };
  assert.equal(await refreshMe(), false);
  assert.equal(session.user.id, user.id);
  assert.equal(courseAccess.course.id, 'course-one');
  assert.equal(session.error.code, 'NETWORK_ERROR');
});

test('401 revokes session while a missing document does not revoke course membership', async () => {
  session.user = user;
  courseAccess.course = { id: 'course-one' };
  globalThis.fetch = async () => reply({ detail: 'Document not found' }, 404);
  await assert.rejects(api('/courses/course-one/documents/gone'), ApiError);
  assert.equal(courseAccess.course.id, 'course-one');
  globalThis.fetch = async () => reply({}, 401);
  await assert.rejects(api('/courses/course-one'), ApiError);
  assert.equal(session.user, null);
  assert.equal(courseAccess.course, null);
});

test('a late identity response cannot resurrect a logged-out session', async () => {
  let finish;
  session.user = user;
  globalThis.fetch = async path => path === '/auth/me'
    ? new Promise(resolve => { finish = resolve; }) : new Response(null, { status: 204 });
  const pending = refreshMe();
  await logout();
  finish(reply(user));
  await pending;
  assert.equal(session.user, null);
});

test('question drafts are in memory and isolated by identity and course', () => {
  clearDrafts();
  questionDraft('alice', 'course-one', 'synthetic question');
  assert.equal(questionDraft('alice', 'course-one'), 'synthetic question');
  assert.equal(questionDraft('alice', 'course-two'), '');
  assert.equal(questionDraft('bob', 'course-one'), '');
  clearDrafts();
});

test('Vite serves admin HTML pages while API calls and document downloads remain proxied', () => {
  const request = (accept, url = '/admin/courses') => ({ method: 'GET', url, headers: { accept } });
  assert.equal(viteConfig.server.proxy['/admin'].bypass(request('text/html')), '/index.html');
  assert.equal(viteConfig.server.proxy['/admin'].bypass(request('application/json')), undefined);
  assert.equal(viteConfig.server.proxy['/courses'].bypass(request('text/html', '/courses/c/documents/d/content')), undefined);
  assert.ok(viteConfig.server.proxy['/runtime']);
  assert.ok(viteConfig.server.proxy['/ready']);
});

import assert from 'node:assert/strict';
import { test } from 'node:test';
import { askStream } from '../src/api.js';
import { createAskHistory } from '../src/askHistory.js';

const frame = (event, data) => `event: ${event}\r\ndata: ${JSON.stringify(data)}\r\n\r\n`;
function reply(text) {
  const bytes = new TextEncoder().encode(text);
  let index = 0;
  return new Response(new ReadableStream({
    pull(controller) {
      if (index < bytes.length) controller.enqueue(bytes.slice(index, ++index));
      else controller.close();
    },
  }), { headers: { 'Content-Type': 'text/event-stream' } });
}

test('POST stream decodes split UTF-8 and CRLF frames, updates text then adopts final citations', async () => {
  const store = createAskHistory();
  const final = { answer: '课程回答', citations: [{ chunk_id: 'one', page: 4 }] };
  const seen = [];
  store.course('alice', 'a');
  store.subscribe(() => {
    const round = store.course('alice', 'a').rounds[0];
    if (round?.text) seen.push([round.text, round.pending]);
  });
  globalThis.fetch = async (path, options) => {
    assert.equal(path, '/courses/a/ask/stream');
    assert.equal(options.method, 'POST');
    assert.equal(options.credentials, 'include');
    assert.equal(options.headers.Accept, 'text/event-stream');
    return reply(frame('phase', { phase: 'generate' })
      + frame('delta', { text: '课程' }) + frame('delta', { text: '回答' }) + frame('final', final));
  };
  await store.ask('alice', 'a', '问题', askStream);
  assert.ok(seen.some(([text, pending]) => text === '课程' && pending));
  assert.deepEqual(store.course('alice', 'a').rounds[0].result, final);
  assert.equal(store.course('alice', 'a').rounds[0].pending, false);
});

test('EOF without terminal and timeout terminal remain failures; retry releases write lock', async () => {
  globalThis.fetch = async () => reply(frame('delta', { text: '未完成' }));
  await assert.rejects(askStream('/courses/a/ask', { method: 'POST', onEvent() {} }),
    error => error.code === 'STREAM_INCOMPLETE');
  globalThis.fetch = async () => reply(frame('error', { error_code: 'UPSTREAM_TIMEOUT', message: 'private' }));
  await assert.rejects(askStream('/courses/a/ask', { method: 'POST', onEvent() {} }),
    error => error.code === 'UPSTREAM_TIMEOUT' && !error.message.includes('private'));
  globalThis.fetch = async () => reply(frame('final', { answer: null, error_code: 'NO_EVIDENCE', citations: [] }));
  assert.equal((await askStream('/courses/a/ask', { method: 'POST', onEvent() {} })).error_code, 'NO_EVIDENCE');
});

test('cancel aborts the reader, clears pending and unlocks explicit retry', async () => {
  const store = createAskHistory();
  let aborted = false;
  globalThis.fetch = async (_, { signal }) => new Response(new ReadableStream({
    start(controller) {
      signal.addEventListener('abort', () => {
        aborted = true;
        controller.error(new Error('aborted'));
      }, { once: true });
    },
  }), { headers: { 'Content-Type': 'text/event-stream' } });
  const task = store.ask('alice', 'a', '保留问题', askStream);
  await new Promise(resolve => setTimeout(resolve, 0));
  store.cancel('alice', 'a');
  await task;
  const round = store.course('alice', 'a').rounds[0];
  assert.equal(aborted, true);
  assert.equal(round.pending, false);
  assert.equal(round.question, '保留问题');
  assert.match(round.failure, /中断/);
  assert.equal(round.result, null);
  globalThis.fetch = async () => reply(frame('final', { answer: '重试成功', citations: [] }));
  await store.ask('alice', 'a', '保留问题', askStream);
  assert.equal(store.course('alice', 'a').rounds[1].result.answer, '重试成功');
});

test('identity clear aborts the stream and discards late deltas', async () => {
  const store = createAskHistory();
  let options;
  let finish;
  const task = store.ask('alice', 'a', '私有问题', (_, args) => {
    options = args;
    return new Promise(resolve => { finish = resolve; });
  });
  store.clear();
  assert.equal(options.signal.aborted, true);
  options.onEvent('delta', { text: '不能泄漏' });
  finish({ answer: '不能泄漏' });
  await task;
  assert.equal(store.course('bob', 'a').rounds.length, 0);
});

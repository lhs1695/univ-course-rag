import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createAskHistory, askHistory, answerNotice, answerFailureMessage, roundStatus } from '../src/askHistory.js';
import { clearDrafts } from '../src/drafts.js';
import { ApiError } from '../src/api.js';

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

test('ordered history retains answers and citations, selects evidence and wires previous context', async () => {
  const store = createAskHistory();
  const calls = [];
  const result = { answer: '第一轮回答', citations: [{ chunk_id: 'one' }] };
  const request = async (url, options) => { calls.push({ url, ...options }); return result; };
  await store.ask('alice', 'a', '第一问', request);
  await store.ask('alice', 'a', '追问', request);
  assert.deepEqual(calls[0].json, { query: '第一问' });
  assert.deepEqual(calls[1].json, { query: '追问', previous_question: '第一问', previous_answer: '第一轮回答' });
  assert.equal(calls[1].url, '/courses/a/ask');
  const state = store.course('alice', 'a');
  assert.deepEqual(state.rounds.map(round => round.question), ['第一问', '追问']);
  store.select('alice', 'a', state.rounds[0].id);
  assert.equal(state.selectedId, state.rounds[0].id);
  assert.deepEqual(state.rounds[0].result.citations, result.citations);
  assert.equal(store.course('alice', 'b').rounds.length, 0);
  assert.equal(store.course('bob', 'a').rounds.length, 0);
  assert.equal(store.course('alice', 'a').rounds.length, 0);
});

test('in-flight request survives leaving a course and unsubscribing, with per-course duplicate protection', async () => {
  const store = createAskHistory();
  const pending = deferred();
  let calls = 0;
  let updates = 0;
  const unsubscribe = store.subscribe(() => updates++);
  const request = () => { calls++; return pending.promise; };
  const task = store.ask('alice', 'a', '等待问题', request);
  const state = store.course('alice', 'a');
  assert.equal(state.rounds[0].pending, true);
  assert.ok(state.rounds[0].startedAt <= Date.now());
  await store.ask('alice', 'a', '重复问题', request);
  assert.equal(calls, 1);
  unsubscribe();
  const previousUpdates = updates;
  await store.ask('alice', 'b', '另一课程', async () => ({ answer: 'b', citations: [] }));
  pending.resolve({ answer: '已返回', citations: [{ chunk_id: 'a' }] });
  await task;
  const restored = store.course('alice', 'a');
  assert.equal(restored.rounds.length, 1);
  assert.equal(restored.rounds[0].pending, false);
  assert.equal(restored.rounds[0].result.answer, '已返回');
  assert.equal(updates, previousUpdates);
});

test('identity changes and logout discard late responses, including logging back in as the same user', async () => {
  for (const changeIdentity of [false, true]) {
    const pending = deferred();
    const task = askHistory.ask('alice', 'a', 'private', () => pending.promise);
    if (changeIdentity) askHistory.course('bob', 'a');
    else clearDrafts();
    await askHistory.ask('alice', 'a', 'new session', async () => ({ answer: 'new', citations: [] }));
    pending.resolve({ answer: 'private old response' });
    await task;
    assert.deepEqual(askHistory.course('alice', 'a').rounds.map(round => round.result.answer), ['new']);
    clearDrafts();
    assert.equal(askHistory.course('alice', 'a').rounds.length, 0);
  }
  clearDrafts();
});

test('failed requests remain in history and unlock the course; refusals supply empty previous answer', async () => {
  const store = createAskHistory();
  await store.ask('alice', 'a', '失败问题', async () => { throw {}; });
  const state = store.course('alice', 'a');
  assert.equal(state.rounds[0].failure, answerFailureMessage);
  assert.equal(roundStatus(state.rounds[0]), '请求失败');
  await store.ask('alice', 'a', '再试', async (_, { json }) => {
    assert.equal(json.previous_answer, '');
    return { error_code: 'NEEDS_CONTEXT', message: '请说明指哪个概念' };
  });
  assert.equal(state.rounds.length, 2);
  assert.equal(roundStatus(state.rounds[1]), '待补充上下文');
});

test('upstream error message survives failure and explicit retry remains available', async () => {
  const store = createAskHistory();
  const message = '上游 AI 服务暂时不可用，请稍后重试。';
  const error = new ApiError(message, 503, 'UPSTREAM_UNAVAILABLE');
  error.stack = 'private stack';
  await store.ask('alice', 'a', '问题', async () => { throw error; });
  const state = store.course('alice', 'a');
  assert.equal(state.rounds[0].failure, message);
  assert.equal(state.rounds[0].pending, false);
  assert.equal(roundStatus(state.rounds[0]), '请求失败');
  await store.ask('alice', 'a', '问题', async () => ({ answer: '重试成功' }));
  assert.equal(state.rounds[1].result.answer, '重试成功');
});

test('context and invalid-question warnings preserve backend messages; system failures remain generic', () => {
  for (const error_code of ['NEEDS_CONTEXT', 'INVALID_QUESTION']) {
    assert.deepEqual(answerNotice({ error_code, message: '后端原文' }), { type: 'warning', message: '后端原文' });
  }
  assert.equal(answerNotice({ error_code: 'NO_EVIDENCE', message: 'other' }).message, '课内资料依据不足，暂时无法据此回答。');
  assert.deepEqual(answerNotice({ error_code: 'MODEL_ERROR', message: 'secret' }), { type: 'error', message: answerFailureMessage });
  assert.deepEqual(answerNotice({ message: '请补充问题' }), { type: 'warning', message: '请补充问题' });
  assert.equal(answerNotice({ answer: 'ok' }), null);
});

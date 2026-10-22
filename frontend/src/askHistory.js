export const answerFailureMessage = '暂时无法完成这次回答，请稍后重试。';

export function answerNotice(result) {
  if (result?.error_code === 'NO_EVIDENCE') {
    return { type: 'warning', message: '课内资料依据不足，暂时无法据此回答。' };
  }
  if (['NEEDS_CONTEXT', 'INVALID_QUESTION'].includes(result?.error_code)) {
    return { type: 'warning', message: result.message || '请补充或调整问题后再试。' };
  }
  if (result?.error_code) return { type: 'error', message: answerFailureMessage };
  if (result?.message) return { type: 'warning', message: result.message };
  return null;
}

export function roundStatus(round) {
  if (round.pending) return '回答中';
  if (round.failure) return '请求失败';
  const notice = answerNotice(round.result);
  if (notice?.type === 'error') return '回答失败';
  if (round.result?.error_code === 'NEEDS_CONTEXT') return '待补充上下文';
  if (round.result?.error_code === 'INVALID_QUESTION') return '请调整问题';
  if (notice) return '未作答';
  return '已回答';
}

// Own requests independently of any mounted view. A new identity discards all
// previous state; generation checks also discard late responses after logout.
export function createAskHistory() {
  let ownerId = null;
  let generation = 0;
  let nextId = 0;
  const courses = new Map();
  const listeners = new Set();
  const controllers = new Map();
  const notify = () => listeners.forEach(listener => listener());
  function clear() {
    generation++;
    controllers.forEach(controller => controller.abort());
    controllers.clear();
    courses.clear();
    ownerId = null;
    notify();
  }
  function course(userId, courseId) {
    if (ownerId !== userId) {
      clear();
      ownerId = userId;
    }
    if (!courses.has(courseId)) courses.set(courseId, { rounds: [], selectedId: null });
    return courses.get(courseId);
  }
  function select(userId, courseId, id) {
    const state = course(userId, courseId);
    if (state.rounds.some(round => round.id === id)) {
      state.selectedId = id;
      notify();
    }
  }
  async function ask(userId, courseId, query, request) {
    const state = course(userId, courseId);
    if (state.rounds.some(round => round.pending) || !query.trim()) return;
    const previous = state.rounds.at(-1);
    const json = { query };
    if (previous) {
      json.previous_question = previous.question;
      json.previous_answer = previous.result?.answer || '';
    }
    const round = { id: ++nextId, question: query, result: null, failure: '', pending: true,
      startedAt: Date.now(), text: '', phase: 'retrieve' };
    const controller = new AbortController();
    controllers.set(round.id, controller);
    const requestGeneration = generation;
    state.rounds.push(round);
    state.selectedId = round.id;
    notify();
    try {
      const result = await request(`/courses/${courseId}/ask`, {
        method: 'POST', json, timeoutMs: 300000, signal: controller.signal,
        onEvent(event, payload) {
          if (generation !== requestGeneration || controller.signal.aborted) return;
          if (event === 'delta') round.text += payload.text;
          if (event === 'phase') round.phase = payload.phase;
          notify();
        },
      });
      if (generation === requestGeneration) round.result = result;
    } catch (error) {
      if (generation === requestGeneration) round.failure = error?.message || answerFailureMessage;
    } finally {
      controllers.delete(round.id);
      if (generation === requestGeneration) {
        round.pending = false;
        notify();
      }
    }
  }
  function cancel(userId, courseId) {
    const state = course(userId, courseId);
    state.rounds.filter(round => round.pending).forEach(round => controllers.get(round.id)?.abort());
  }
  return { course, ask, select, clear, cancel, subscribe(listener) {
    listeners.add(listener);
    return () => listeners.delete(listener);
  } };
}

export const askHistory = createAskHistory();

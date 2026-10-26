import assert from 'node:assert/strict';
import { test } from 'node:test';
import { createStudentSurface, STUDENT_SURFACE_KEY } from '../src/theme.js';

test('first visit defaults to study; a new instance restores the selected surface', () => {
  const values = new Map();
  const storage = { getItem: key => values.get(key), setItem: (key, value) => values.set(key, value) };
  const first = createStudentSurface(storage);
  assert.equal(first.surface.value, 'study');
  first.select('ask');
  assert.equal(values.get(STUDENT_SURFACE_KEY), 'ask');
  const refreshed = createStudentSurface(storage);
  assert.equal(refreshed.surface.value, 'ask');
  refreshed.select('study');
  assert.equal(createStudentSurface(storage).surface.value, 'study');
});

test('invalid saved values fall back to study and invalid selections are ignored', () => {
  let writes = 0;
  const state = createStudentSurface({ getItem: () => 'ce', setItem: () => writes++ });
  assert.equal(state.surface.value, 'study');
  state.select('balance');
  assert.equal(state.surface.value, 'study');
  assert.equal(writes, 0);
});

test('blocked or unavailable localStorage keeps the theme control usable in memory', () => {
  for (const storage of [null, { getItem() { throw new Error('blocked'); }, setItem() { throw new Error('full'); } }]) {
    const state = createStudentSurface(storage);
    assert.equal(state.surface.value, 'study');
    state.select('ask');
    assert.equal(state.surface.value, 'ask');
  }
});

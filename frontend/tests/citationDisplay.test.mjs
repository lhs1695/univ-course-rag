import assert from 'node:assert/strict';
import { test } from 'node:test';
import { cleanExcerpt, citationTitle, citationPageLabel, citationOpenLabel } from '../src/citationDisplay.js';

test('excerpts remove extraction artifacts while retaining readable content', () => {
  assert.equal(cleanExcerpt('Ġ矩阵\u200b是\x01数的排列。\n\t可用于计算。', 3), '矩阵是数的排列。\n 可用于计算。');
  assert.equal(cleanExcerpt('A matrix has rows and columns.', 3), 'A matrix has rows and columns.');
  assert.equal(cleanExcerpt('行列式', 3), '行列式');
});

test('garbled matrices degrade with source page; absent pages never become zero', () => {
  assert.equal(cleanExcerpt('" # a " # b " # c', 60), '摘录含公式或版式噪声，请打开原文 第 60 页核对。');
  assert.equal(cleanExcerpt('###', null), '摘录含公式或版式噪声，请打开原文 核对。');
});

test('titles retain original identity through a friendly display name', () => {
  assert.equal(citationTitle('01-linear-algebra-full.pdf'), '线性代数讲义');
  assert.equal(citationTitle('chapter_2-introduction.PDF'), 'chapter 2 introduction');
});

test('page and open labels support sources with or without pages', () => {
  assert.equal(citationPageLabel(10), '第 10 页');
  assert.equal(citationPageLabel(null), '原资料');
  assert.equal(citationOpenLabel(10), '打开原文 · 第 10 页');
  assert.equal(citationOpenLabel(undefined), '打开原文');
});

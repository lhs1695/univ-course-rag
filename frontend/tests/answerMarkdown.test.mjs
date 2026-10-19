import assert from 'node:assert/strict';
import { test } from 'node:test';
import { renderAnswer } from '../src/answerMarkdown.js';

const id = '12345678-1234-1234-1234-123456789abc';
const other = '00000000-0000-0000-0000-000000000000';
const citations = [{ chunk_id: id }];

test('Markdown formatting and repeated citations share the registered card number', () => {
  const html = renderAnswer(`## 概念\n**重点** [Source ${id.toUpperCase()}] 和 [${id}]`, citations);
  assert.match(html, /<h2>概念<\/h2>/);
  assert.match(html, /<strong>重点<\/strong>/);
  assert.equal((html.match(new RegExp(`href="#source-${id}"`, 'g')) || []).length, 2);
  assert.equal((html.match(/核对引用 1/g) || []).length, 2);
  assert.match(renderAnswer(`[Source ${other}]`, citations), /未登记引用/);
  assert.doesNotMatch(renderAnswer(`[Source ${other}]`, citations), /<a /);
  assert.doesNotMatch(renderAnswer(`[Source ${id}]`), /<a /);
});

test('raw HTML, event handlers, SVG, generated URLs and images remain inert', () => {
  const html = renderAnswer([
    '<script>alert(1)</script>', '<img src=x onerror=alert(1)>',
    '<svg onload=alert(1)>', '<iframe srcdoc="<script>alert(1)</script>">',
    '[打开](javascript:alert(1))', '[打开](https://example.com)',
    '![图](https://example.com/tracker.png)', '<https://example.com>',
    '&lt;img src=x onerror=alert(1)&gt;',
    '```html\n<img src=x onerror=alert(1)>\n```',
  ].join('\n\n'), citations);
  assert.doesNotMatch(html, /<(?:script|img|svg|iframe|a)\b/i);
  assert.match(html, /&lt;script&gt;/);
  assert.match(html, /<pre><code/);
});

test('code and escaped source markers stay literal; user markup cannot forge card attributes', () => {
  const html = renderAnswer(`\`[Source ${id}]\`\n\n\`\`\`\n[Source ${id}]\n\`\`\`\n\n\\[Source ${id}]\n\n<a data-source-id="${id}" href="#source-${id}">伪造</a>`, citations);
  assert.doesNotMatch(html, /<a\b/);
  assert.match(html, /&lt;a /);
  assert.match(html, /<code>\[Source /);
});

test('tables and nested lists use the package renderer', () => {
  const html = renderAnswer('| 项 | 值 |\n| --- | --- |\n| A | 1 |\n\n- 一\n  - 二');
  assert.match(html, /<table>/);
  assert.equal((html.match(/<ul>/g) || []).length, 2);
});

test('inline dollar math renders within Chinese text', () => {
  const html = renderAnswer('平方为 $x^2$。');
  assert.match(html, /class="katex"/);
  assert.match(html, /class="katex-html"/);
  assert.doesNotMatch(html, /katex-mathml|<math|<annotation|aria-hidden/);
  assert.doesNotMatch(html, /katex-display|katex-error/);
});

test('display dollar math renders across lines', () => {
  const html = renderAnswer('公式：\n\n$$\nx^2 + y^2 = z^2\n$$');
  assert.match(html, /class="katex-display"/);
  assert.match(html, /class="katex"/);
  assert.doesNotMatch(html, /katex-error/);
});

test('backslash parentheses render inline math', () => {
  const html = renderAnswer(String.raw`平方为 \(x^2\)。`);
  assert.match(html, /class="katex"/);
  assert.match(html, /class="katex-html"/);
  assert.doesNotMatch(html, /katex-mathml|<math|<annotation|aria-hidden/);
  assert.doesNotMatch(html, /katex-error/);
});

test('ordinary parentheses containing TeX render fractions', () => {
  const html = renderAnswer(String.raw`结果为 (\frac{f(x)}{2})。`);
  assert.match(html, /class="katex"/);
  assert.match(html, /class="mfrac"/);
  assert.doesNotMatch(html, /katex-error/);
});

test('ordinary Chinese parentheses and plain text remain unchanged', () => {
  assert.equal(renderAnswer('定义（这是普通中文括号）与(补充说明)。'),
    '<p>定义（这是普通中文括号）与(补充说明)。</p>\n');
  assert.equal(renderAnswer('正常中文文本，无公式。'), '<p>正常中文文本，无公式。</p>\n');
});

test('script remains escaped in the same paragraph as math', () => {
  const html = renderAnswer('<script>alert(1)</script> 与 $x^2$。');
  assert.match(html, /class="katex"/);
  assert.match(html, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/);
  assert.doesNotMatch(html, /<script\b/i);
});

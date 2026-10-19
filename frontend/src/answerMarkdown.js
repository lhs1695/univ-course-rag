import MarkdownIt from 'markdown-it';
import katex from 'katex';

// Untrusted Markdown never enables HTML, arbitrary links or images.
const markdown = new MarkdownIt({ html: false, linkify: false, typographer: false });

function renderMath(tokens, index) {
  const token = tokens[index];
  try {
    const html = katex.renderToString(token.content, {
      displayMode: token.type === 'math_block', throwOnError: false, trust: false,
    });
    // KaTeX returns an error span for invalid TeX when throwOnError is false.
    if (!html.includes('class="katex-error"')) return html;
  } catch {
    // Unexpected parser failures must remain inert text as well.
  }
  return markdown.utils.escapeHtml(token.markup + token.content + token.meta);
}
markdown.renderer.rules.math_inline = renderMath;
markdown.renderer.rules.math_block = renderMath;

function closingAt(src, close, start, max) {
  for (let pos = src.indexOf(close, start); pos >= 0 && pos < max; pos = src.indexOf(close, pos + 1)) {
    let slashes = 0;
    for (let i = pos - 1; i >= 0 && src[i] === '\\'; i--) slashes++;
    if (slashes % 2 === 0) return pos;
  }
  return -1;
}

markdown.block.ruler.before('fence', 'math_block', (state, startLine, endLine, silent) => {
  if (state.sCount[startLine] - state.blkIndent >= 4) return false;
  const start = state.bMarks[startLine] + state.tShift[startLine];
  const open = state.src.startsWith('$$', start) ? '$$' : '\\[';
  if (!state.src.startsWith(open, start)) return false;
  const close = open === '$$' ? '$$' : '\\]';
  const end = closingAt(state.src, close, start + open.length, state.eMarks[endLine - 1]);
  if (end < 0) return false;
  let lastLine = startLine;
  while (lastLine + 1 < endLine && state.bMarks[lastLine + 1] <= end) lastLine++;
  if (state.src.slice(end + close.length, state.eMarks[lastLine]).trim()) return false;
  if (silent) return true;
  const token = state.push('math_block', '', 0);
  token.block = true;
  token.map = [startLine, lastLine + 1];
  token.content = state.src.slice(start + open.length, end);
  token.markup = open;
  token.meta = close;
  state.line = lastLine + 1;
  return true;
}, { alt: ['paragraph', 'reference', 'blockquote', 'list'] });

// Let markdown-it keep its own text/escape/code rules, stopping text at possible
// math openers so formulas embedded in a Chinese sentence reach our math rule.
const textRule = markdown.inline.ruler.getRules('')[0];
markdown.inline.ruler.at('text', (state, silent) => {
  const max = state.posMax;
  const next = state.src.slice(state.pos + 1, max).search(/[$(]/);
  if (next >= 0) state.posMax = state.pos + 1 + next;
  try { return textRule(state, silent); } finally { state.posMax = max; }
});
markdown.inline.ruler.before('text', 'math_inline', (state, silent) => {
  const start = state.pos;
  const src = state.src;
  const open = ['$$', '\\[', '\\(', '$', '('].find((value) => src.startsWith(value, start));
  if (!open) return false;
  const close = { '$$': '$$', '\\[': '\\]', '\\(': '\\)', '$': '$', '(': ')' }[open];
  // Ordinary parentheses may contain nested parentheses, e.g. (\\frac{f(x)}{2}).
  let end;
  if (open === '(') {
    let depth = 1;
    for (end = start + 1; end < state.posMax && depth; end++) {
      if (src[end] === '(') depth++;
      if (src[end] === ')') depth--;
    }
    end = depth ? -1 : end - 1;
  } else {
    end = closingAt(src, close, start + open.length, state.posMax);
  }
  if (end < 0) return false;
  const content = src.slice(start + open.length, end);
  if (!content.trim() || (open === '(' && !/\\[a-zA-Z]+/.test(content))) return false;
  if ((open === '$' || open === '(' || open === '\\(') && content.includes('\n')) return false;
  // Avoid treating prices such as "$5 and $10" as a formula.
  if (open === '$' && (/^\s|\s$/.test(content) || /\d/.test(src[end + 1] || ''))) return false;
  if (!silent) {
    const token = state.push(open === '$$' || open === '\\[' ? 'math_block' : 'math_inline', '', 0);
    token.content = content;
    token.markup = open;
    token.meta = close;
  }
  state.pos = end + close.length;
  return true;
});
const sourceMarker = /^\[(?:Source\s+)?([\da-f]{8}-[\da-f]{4}-[\da-f]{4}-[\da-f]{4}-[\da-f]{12})\]/i;
markdown.inline.ruler.before('link', 'source_citation', (state, silent) => {
  const match = sourceMarker.exec(state.src.slice(state.pos));
  if (!match) return false;
  if (!silent) {
    const token = state.push('source_citation', '', 0);
    token.content = match[1].toLowerCase();
  }
  state.pos += match[0].length;
  return true;
});
markdown.disable(['link', 'image', 'autolink']);
markdown.renderer.rules.source_citation = (tokens, index, options, env) => {
  const id = tokens[index].content; // Only a UUID can reach an HTML attribute.
  const number = env.sources.get(id);
  if (!number) return '<span class="unknown-citation">[未登记引用]</span>';
  return `<a class="inline-citation" href="#source-${id}" data-source-id="${id}" aria-label="核对引用 ${number}">[${number}]</a>`;
};

export function renderAnswer(answer, citations = []) {
  const sources = new Map(citations.map((item, index) => [item.chunk_id.toLowerCase(), index + 1]));
  return markdown.render(String(answer || ''), { sources });
}

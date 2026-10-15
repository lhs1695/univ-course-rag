import MarkdownIt from 'markdown-it';

// Untrusted Markdown never enables HTML, arbitrary links, images or plugins.
const markdown = new MarkdownIt({ html: false, linkify: false, typographer: false });
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

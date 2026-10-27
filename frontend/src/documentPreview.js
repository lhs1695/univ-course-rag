import MarkdownIt from "markdown-it";

const markdown = new MarkdownIt({ html: false, linkify: true, breaks: true });
// Course text must not cause remote image requests while being read.
markdown.renderer.rules.image = (tokens, index) => markdown.utils.escapeHtml(tokens[index].content || "图片");

export function previewFormat(filename) {
  const extension = String(filename || "").split(".").pop().toLowerCase();
  return extension === "markdown" ? "md" : extension;
}

export function previewPage(value, count) {
  const page = Math.max(1, Number.parseInt(value, 10) || 1);
  return count > 0 ? Math.min(page, count) : page;
}

export function renderDocumentMarkdown(text) {
  return markdown.render(String(text || ""));
}

export function textPreviewPages(text) {
  // Respect explicit form feeds; otherwise keep paragraphs together in readable sections.
  const pages = [];
  for (const section of String(text).split(/\f|\n(?=#{1,2} )/)) {
    let page = '';
    for (const paragraph of section.split('\n\n')) {
      if (page && page.length + paragraph.length > 6000) { pages.push(page); page = ''; }
      page += (page ? '\n\n' : '') + paragraph;
    }
    if (page.trim()) pages.push(page);
  }
  return pages;
}

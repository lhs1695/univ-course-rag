// Display only: preserve the API excerpt for evidence and source inspection.
export function cleanExcerpt(text, page) {
  const raw = String(text || '');
  const clean = raw
    .replace(/[Ġ\u200b-\u200f\u202a-\u202e\u2060-\u206f\ufeff\ufffd\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/g, '')
    .replace(/(?:["#`|\\]\s*){2,}/g, ' ')
    .replace(/[ \t]+/g, ' ')
    .replace(/\n{3,}/g, '\n\n').trim();
  const compact = clean.replace(/\s/g, '');
  const meaningful = compact.match(/[\p{L}\p{N}]/gu)?.length || 0;
  const junkRuns = raw.match(/(?:["#`|\\]\s*){2,}/g)?.length || 0;
  if (!meaningful || meaningful / compact.length < 0.45 || junkRuns >= 3 ||
      (meaningful < 12 && /["#`|\\=∑∫]/.test(raw))) {
    const sourcePage = Number.isInteger(Number(page)) && Number(page) > 0 ? ` 第 ${Number(page)} 页` : ' ';
    return `摘录含公式或版式噪声，请打开原 PDF${sourcePage}核对。`;
  }
  return clean;
}

export function citationTitle(filename) {
  if (filename === '01-linear-algebra-full.pdf') return '线性代数讲义';
  return String(filename || '课程资料').replace(/\.[a-z0-9]+$/i, '').replace(/[-_]+/g, ' ').trim() || '课程资料';
}

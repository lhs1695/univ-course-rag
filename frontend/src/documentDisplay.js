export function isPdfDocument(document) {
  return String(document?.filename || "").toLowerCase().endsWith(".pdf");
}

function isPptxDocument(document) {
  return String(document?.filename || "").toLowerCase().endsWith(".pptx");
}

export function documentPageLabel(document) {
  const count = document?.source_unit_count;
  if (count == null) return "—";
  if (isPdfDocument(document)) return `${count} 页`;
  if (isPptxDocument(document)) return `${count} 张`;
  return "—";
}

export function documentCoverage(document) {
  if (document?.job_status === "succeeded") {
    if (document.quality_warning) {
      return { label: "建议核对原文", type: "warning" };
    }
    return { label: "正常", type: "success" };
  }
  if (document?.job_status === "failed") {
    return { label: "暂不可用", type: "danger" };
  }
  return { label: "处理中", type: "warning" };
}

/** Fixed, verifiable reason for teacher UI; never invents page numbers. */
export function documentCoverageHint(document) {
  if (document?.job_status !== "succeeded") return "";
  if (document.quality_warning === "COVERAGE_INCOMPLETE") {
    return "部分内容解析存疑，请打开原文核对。";
  }
  if (document.quality_warning === "LOW_EXTRACTED_TEXT") {
    return "抽取文字偏少，请打开原文核对。";
  }
  return document.quality_warning ? "请打开原文核对解析结果。" : "";
}

export function clampDocumentPage(page, document) {
  const parsed = Number.parseInt(page, 10);
  const safePage = Number.isFinite(parsed) ? parsed : 1;
  const max = document?.source_unit_count;
  const upper = Number.isFinite(max) && max >= 1 ? max : null;
  if (safePage < 1) return 1;
  return upper == null ? safePage : Math.min(safePage, upper);
}

export function documentContentUrl(courseId, document, page = 1) {
  const base = `/courses/${courseId}/documents/${document.id}/content`;
  if (!isPdfDocument(document)) return base;
  return `${base}#page=${clampDocumentPage(page, document)}`;
}

export function documentQualityLabel(document) {
  return document?.job_status === "succeeded" ? documentCoverage(document).label : "—";
}

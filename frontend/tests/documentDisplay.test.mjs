import assert from "node:assert/strict";
import { test } from "node:test";
import {
  clampDocumentPage,
  documentContentUrl,
  documentCoverage,
  documentPageLabel,
  documentQualityLabel,
  isPdfDocument,
} from "../src/documentDisplay.js";

const pdf = { id: "doc-1", filename: "lecture.pdf", source_unit_count: 12, job_status: "succeeded", quality_warning: null };

test("page label only calls PDF source units pages", () => {
  assert.equal(documentPageLabel(pdf), "12 页");
  assert.equal(documentPageLabel({ ...pdf, filename: "slides.pptx" }), "12 张");
  assert.equal(documentPageLabel({ ...pdf, filename: "notes.md" }), "—");
  assert.equal(documentPageLabel({ ...pdf, source_unit_count: null }), "—");
});

test("coverage maps ingest state to student-friendly labels", () => {
  assert.deepEqual(documentCoverage(pdf), { label: "已入库", type: "success" });
  assert.deepEqual(documentCoverage({ ...pdf, quality_warning: "COVERAGE_INCOMPLETE" }), { label: "已入库", type: "success" });
  assert.deepEqual(documentCoverage({ ...pdf, quality_warning: "LOW_EXTRACTED_TEXT" }), { label: "文本较少", type: "warning" });
  assert.deepEqual(documentCoverage({ ...pdf, job_status: "running" }), { label: "处理中", type: "warning" });
  assert.deepEqual(documentCoverage({ ...pdf, job_status: "failed" }), { label: "暂不可用", type: "danger" });
});

test("PDF content URL clamps page and non-PDF has no hash", () => {
  assert.equal(isPdfDocument(pdf), true);
  assert.equal(clampDocumentPage(0, pdf), 1);
  assert.equal(clampDocumentPage(99, pdf), 12);
  assert.equal(documentContentUrl("course-1", pdf, 3), "/courses/course-1/documents/doc-1/content#page=3");
  assert.equal(documentContentUrl("course-1", pdf, 99), "/courses/course-1/documents/doc-1/content#page=12");
  assert.equal(
    documentContentUrl("course-1", { id: "doc-2", filename: "notes.md", source_unit_count: 1 }, 5),
    "/courses/course-1/documents/doc-2/content",
  );
});

test("quality wording distinguishes PDF pages, slides and content units", () => {
  const row = { ...pdf, extracted_char_count: 100, chunk_count: 3 };
  assert.equal(documentQualityLabel(row), "共 12 页内容 · 抽取约 100 字 · 已切成 3 段供检索");
  assert.match(documentQualityLabel({ ...row, filename: "notes.md" }), /共 12 个内容单元/);
  assert.match(documentQualityLabel({ ...row, filename: "slides.pptx" }), /共 12 张幻灯片内容/);
});

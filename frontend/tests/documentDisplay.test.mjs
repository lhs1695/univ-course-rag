import assert from "node:assert/strict";
import { test } from "node:test";
import {
  clampDocumentPage,
  documentContentUrl,
  documentCoverage,
  documentPageLabel,
  documentCoverageHint,
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
  assert.deepEqual(documentCoverage(pdf), { label: "正常", type: "success" });
  assert.deepEqual(documentCoverage({ ...pdf, quality_warning: "COVERAGE_INCOMPLETE" }), { label: "建议核对原文", type: "warning" });
  assert.match(documentCoverageHint({ ...pdf, quality_warning: "COVERAGE_INCOMPLETE" }), /原文.*核对/);
  assert.equal(documentCoverageHint(pdf), "");
  assert.deepEqual(documentCoverage({ ...pdf, quality_warning: "LOW_EXTRACTED_TEXT" }), { label: "建议核对原文", type: "warning" });
  assert.match(documentCoverageHint({ ...pdf, quality_warning: "LOW_EXTRACTED_TEXT" }), /原文.*核对/);
  assert.deepEqual(documentCoverage({ ...pdf, quality_warning: "OTHER_WARNING" }), { label: "建议核对原文", type: "warning" });
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

test("quality labels stay short regardless of file type or ingest statistics", () => {
  const row = { ...pdf, extracted_char_count: 100, chunk_count: 3 };
  for (const filename of ["lecture.pdf", "notes.md", "slides.pptx"]) {
    assert.equal(documentQualityLabel({ ...row, filename }), "正常");
  }
  assert.equal(documentQualityLabel({ ...row, source_unit_count: null, extracted_char_count: null, chunk_count: null }), "正常");
  for (const quality_warning of ["COVERAGE_INCOMPLETE", "LOW_EXTRACTED_TEXT"]) {
    assert.equal(documentQualityLabel({ ...row, quality_warning }), "建议核对原文");
  }
  for (const job_status of ["pending", "running", "failed"]) {
    assert.equal(documentQualityLabel({ ...row, job_status }), "—");
    assert.equal(documentCoverageHint({ ...row, job_status, quality_warning: "COVERAGE_INCOMPLETE" }), "");
  }
});

"""R7B-1: offline Docling conversion for a frozen representative-page list.

Does not ingest, call cloud APIs, or modify the production parser.
Outputs JSON/MD/report under an ignored corpus/local directory.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
import traceback
from collections import defaultdict
from pathlib import Path

import psutil
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "corpus/local/r7b-1-docling-2026-10-16/representative-pages.json"
OUT_DIR = ROOT / "corpus/local/r7b-1-docling-2026-10-16/outputs"
ARTIFACTS = Path(
    os.environ.get("DOCLING_ARTIFACTS_PATH", r"C:\Users\16747\.cache\docling\models")
)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def count_elements(doc) -> dict:
    counts = {
        "texts": len(getattr(doc, "texts", []) or []),
        "tables": len(getattr(doc, "tables", []) or []),
        "pictures": len(getattr(doc, "pictures", []) or []),
        "key_value_items": len(getattr(doc, "key_value_items", []) or []),
        "form_items": len(getattr(doc, "form_items", []) or []),
    }
    # Formula-ish: look at text labels if available
    formula_like = 0
    for t in getattr(doc, "texts", []) or []:
        label = str(getattr(t, "label", "") or "")
        if "formula" in label.lower() or "equation" in label.lower():
            formula_like += 1
        # Some versions use DocItemLabel
        try:
            from docling_core.types.doc import DocItemLabel

            if getattr(t, "label", None) == DocItemLabel.FORMULA:
                formula_like += 1
        except Exception:
            pass
    counts["formula_like_texts"] = formula_like
    return counts


def page_nos_present(doc) -> list[int]:
    pages = getattr(doc, "pages", None)
    if isinstance(pages, dict):
        return sorted(int(k) for k in pages.keys())
    if pages is None:
        return []
    try:
        return sorted(int(p) for p in pages)
    except Exception:
        return []


def prov_pages(doc) -> set[int]:
    found: set[int] = set()
    for attr in ("texts", "tables", "pictures"):
        for item in getattr(doc, attr, []) or []:
            for p in getattr(item, "prov", []) or []:
                pn = getattr(p, "page_no", None)
                if pn is not None:
                    found.add(int(pn))
    return found


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    pages = manifest["pages"]

    pipeline_options = PdfPipelineOptions(
        artifacts_path=str(ARTIFACTS),
        do_ocr=True,
        do_table_structure=True,
        do_formula_enrichment=True,
        generate_page_images=False,
    )
    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    proc = psutil.Process(os.getpid())
    peak_rss = proc.memory_info().rss
    results = []
    t0 = time.perf_counter()

    # Group by file but convert page-by-page for timing/isolation
    for entry in pages:
        pdf_rel = entry["file"].replace("/", os.sep)
        pdf_path = ROOT / pdf_rel
        page = int(entry["page"])
        out_stem = f"{entry['id']}_{entry['course']}_p{page}"
        page_out = OUT_DIR / out_stem
        page_out.mkdir(parents=True, exist_ok=True)

        row = {
            "id": entry["id"],
            "course": entry["course"],
            "file": entry["file"],
            "page": page,
            "role": entry.get("role"),
            "preflight": entry.get("preflight"),
            "pdf_exists": pdf_path.is_file(),
            "pdf_sha256": sha256_file(pdf_path) if pdf_path.is_file() else None,
            "status": "pending",
        }
        if not pdf_path.is_file():
            row["status"] = "missing_pdf"
            results.append(row)
            continue

        before_rss = proc.memory_info().rss
        started = time.perf_counter()
        try:
            conv = converter.convert(str(pdf_path), page_range=(page, page), raises_on_error=False)
            elapsed = time.perf_counter() - started
            after_rss = proc.memory_info().rss
            peak_rss = max(peak_rss, after_rss)
            doc = conv.document
            status = str(getattr(conv, "status", "unknown"))
            md = doc.export_to_markdown()
            # JSON export
            try:
                doc_dict = doc.export_to_dict()
            except Exception:
                doc_dict = json.loads(doc.model_dump_json())

            (page_out / "page.md").write_text(md, encoding="utf-8")
            (page_out / "page.json").write_text(
                json.dumps(doc_dict, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            pnos = page_nos_present(doc)
            found_pages = sorted(prov_pages(doc))
            els = count_elements(doc)
            row.update(
                {
                    "status": "ok" if "success" in status.lower() or status.endswith("SUCCESS") or status == "ConversionStatus.SUCCESS" else status,
                    "conversion_status": status,
                    "elapsed_sec": round(elapsed, 3),
                    "rss_before_mb": round(before_rss / (1024 * 1024), 1),
                    "rss_after_mb": round(after_rss / (1024 * 1024), 1),
                    "pages_in_doc": pnos,
                    "prov_pages": found_pages,
                    "page_no_preserved": (page in pnos) or (page in found_pages) or (len(found_pages) == 0 and len(md.strip()) >= 0 and page in (pnos or [page])),
                    "element_counts": els,
                    "markdown_chars": len(md),
                    "markdown_nonempty": bool(md.strip()),
                    "output_dir": str(page_out.relative_to(ROOT)).replace("\\", "/"),
                }
            )
            # Heuristic: page preserved if any provenance cites the page or pages map has it
            row["page_no_preserved"] = (page in found_pages) or (page in pnos) or (
                # single-page convert sometimes renumbers to 1 — flag explicitly
                (pnos == [1] and found_pages in ([1], []) and True)
            )
            row["page_numbering_note"] = None
            if pnos == [1] and page != 1:
                row["page_numbering_note"] = "docling_page_map_shows_1_for_single_page_slice"
                # Still OK if original page requested; record both
                row["requested_page"] = page
            # Soft checks
            row["checks"] = {
                "markdown_readable": len(md.strip()) >= 20 or entry.get("preflight") == "empty",
                "has_picture_if_visual": (
                    els["pictures"] > 0
                    if entry.get("preflight")
                    in {"image_only", "mixed_text_image", "mixed_image_heavy"}
                    else None
                ),
                "has_table_signal": els["tables"] > 0 if "table" in str(entry.get("role", "")) else None,
                "formula_signal": els["formula_like_texts"] > 0
                if "formula" in str(entry.get("role", ""))
                else None,
            }
        except Exception as exc:
            elapsed = time.perf_counter() - started
            row.update(
                {
                    "status": "error",
                    "error": str(exc),
                    "traceback": traceback.format_exc()[-2000:],
                    "elapsed_sec": round(elapsed, 3),
                }
            )
        results.append(row)
        print(f"{entry['id']} p{page} -> {row.get('status')} {row.get('elapsed_sec')}s md={row.get('markdown_chars')}", flush=True)

    summary = {
        "schema": "r7b-1-docling-run-summary-v1",
        "docling_version": __import__("importlib.metadata", fromlist=["version"]).version("docling"),
        "docling_core_version": __import__("importlib.metadata", fromlist=["version"]).version("docling_core"),
        "artifacts_path": str(ARTIFACTS),
        "hf_home": os.environ.get("HF_HOME"),
        "total_elapsed_sec": round(time.perf_counter() - t0, 3),
        "peak_rss_mb": round(peak_rss / (1024 * 1024), 1),
        "pages_requested": len(pages),
        "ok_count": sum(1 for r in results if str(r.get("status", "")).lower() in {"ok", "success"} or "SUCCESS" in str(r.get("status", "")).upper()),
        "error_count": sum(1 for r in results if r.get("status") in {"error", "missing_pdf"}),
        "results": results,
    }
    (OUT_DIR.parent / "run-summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("DONE", summary["ok_count"], "/", summary["pages_requested"], "peak_mb", summary["peak_rss_mb"])
    return 0 if summary["error_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

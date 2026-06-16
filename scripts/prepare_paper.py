#!/usr/bin/env python3
"""Prepare a paper PDF URL or local PDF for annotated Markdown translation."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def normalize_source(source: str) -> str:
    parsed = urllib.parse.urlparse(source)
    if "arxiv.org" in parsed.netloc and parsed.path.startswith("/abs/"):
        paper_id = parsed.path.removeprefix("/abs/")
        return f"https://arxiv.org/pdf/{paper_id}"
    if "arxiv.org" in parsed.netloc and parsed.path.startswith("/html/"):
        paper_id = parsed.path.removeprefix("/html/")
        return f"https://arxiv.org/pdf/{paper_id}"
    return source


def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return value[:120] or "paper"


def download_pdf(url: str, out_path: Path) -> None:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 paper-translation-annotator",
            "Accept": "application/pdf,*/*",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        content_type = response.headers.get("content-type", "")
        data = response.read()
    if len(data) < 1024:
        raise RuntimeError("Downloaded file is unexpectedly small; source may not be a PDF.")
    if b"%PDF" not in data[:2048] and "pdf" not in content_type.lower():
        raise RuntimeError(f"Downloaded content does not look like a PDF: {content_type!r}")
    out_path.write_bytes(data)


def extract_with_pymupdf(pdf_path: Path, max_pages: int | None) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    try:
        import fitz  # PyMuPDF
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PyMuPDF is not available. Install pymupdf or use another PDF extractor.") from exc

    pages: list[dict] = []
    doc = fitz.open(pdf_path)
    page_limit = min(len(doc), max_pages) if max_pages else len(doc)
    for index in range(page_limit):
        page = doc[index]
        text = page.get_text("text").strip()
        links = []
        for link in page.get_links():
            uri = link.get("uri")
            if uri:
                links.append(uri)
        if not text:
            warnings.append(f"Page {index + 1} has no extracted text; it may be scanned or image-heavy.")
        pages.append(
            {
                "page": index + 1,
                "width": page.rect.width,
                "height": page.rect.height,
                "text": text,
                "links": links[:20],
            }
        )
    doc.close()
    return pages, warnings


def infer_title(pages: list[dict], override: str | None, source: str) -> str:
    if override:
        return override
    first_text = pages[0]["text"] if pages else ""
    for line in first_text.splitlines()[:20]:
        candidate = line.strip()
        if 12 <= len(candidate) <= 180 and not candidate.lower().startswith(("abstract", "arxiv:", "doi:")):
            return candidate
    parsed = urllib.parse.urlparse(source)
    return safe_name(Path(parsed.path).stem or Path(source).stem or "paper")


def write_extracted_md(path: Path, title: str, source: str, pages: list[dict]) -> None:
    parts = [
        f"# Extracted Text: {title}",
        "",
        f"Source: {source}",
        "",
        "Use this file as source material. Page markers must be preserved during translation when useful.",
        "",
    ]
    for page in pages:
        parts.extend(
            [
                f"## Page {page['page']}",
                "",
                page["text"] or "[No extractable text on this page]",
                "",
            ]
        )
    path.write_text("\n".join(parts), encoding="utf-8")


def write_skeleton(path: Path, title: str, source: str) -> None:
    text = f"""# 《{title}》

> Source: {source}

## Paper Information

Authors:

Institutions:

## TL;DR

> [!IMPORTANT]
> **关键点**
>

## Terms

| English | 中文 | Note |
|---|---|---|

## Annotated Translation

### Abstract

### 1. Introduction

## Figure And Table Reading Notes

## Method Map

## Limitations And Open Questions
"""
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="PDF URL, arXiv abs/html/pdf URL, or local PDF path")
    parser.add_argument("--out-dir", default="work/paper-translation", help="output directory")
    parser.add_argument("--max-pages", type=int, default=None, help="extract only first N pages")
    parser.add_argument("--title", default=None, help="override inferred title")
    parser.add_argument("--no-download", action="store_true", help="treat source as local path only")
    args = parser.parse_args()

    out_dir = Path(args.out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    source = normalize_source(args.source)
    parsed = urllib.parse.urlparse(source)
    pdf_path = out_dir / "source.pdf"

    if parsed.scheme in {"http", "https"} and not args.no_download:
        download_pdf(source, pdf_path)
    else:
        local = Path(args.source).expanduser().resolve()
        if not local.exists():
            raise FileNotFoundError(local)
        if local.suffix.lower() != ".pdf":
            raise RuntimeError(f"Local source does not end with .pdf: {local}")
        shutil.copyfile(local, pdf_path)

    pages, warnings = extract_with_pymupdf(pdf_path, args.max_pages)
    title = infer_title(pages, args.title, source)

    extracted_path = out_dir / "extracted.md"
    skeleton_path = out_dir / "translation_skeleton.md"
    metadata_path = out_dir / "metadata.json"

    write_extracted_md(extracted_path, title, source, pages)
    write_skeleton(skeleton_path, title, source)

    metadata = {
        "source": source,
        "pdf_path": str(pdf_path),
        "title": title,
        "page_count_extracted": len(pages),
        "max_pages": args.max_pages,
        "warnings": warnings,
        "extracted_md": str(extracted_path),
        "translation_skeleton": str(skeleton_path),
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)

#!/usr/bin/env python3
"""Export a translated Markdown paper to PDF."""

from __future__ import annotations

import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


CALLOUT_CLASS = {
    "IMPORTANT": "important",
    "NOTE": "note",
    "TIP": "tip",
    "WARNING": "warning",
}

REPORTLAB_FONT = "PaperCJK"


def slugify(text: str) -> str:
    value = re.sub(r"<[^>]+>", "", text).strip().lower()
    value = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", value).strip("-")
    return value or "section"


def rewrite_image_paths(markdown_text: str, base_dir: Path) -> str:
    def replace(match: re.Match[str]) -> str:
        alt, src = match.group(1), match.group(2).strip()
        if re.match(r"^[a-z]+://", src) or src.startswith("data:"):
            return match.group(0)
        path, suffix = src, ""
        if "#" in path:
            path, fragment = path.split("#", 1)
            suffix = "#" + fragment
        image_path = (base_dir / path).resolve()
        if image_path.exists():
            return f"![{alt}]({image_path.as_uri()}{suffix})"
        return match.group(0)

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace, markdown_text)


def markdown_has_math(markdown_text: str) -> bool:
    return bool(
        re.search(r"(?m)^```math\s*$", markdown_text)
        or re.search(r"(?s)\$\$.*?\$\$", markdown_text)
        or re.search(r"(?<!\\)\$[^$\n]+(?<!\\)\$", markdown_text)
    )


def normalize_math_fences(markdown_text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        body = match.group(1).strip("\n")
        return f"\n$$\n{body}\n$$\n"

    return re.sub(r"(?ms)^```math\s*\n(.*?)\n```\s*$", replace, markdown_text)


def inline_markdown(text: str) -> str:
    escaped = html.escape(text, quote=False)
    escaped = re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", r'<img src="\2" alt="\1">', escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', escaped)
    escaped = re.sub(r"`([^`]+)`", r"<code>\1</code>", escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", escaped)
    return escaped


def markdown_to_html(markdown_text: str) -> str:
    markdown_text = normalize_math_fences(markdown_text)
    try:
        import markdown  # type: ignore
    except Exception:
        return group_figures_in_html(fallback_markdown_to_html(markdown_text))

    rendered = markdown.markdown(
        markdown_text,
        extensions=["extra", "tables", "fenced_code", "toc", "sane_lists"],
        output_format="html5",
    )
    return group_figures_in_html(rendered)


def group_figures_in_html(html_text: str) -> str:
    paragraph_image_pattern = re.compile(
        r'<p><img src="([^"]+)" alt="([^"]*)"\s*/?></p>\s*'
        r'<p>(<strong>(?:Figure|Fig\.|Table|Algorithm)\s+.*?)</p>',
        re.IGNORECASE | re.DOTALL,
    )
    figure_image_pattern = re.compile(
        r'<figure><img src="([^"]+)" alt="([^"]*)"\s*/?></figure>\s*'
        r'<p>(<strong>(?:Figure|Fig\.|Table|Algorithm)\s+.*?)</p>',
        re.IGNORECASE | re.DOTALL,
    )

    def replace(match: re.Match[str]) -> str:
        src, alt, caption = match.groups()
        return (
            f'<figure class="paper-figure"><img src="{src}" alt="{alt}">'
            f"<figcaption>{caption}</figcaption></figure>"
        )

    html_text = paragraph_image_pattern.sub(replace, html_text)
    return figure_image_pattern.sub(replace, html_text)


def fallback_markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    output: list[str] = []
    paragraph: list[str] = []
    list_items: list[str] = []
    table_rows: list[str] = []
    in_code = False
    code_lines: list[str] = []
    callout: dict[str, object] | None = None

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            output.append(f"<p>{inline_markdown(' '.join(paragraph))}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal list_items
        if list_items:
            output.append("<ul>")
            output.extend(f"<li>{item}</li>" for item in list_items)
            output.append("</ul>")
            list_items = []

    def flush_table() -> None:
        nonlocal table_rows
        if not table_rows:
            return
        output.append("<table>")
        for idx, row in enumerate(table_rows):
            cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
            if idx == 1 and all(set(cell) <= {"-", ":", " "} for cell in cells):
                continue
            tag = "th" if idx == 0 else "td"
            output.append("<tr>" + "".join(f"<{tag}>{inline_markdown(cell)}</{tag}>" for cell in cells) + "</tr>")
        output.append("</table>")
        table_rows = []

    def flush_callout() -> None:
        nonlocal callout
        if not callout:
            return
        body = "\n".join(callout["body"])  # type: ignore[index]
        rendered = fallback_markdown_to_html(body) if body.strip() else ""
        output.append(
            f'<div class="callout {callout["class"]}">'
            f'<div class="callout-title">{html.escape(str(callout["title"]))}</div>'
            f'<div class="callout-body">{rendered}</div>'
            "</div>"
        )
        callout = None

    def flush_blocks() -> None:
        flush_paragraph()
        flush_list()
        flush_table()
        flush_callout()

    for line in lines:
        if line.startswith("```"):
            flush_blocks()
            if in_code:
                output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue

        callout_match = re.match(r"^>\s*\[!(IMPORTANT|NOTE|TIP|WARNING)\]\s*(.*)$", line)
        if callout_match:
            flush_blocks()
            kind, title = callout_match.groups()
            callout = {
                "class": CALLOUT_CLASS.get(kind, "note"),
                "title": title.strip() or kind.title(),
                "body": [],
            }
            continue
        if callout and line.startswith(">"):
            body_line = line[1:].lstrip()
            title_match = re.match(r"^\*\*([^*]+)\*\*\s*$", body_line)
            if title_match and str(callout["title"]).upper() in CALLOUT_CLASS:
                callout["title"] = title_match.group(1)
            else:
                callout["body"].append(body_line)  # type: ignore[index]
            continue
        if callout:
            flush_callout()

        if not line.strip():
            flush_blocks()
            continue
        if line.startswith("|") and line.rstrip().endswith("|"):
            flush_paragraph()
            flush_list()
            table_rows.append(line)
            continue
        if table_rows:
            flush_table()
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_blocks()
            level = len(heading.group(1))
            title = inline_markdown(heading.group(2))
            output.append(f'<h{level} id="{slugify(heading.group(2))}">{title}</h{level}>')
            continue
        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        if bullet:
            flush_paragraph()
            list_items.append(inline_markdown(bullet.group(1)))
            continue
        image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
        if image:
            flush_blocks()
            output.append(f'<figure><img src="{html.escape(image.group(2))}" alt="{html.escape(image.group(1))}"></figure>')
            continue
        paragraph.append(line.strip())

    flush_blocks()
    if in_code:
        output.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
    return "\n".join(output)


def build_document(body: str, title: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<script>
window.MathJax = {{
  tex: {{ inlineMath: [['$', '$'], ['\\\\(', '\\\\)']], displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']] }},
  svg: {{ fontCache: 'global' }}
}};
</script>
<script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-svg.js"></script>
<script>
window.addEventListener('load', () => {{
  const markReady = () => document.body.setAttribute('data-mathjax-ready', 'true');
  if (window.MathJax && window.MathJax.typesetPromise) {{
    window.MathJax.typesetPromise().then(markReady).catch(markReady);
  }} else {{
    markReady();
  }}
}});
</script>
<style>
@page {{ size: A4; margin: 20mm 17mm; }}
:root {{
  color-scheme: light;
  --text: #172033;
  --muted: #536173;
  --line: #d9e1ea;
  --important: #e0f2fe;
  --important-line: #0284c7;
  --note: #edf7ed;
  --note-line: #16a34a;
  --tip: #fff7ed;
  --tip-line: #ea580c;
  --warning: #fef2f2;
  --warning-line: #dc2626;
}}
body {{
  max-width: 900px;
  margin: 0 auto;
  padding: 28px;
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif;
  font-size: 15px;
  line-height: 1.72;
  background: #fff;
}}
h1, h2, h3, h4 {{ line-height: 1.28; margin: 1.5em 0 0.55em; }}
h1 {{ font-size: 2rem; border-bottom: 2px solid var(--line); padding-bottom: 0.35em; }}
h2 {{ font-size: 1.45rem; border-bottom: 1px solid var(--line); padding-bottom: 0.22em; }}
h3 {{ font-size: 1.18rem; }}
p {{ margin: 0.75em 0; }}
a {{ color: #0369a1; text-decoration: none; }}
blockquote {{ margin: 1em 0; padding: 0.1em 1em; border-left: 4px solid #94a3b8; color: var(--muted); background: #f8fafc; }}
.callout {{ margin: 1em 0; padding: 0.85em 1em; border-left: 5px solid; border-radius: 6px; break-inside: avoid; }}
.callout-title {{ font-weight: 700; margin-bottom: 0.2em; }}
.callout-body > :first-child {{ margin-top: 0; }}
.callout-body > :last-child {{ margin-bottom: 0; }}
.callout.important {{ background: var(--important); border-left-color: var(--important-line); }}
.callout.note {{ background: var(--note); border-left-color: var(--note-line); }}
.callout.tip {{ background: var(--tip); border-left-color: var(--tip-line); }}
.callout.warning {{ background: var(--warning); border-left-color: var(--warning-line); }}
img {{ max-width: 100%; height: auto; display: block; margin: 0.7em auto; }}
figure {{
  margin: 1.2em 0;
  break-inside: avoid;
  page-break-inside: avoid;
}}
figure.paper-figure {{
  margin: 1.1em 0 1.25em;
  display: inline-block;
  width: 100%;
  break-inside: auto;
  page-break-inside: auto;
}}
figure.paper-figure img {{
  margin-bottom: 0.45em;
  max-width: 100%;
  max-height: 105mm;
  width: auto;
  object-fit: contain;
}}
figcaption {{
  color: var(--muted);
  font-size: 0.92em;
  line-height: 1.55;
  text-align: left;
  break-before: avoid;
  page-break-before: avoid;
  break-inside: avoid;
  page-break-inside: avoid;
}}
table {{ width: 100%; border-collapse: collapse; margin: 1em 0; font-size: 0.92em; break-inside: avoid; }}
th, td {{ border: 1px solid var(--line); padding: 0.42em 0.55em; vertical-align: top; }}
th {{ background: #f1f5f9; }}
pre {{ overflow-x: auto; background: #0f172a; color: #e2e8f0; padding: 1em; border-radius: 6px; }}
code {{ font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace; font-size: 0.92em; }}
@media print {{
  body {{ max-width: none; margin: 0; padding: 0; }}
  a {{ color: inherit; }}
  h1, h2, h3, h4, h5, h6 {{
    break-after: avoid;
    page-break-after: avoid;
  }}
  p, li, blockquote {{
    orphans: 3;
    widows: 3;
  }}
  figure.paper-figure img {{
    max-height: 92mm;
  }}
}}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def find_chrome() -> str | None:
    candidates = [
        os.environ.get("CHROME"),
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("microsoft-edge"),
    ]
    return next((str(path) for path in candidates if path and Path(path).exists()), None)


def export_with_weasyprint(html_text: str, html_path: Path, pdf_path: Path) -> bool:
    try:
        from weasyprint import HTML  # type: ignore
    except Exception:
        return False
    HTML(string=html_text, base_url=str(html_path.parent)).write_pdf(str(pdf_path))
    return True


def export_with_chrome(html_path: Path, pdf_path: Path, timeout: int) -> bool:
    chrome = find_chrome()
    if not chrome:
        return False
    profile_dir = Path(tempfile.mkdtemp(prefix="paper-md-pdf-chrome-"))
    command = [
        chrome,
        "--headless",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-sync",
        "--disable-translate",
        "--no-first-run",
        "--no-default-browser-check",
        "--allow-file-access-from-files",
        "--no-pdf-header-footer",
        "--run-all-compositor-stages-before-draw",
        f"--user-data-dir={profile_dir}",
        "--virtual-time-budget=10000",
        f"--print-to-pdf={pdf_path}",
        html_path.as_uri(),
    ]
    output_was_written = False
    try:
        subprocess.run(command, check=True, timeout=timeout)
        output_was_written = pdf_path.exists() and pdf_path.stat().st_size > 1024
        return True
    except subprocess.TimeoutExpired:
        output_was_written = pdf_path.exists() and pdf_path.stat().st_size > 1024
        if output_was_written:
            print(
                f"Chrome/Chromium did not exit within {timeout}s, but a PDF was written successfully.",
                file=sys.stderr,
            )
            return True
        print(f"Chrome/Chromium PDF export timed out after {timeout}s before writing a PDF.", file=sys.stderr)
        return False
    except subprocess.CalledProcessError as exc:
        output_was_written = pdf_path.exists() and pdf_path.stat().st_size > 1024
        if output_was_written:
            print(
                f"Chrome/Chromium exited with {exc.returncode}, but a PDF was written successfully.",
                file=sys.stderr,
            )
            return True
        print(f"Chrome/Chromium PDF export failed with exit code {exc.returncode}.", file=sys.stderr)
        return False
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)


def reportlab_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(r"`([^`]+)`", rf'<font name="{REPORTLAB_FONT}">\1</font>', escaped)
    escaped = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", escaped)
    escaped = re.sub(r"\*([^*]+)\*", r"<i>\1</i>", escaped)
    escaped = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<font color="#0369a1">\1</font>', escaped)
    return escaped


def split_reportlab_paragraphs(markdown_text: str) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    paragraph: list[str] = []
    table_rows: list[str] = []
    callout: dict[str, object] | None = None
    in_code = False
    code_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            blocks.append({"type": "paragraph", "text": " ".join(paragraph)})
            paragraph = []

    def flush_table() -> None:
        nonlocal table_rows
        if table_rows:
            blocks.append({"type": "table", "rows": table_rows})
            table_rows = []

    def flush_callout() -> None:
        nonlocal callout
        if callout:
            blocks.append(callout)
            callout = None

    def flush_code() -> None:
        nonlocal code_lines
        if code_lines:
            blocks.append({"type": "code", "text": "\n".join(code_lines)})
            code_lines = []

    def flush_blocks() -> None:
        flush_paragraph()
        flush_table()
        flush_callout()

    for line in markdown_text.splitlines():
        if line.startswith("```"):
            flush_blocks()
            if in_code:
                flush_code()
                in_code = False
            else:
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue

        callout_match = re.match(r"^>\s*\[!(IMPORTANT|NOTE|TIP|WARNING)\]\s*(.*)$", line)
        if callout_match:
            flush_blocks()
            kind, title = callout_match.groups()
            callout = {
                "type": "callout",
                "kind": CALLOUT_CLASS.get(kind, "note"),
                "title": title.strip() or kind.title(),
                "body": [],
            }
            continue
        if callout and line.startswith(">"):
            body_line = line[1:].lstrip()
            title_match = re.match(r"^\*\*([^*]+)\*\*\s*$", body_line)
            if title_match and str(callout["title"]).upper() in CALLOUT_CLASS:
                callout["title"] = title_match.group(1)
            else:
                callout["body"].append(body_line)  # type: ignore[index]
            continue
        if callout:
            flush_callout()

        if not line.strip():
            flush_blocks()
            continue
        if line.startswith("|") and line.rstrip().endswith("|"):
            flush_paragraph()
            table_rows.append(line)
            continue
        if table_rows:
            flush_table()
        heading = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading:
            flush_blocks()
            blocks.append({"type": "heading", "level": len(heading.group(1)), "text": heading.group(2)})
            continue
        image = re.match(r"^!\[([^\]]*)\]\(([^)]+)\)\s*$", line)
        if image:
            flush_blocks()
            blocks.append({"type": "image", "alt": image.group(1), "src": image.group(2)})
            continue
        bullet = re.match(r"^\s*[-*]\s+(.+)$", line)
        if bullet:
            flush_paragraph()
            blocks.append({"type": "bullet", "text": bullet.group(1)})
            continue
        paragraph.append(line.strip())

    flush_blocks()
    if in_code:
        flush_code()
    return blocks


def resolve_image_path(src: str, base_dir: Path) -> Path | None:
    if src.startswith("file://"):
        return Path(src.removeprefix("file://"))
    if re.match(r"^[a-z]+://", src):
        return None
    path = src.split("#", 1)[0]
    image_path = (base_dir / path).resolve()
    return image_path if image_path.exists() else None


def export_with_reportlab(markdown_text: str, markdown_path: Path, pdf_path: Path, title: str) -> bool:
    try:
        from PIL import Image as PILImage  # type: ignore
        from reportlab.lib import colors  # type: ignore
        from reportlab.lib.enums import TA_CENTER  # type: ignore
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet  # type: ignore
        from reportlab.lib.units import mm  # type: ignore
        from reportlab.pdfbase import pdfmetrics  # type: ignore
        from reportlab.pdfbase.ttfonts import TTFont  # type: ignore
        from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle  # type: ignore
    except Exception:
        return False

    font_path = next(
        (
            path
            for path in [
                "/System/Library/Fonts/STHeiti Medium.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/System/Library/Fonts/Supplemental/Songti.ttc",
            ]
            if Path(path).exists()
        ),
        None,
    )
    if not font_path:
        return False
    pdfmetrics.registerFont(TTFont(REPORTLAB_FONT, font_path))
    pdfmetrics.registerFontFamily(
        REPORTLAB_FONT,
        normal=REPORTLAB_FONT,
        bold=REPORTLAB_FONT,
        italic=REPORTLAB_FONT,
        boldItalic=REPORTLAB_FONT,
    )
    styles = getSampleStyleSheet()
    base = ParagraphStyle(
        "PaperBase",
        parent=styles["Normal"],
        fontName=REPORTLAB_FONT,
        fontSize=10.5,
        leading=17,
        textColor=colors.HexColor("#172033"),
        spaceAfter=6,
    )
    heading_styles = {
        1: ParagraphStyle("H1", parent=base, fontSize=20, leading=26, spaceBefore=8, spaceAfter=12),
        2: ParagraphStyle("H2", parent=base, fontSize=15, leading=21, spaceBefore=14, spaceAfter=8),
        3: ParagraphStyle("H3", parent=base, fontSize=12.5, leading=18, spaceBefore=10, spaceAfter=6),
        4: ParagraphStyle("H4", parent=base, fontSize=11.5, leading=17, spaceBefore=8, spaceAfter=5),
    }
    caption = ParagraphStyle("Caption", parent=base, fontSize=9, leading=13, alignment=TA_CENTER, textColor=colors.HexColor("#536173"))
    code = ParagraphStyle("Code", parent=base, fontSize=8.5, leading=12, backColor=colors.HexColor("#f1f5f9"))
    bullet = ParagraphStyle("Bullet", parent=base, leftIndent=12, firstLineIndent=-8)

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
    )
    story = []
    callout_colors = {
        "important": (colors.HexColor("#e0f2fe"), colors.HexColor("#0284c7")),
        "note": (colors.HexColor("#edf7ed"), colors.HexColor("#16a34a")),
        "tip": (colors.HexColor("#fff7ed"), colors.HexColor("#ea580c")),
        "warning": (colors.HexColor("#fef2f2"), colors.HexColor("#dc2626")),
    }

    def paragraph(text: str, style: ParagraphStyle = base) -> Paragraph:
        return Paragraph(reportlab_inline(text), style)

    for block in split_reportlab_paragraphs(markdown_text):
        kind = block["type"]
        if kind == "heading":
            level = int(block["level"])
            story.append(paragraph(str(block["text"]), heading_styles.get(level, heading_styles[4])))
        elif kind == "paragraph":
            story.append(paragraph(str(block["text"])))
        elif kind == "bullet":
            story.append(Paragraph("• " + reportlab_inline(str(block["text"])), bullet))
        elif kind == "code":
            story.append(Paragraph(html.escape(str(block["text"])).replace("\n", "<br/>"), code))
        elif kind == "table":
            rows = []
            for idx, row in enumerate(block["rows"]):  # type: ignore[index]
                cells = [cell.strip() for cell in str(row).strip().strip("|").split("|")]
                if idx == 1 and all(set(cell) <= {"-", ":", " "} for cell in cells):
                    continue
                rows.append([paragraph(cell) for cell in cells])
            if rows:
                table = Table(rows, repeatRows=1)
                table.setStyle(
                    TableStyle(
                        [
                            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#d9e1ea")),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("LEFTPADDING", (0, 0), (-1, -1), 5),
                            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ]
                    )
                )
                story.append(table)
                story.append(Spacer(1, 5))
        elif kind == "callout":
            bg, line = callout_colors.get(str(block["kind"]), callout_colors["note"])
            body_text = "\n".join(block["body"])  # type: ignore[index]
            content = [Paragraph(f"<b>{html.escape(str(block['title']))}</b>", base)]
            if body_text.strip():
                content.append(paragraph(body_text))
            table = Table([[content]], colWidths=[doc.width])
            table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), bg),
                        ("LINEBEFORE", (0, 0), (-1, -1), 4, line),
                        ("BOX", (0, 0), (-1, -1), 0.25, bg),
                        ("LEFTPADDING", (0, 0), (-1, -1), 10),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ]
                )
            )
            story.append(KeepTogether(table))
            story.append(Spacer(1, 6))
        elif kind == "image":
            image_path = resolve_image_path(str(block["src"]), markdown_path.parent)
            if not image_path:
                story.append(paragraph(f"[Missing image: {block['src']}]", caption))
                continue
            with PILImage.open(image_path) as img:
                width_px, height_px = img.size
            max_width = doc.width
            draw_width = min(max_width, width_px * 0.45)
            draw_height = height_px * draw_width / width_px
            story.append(KeepTogether([Image(str(image_path), width=draw_width, height=draw_height), paragraph(str(block["alt"]), caption)]))
            story.append(Spacer(1, 6))

    doc.build(story)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("markdown", help="translated Markdown file")
    parser.add_argument("-o", "--output", help="output PDF path")
    parser.add_argument("--html", help="also keep the intermediate HTML at this path")
    parser.add_argument("--title", help="HTML/PDF document title")
    parser.add_argument("--html-only", action="store_true", help="only write HTML, do not export PDF")
    parser.add_argument("--pdf-timeout", type=int, default=45, help="Chrome/Chromium PDF export timeout in seconds")
    args = parser.parse_args()

    markdown_path = Path(args.markdown).expanduser().resolve()
    if not markdown_path.exists():
        raise FileNotFoundError(markdown_path)

    pdf_path = Path(args.output).expanduser().resolve() if args.output else markdown_path.with_suffix(".pdf")
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    keep_html = bool(args.html or args.html_only)
    if args.html:
        html_path = Path(args.html).expanduser().resolve()
        html_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = None
    elif args.html_only:
        html_path = pdf_path.with_suffix(".html")
        html_path.parent.mkdir(parents=True, exist_ok=True)
        temp_dir = None
    else:
        temp_dir = tempfile.TemporaryDirectory(prefix="paper-md-html-")
        html_path = Path(temp_dir.name) / f"{pdf_path.stem}.html"

    raw_markdown = markdown_path.read_text(encoding="utf-8")
    title = args.title or next((line.lstrip("# ").strip() for line in raw_markdown.splitlines() if line.startswith("# ")), markdown_path.stem)
    prepared_markdown = rewrite_image_paths(raw_markdown, markdown_path.parent)
    contains_math = markdown_has_math(prepared_markdown)
    body = markdown_to_html(prepared_markdown)
    html_text = build_document(body, title)
    html_path.write_text(html_text, encoding="utf-8")

    if args.html_only:
        print(f"HTML written: {html_path}")
        if temp_dir:
            temp_dir.cleanup()
        return 0

    if contains_math and export_with_chrome(html_path, pdf_path, args.pdf_timeout):
        print(f"PDF written with Chrome/Chromium: {pdf_path}")
        if keep_html:
            print(f"HTML written: {html_path}")
        if temp_dir:
            temp_dir.cleanup()
        return 0

    if export_with_weasyprint(html_text, html_path, pdf_path):
        renderer = "WeasyPrint"
        if contains_math:
            renderer += " (MathJax JavaScript is not executed; install Chrome/Chromium for rendered math)"
        print(f"PDF written with {renderer}: {pdf_path}")
        if keep_html:
            print(f"HTML written: {html_path}")
        if temp_dir:
            temp_dir.cleanup()
        return 0

    if not contains_math and export_with_chrome(html_path, pdf_path, args.pdf_timeout):
        print(f"PDF written with Chrome/Chromium: {pdf_path}")
        if keep_html:
            print(f"HTML written: {html_path}")
        if temp_dir:
            temp_dir.cleanup()
        return 0

    if export_with_reportlab(raw_markdown, markdown_path, pdf_path, title):
        print(f"PDF written with ReportLab fallback: {pdf_path}")
        if keep_html:
            print(f"HTML written: {html_path}")
        if temp_dir:
            temp_dir.cleanup()
        return 0

    if keep_html:
        print(f"HTML preview written for debugging: {html_path}")
    print(
        "PDF export needs a working WeasyPrint or Chrome/Chromium backend. "
        "Install WeasyPrint, fix the local browser backend, or rerun with --html "
        "only if you explicitly need an HTML debugging preview.",
        file=sys.stderr,
    )
    if temp_dir:
        temp_dir.cleanup()
    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)

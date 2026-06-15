---
name: paper-translation-annotator
description: Translate English academic paper PDFs from a PDF URL, arXiv URL, or local PDF into Chinese Markdown while preserving the paper's logical structure, page reading flow, figures, tables, equations in LaTeX/high-fidelity math format, citations, and adding Markdown callout annotations for key concepts, methods, assumptions, formulas, results, limitations, and reading pitfalls. Use when the user asks to translate a paper, read an English paper in Chinese, create an annotated paper translation, explain a PDF paper URL, preserve figures and tables in Markdown, or produce a Markdown study version of an academic PDF.
---

# Paper Translation Annotator

Create a reader-friendly Chinese Markdown translation of an English academic paper from a PDF URL or local PDF. The output is Markdown, not a rewritten PDF, but it should still be a visually useful study edition: preserve the paper's logical structure, reading flow, figures, tables, equations, citations, and important layout cues. Add high-value explanatory annotations with Markdown callout blocks.

## Default Workflow

1. Prepare the source with `scripts/prepare_paper.py`.
2. Inspect the generated extraction report, Markdown skeleton, PDF page count, and extraction warnings.
3. Extract or render paper figures and tables before writing the final translation. Prefer cropped original PDF assets when available; otherwise render the relevant PDF page region or recreate tables faithfully in Markdown/HTML.
4. Translate section by section into Chinese while preserving the paper's original reading flow: place each figure/table near the paragraph that discusses it, keep captions, and keep equation blocks near their original explanatory text.
5. Preserve figure/table/equation/citation anchors in text, such as `Figure 2`, `Table 1`, `Eq. (3)`, `[12]`, and author-year citations.
6. Rewrite formulas, variables, Greek letters, superscripts/subscripts, matrices, and complexity expressions in LaTeX math or another high-fidelity Markdown-renderable math format.
7. Add annotations only where they help comprehension.
8. Save the final Markdown under the requested output path, or under `outputs/` when the user wants a deliverable. Save extracted visual assets under a sibling folder such as `outputs/assets/<paper-slug>/`.
9. When the user wants GitHub-friendly display or a shareable artifact, export the final Markdown to PDF with `scripts/export_markdown_pdf.py`.

## Source Preparation

Run:

```bash
python3 <skill-dir>/scripts/prepare_paper.py "<pdf-or-arxiv-url-or-local-pdf>" --out-dir work/paper-translation
```

Optional flags:

```bash
--max-pages 20       # extract only first N pages for long papers or trials
--title "..."        # override inferred title
--no-download        # treat input as local path only
```

The script produces:

- `source.pdf` when input is a URL
- `extracted.md` with page-delimited extracted text
- `metadata.json` with source URL, page count, extraction warnings, and paths
- `translation_skeleton.md` with the required output structure

If extraction quality is poor, tell the user plainly and choose the best fallback: OCR request, arXiv source, publisher HTML, or a partial translation.

## PDF Export

GitHub Markdown may not render callouts, LaTeX math, or local paper assets consistently. When a stable visual artifact is needed, run:

```bash
python3 <skill-dir>/scripts/export_markdown_pdf.py "<translated.md>" -o "<translated.pdf>"
```

The export script:

- rewrites local image links to file URLs so figure and table assets can render in the PDF;
- converts Markdown callouts into styled highlighted blocks;
- loads MathJax in the generated HTML so LaTeX math can render before printing;
- writes a sibling HTML file for debugging and browser preview;
- exports PDF automatically when WeasyPrint or Chrome/Chromium is available.

If no PDF renderer is available, the script still writes HTML and tells the user which dependency is missing. In that case, ask the user to install Chrome/Chromium or WeasyPrint, or open the generated HTML in a browser and print to PDF.

## Figure, Table, And Layout Preservation

- Default output must be image-and-table rich, not text-only.
- Include original figures with Markdown image links whenever the PDF contains figures, diagrams, plots, or visual tables that materially support the paper.
- Put each figure/table close to its first substantial discussion, not only in a separate notes section.
- Preserve original captions in translated form and keep labels such as `Figure 1`, `Table 2`, and `Algorithm 1`.
- For tables, prefer faithful Markdown or HTML tables when extraction is clean. If a table is too complex, include a cropped table image and add a concise translated caption or reading note.
- For multi-column PDFs, preserve logical reading order rather than literal column geometry. Use headings, figures, captions, tables, equations, and paragraphs to approximate the original paper's flow.
- Do not fabricate missing figure content. If a figure/table cannot be extracted, state that plainly near the placeholder and explain what the surrounding text supports.

## Math And Formula Preservation

- Preserve displayed equations as fenced or block LaTeX math, for example `$$ ... $$`, and keep equation numbers such as `(1)` when present.
- Preserve inline variables and symbols with inline LaTeX, for example `$d_{model}$`, `$QK^T$`, `$O(n^2 \cdot d)$`, `$\\beta_1$`, and `$\\epsilon$`.
- Convert extracted plain-text approximations of formulas into valid LaTeX when the source formula is clear.
- Keep Greek letters, superscripts, subscripts, square roots, fractions, matrix transposes, summations, and complexity notation in high-fidelity math form.
- If formula extraction is uncertain, preserve the closest readable form and mark the uncertainty with a red annotation rather than silently simplifying it.

## Output Contract

Use this structure unless the user asks otherwise:

```markdown
# 《中文标题》

> Source: <URL or filename>

## Paper Information

Authors: <authors>

Institutions: <institutions>

## TL;DR

## Terms

## Annotated Translation

### Abstract

### 1. Introduction

...

![Figure 1. Translated caption.](assets/<paper-slug>/figure-1.png)

$$
Attention(Q,K,V)=\\operatorname{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V
\\tag{1}
$$

## Figure And Table Reading Notes

## Method Map

## Limitations And Open Questions
```

## Highlight Markup

Use Markdown callout blocks for all annotations, including short annotations. This keeps the whole note visually highlighted while leaving formulas in Markdown text so MathJax/KaTeX can render them. Do not use raw HTML spans or divs for annotations. Use these callout types consistently:

- `[!IMPORTANT]` for core concepts, key claims, main contributions, and headline results.
- `[!NOTE]` for methods, formulas, architecture, experiments, metrics, and algorithms.
- `[!TIP]` for intuition, reading path, comparisons, and memory hooks.
- `[!WARNING]` for limitations, assumptions, caveats, uncertainty, and possible misreadings.

```markdown
> [!IMPORTANT] 关键点
> Transformer 的核心贡献是证明只用注意力也能成为强大的序列转导主干架构。

> [!NOTE] 方法注
> $QK^T$ 给出每个 query 对每个 key 的相似度；softmax 把相似度变成权重。

> [!TIP] 读法提示
> 先看 Table 1 理解 self-attention 的路径长度优势，再读模型细节。

> [!WARNING] 注意
> 注意力可视化是定性证据，不等同于严格因果解释。
```

Keep annotation density useful: normally 1-3 annotations per dense section, more only for math-heavy or method-heavy parts.

## Translation Rules

- Translate faithfully first; explain second.
- Do not invent content that is not in the paper.
- Do not place annotations or LaTeX math inside raw HTML elements such as `<span>`, `<div>`, or `<strong>`. Use Markdown callout blocks for every annotation so the whole note is highlighted and math remains renderable.
- Keep the title clean: `# 《中文标题》` only. Do not append `annotated translation`.
- Do not include process notes such as `Translation note` in the final deliverable.
- Include a compact `Paper Information` section with only `Authors:` and `Institutions:` when the source provides them. Do not use a table for this section unless the user asks.
- Preserve technical terms in `中文（English term）` form on first use.
- Keep citations, equation numbers, figure/table references, dataset names, model names, and metric names intact.
- For formulas, produce LaTeX/high-fidelity math by default; do not downgrade clear formulas into prose-only descriptions.
- For figures and tables, include visual/table content by default and do not fabricate missing content. Explain only what the figure, table, caption, or surrounding text supports.
- If the paper is long, process in batches and maintain a running glossary and claim list.
- If the user requests full text but token budget is limited, translate all major sections with condensed detail and say which appendix/supplementary parts were summarized.

## Quality Checks

Before final delivery, check:

- The Markdown renders without broken HTML tags.
- LaTeX math is not nested inside raw HTML blocks or inline HTML spans.
- No `Color Legend` section is present unless the user explicitly asks for one.
- The top title does not include `annotated translation`.
- No `Translation note` or internal process note is present in the final deliverable.
- `Paper Information` is compact plain text with authors and institutions when available.
- All explanatory annotations use Markdown callout blocks, not raw HTML spans/divs.
- Section order matches the source paper as closely as extraction allows.
- Figures, tables, captions, and equations appear near their source discussion rather than being reduced to end notes only.
- Visual assets referenced by Markdown image links exist locally and use stable relative paths.
- If a PDF artifact is requested, `scripts/export_markdown_pdf.py` runs successfully or at least produces an HTML preview with a clear dependency note.
- Display equations are valid LaTeX/high-fidelity math, and inline variables use math markup where useful.
- Every major claim remains linked to its source section, citation, figure, table, or equation where available.
- Limitations and uncertainty are marked in red, not hidden in neutral prose.

## References

- `references/annotation-style.md` - callout type meaning, good annotation targets, and annotation density guidance.
- `scripts/export_markdown_pdf.py` - convert translated Markdown into styled HTML and PDF for stable sharing when GitHub rendering is insufficient.

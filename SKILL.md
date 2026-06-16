---
name: paper-translation-annotator
description: Use for translating English paper PDFs/arXiv links into Chinese Markdown with figures, tables, equations, citations, and callout annotations.
homepage: https://github.com/TransformeR22/paper-translation-annotator
metadata: {"openclaw":{"emoji":"📄","homepage":"https://github.com/TransformeR22/paper-translation-annotator","requires":{"anyBins":["python3","python"]}}}
---

# Paper Translation Annotator

Create a reader-friendly Chinese Markdown translation of an English academic paper from a PDF URL or local PDF. The output is Markdown, not a rewritten PDF, but it should still be a visually useful study edition: preserve the paper's logical structure, reading flow, figures, tables, equations, citations, and important layout cues. Add high-value explanatory annotations with Markdown callout blocks.

## Default Workflow

1. Prepare the source with `{baseDir}/scripts/prepare_paper.py`. In runtimes that do not expand `{baseDir}`, use the absolute path to this skill directory.
2. Inspect the generated extraction report, Markdown skeleton, PDF page count, and extraction warnings.
3. Extract or render paper figures and tables before writing the final translation. Prefer cropped original PDF assets when available; otherwise render the relevant PDF page region or recreate tables faithfully in Markdown/HTML.
4. Translate section by section into Chinese while preserving the paper's original reading flow: place each figure/table near the paragraph that discusses it, keep captions, and keep equation blocks near their original explanatory text.
5. Preserve figure/table/equation/citation anchors in text, such as `Figure 2`, `Table 1`, `Eq. (3)`, `[12]`, and author-year citations.
6. Rewrite formulas, variables, Greek letters, superscripts/subscripts, matrices, and complexity expressions in GitHub-compatible LaTeX math.
7. Add annotations only where they help comprehension.
8. Save the final Markdown under the requested output path, or under `outputs/` when the user wants a deliverable. Save extracted visual assets under a sibling folder such as `outputs/assets/<paper-slug>/`.
9. When the user wants GitHub-friendly display or a shareable artifact, export the final Markdown to PDF with `{baseDir}/scripts/export_markdown_pdf.py`.

## Source Preparation

Run:

```bash
python3 "{baseDir}/scripts/prepare_paper.py" "<pdf-or-arxiv-url-or-local-pdf>" --out-dir work/paper-translation
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
python3 "{baseDir}/scripts/export_markdown_pdf.py" "<translated.md>" -o "<translated.pdf>"
```

The export script:

- rewrites local image links to file URLs so figure and table assets can render in the PDF;
- converts GitHub-style fenced math blocks into MathJax display math;
- converts Markdown callouts into styled highlighted blocks;
- loads MathJax in the generated HTML so LaTeX math can render before printing;
- prefers Chrome/Chromium for math-heavy PDFs because WeasyPrint does not execute MathJax JavaScript;
- uses temporary HTML internally and does not keep it unless `--html` or `--html-only` is explicitly requested;
- exports PDF automatically when WeasyPrint or Chrome/Chromium is available.

If no PDF renderer is available, the script reports the missing dependency. Do not include HTML in the final deliverable unless the user explicitly asks for it with `--html` or `--html-only`.

## Figure, Table, And Layout Preservation

- Default output must be image-and-table rich, not text-only.
- Include original figures with Markdown image links whenever the PDF contains figures, diagrams, plots, or visual tables that materially support the paper.
- Put each figure/table close to its first substantial discussion, not only in a separate notes section.
- Preserve original captions in translated form and keep labels such as `Figure 1`, `Table 2`, and `Algorithm 1`.
- For tables, prefer faithful Markdown or HTML tables when extraction is clean. If a table is too complex, include a cropped table image and add a concise translated caption or reading note.
- For multi-column PDFs, preserve logical reading order rather than literal column geometry. Use headings, figures, captions, tables, equations, and paragraphs to approximate the original paper's flow.
- Do not fabricate missing figure content. If a figure/table cannot be extracted, state that plainly near the placeholder and explain what the surrounding text supports.

## Math And Formula Preservation

- Preserve displayed equations as GitHub-compatible fenced math blocks:

````markdown
```math
\mathrm{Attention}(Q,K,V)
=
\mathrm{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V
```

**(1)**
````

- Preserve inline variables and symbols with inline LaTeX, for example `$d_{model}$`, `$QK^T$`, `$O(n^2 \cdot d)$`, `$\\beta_1$`, and `$\\epsilon$`.
- Convert extracted plain-text approximations of formulas into valid LaTeX when the source formula is clear.
- Keep Greek letters, superscripts, subscripts, square roots, fractions, matrix transposes, summations, and complexity notation in high-fidelity math form.
- Do not use `\tag{...}` for equation numbers in final Markdown. It may render in VS Code extensions, but it is unreliable on GitHub. Put the equation number on its own line after the math block, for example `**(1)**`.
- Do not use `\operatorname{...}` in GitHub-targeted Markdown. GitHub may reject it with "macros are not allowed". Prefer `\mathrm{...}` for function-like names, for example `\mathrm{softmax}` and `\mathrm{LayerNorm}`.
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

```math
Attention(Q,K,V)=\\mathrm{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}}\\right)V
```

**(1)**

## Figure And Table Reading Notes

## Method Map

## Limitations And Open Questions
```

## Highlight Markup

Use GitHub alert callout blocks for all annotations, including short annotations. This keeps the whole note visually highlighted while leaving formulas in Markdown text so GitHub math can render them. Do not use raw HTML spans or divs for annotations. Use these callout types consistently:

- `[!IMPORTANT]` for core concepts, key claims, main contributions, and headline results.
- `[!NOTE]` for methods, formulas, architecture, experiments, metrics, and algorithms.
- `[!TIP]` for intuition, reading path, comparisons, and memory hooks.
- `[!WARNING]` for limitations, assumptions, caveats, uncertainty, and possible misreadings.

```markdown
> [!IMPORTANT]
> **关键点**
> Transformer 的核心贡献是证明只用注意力也能成为强大的序列转导主干架构。

> [!NOTE]
> **方法注**
> $QK^T$ 给出每个 query 对每个 key 的相似度；softmax 把相似度变成权重。

> [!TIP]
> **读法提示**
> 先看 Table 1 理解 self-attention 的路径长度优势，再读模型细节。

> [!WARNING]
> **注意**
> 注意力可视化是定性证据，不等同于严格因果解释。
```

The alert marker must be alone on its own line. Put the Chinese title on the next blockquote line in bold. Do not write `> [!IMPORTANT] 关键点`, because GitHub may display it as plain blockquote text instead of an alert.

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
- For formulas, produce GitHub-compatible LaTeX math by default; do not downgrade clear formulas into prose-only descriptions.
- For figures and tables, include visual/table content by default and do not fabricate missing content. Explain only what the figure, table, caption, or surrounding text supports.
- If the paper is long, process in batches and maintain a running glossary and claim list.
- If the user requests full text but token budget is limited, translate all major sections with condensed detail and say which appendix/supplementary parts were summarized.

## Quality Checks

Before final delivery, check:

- The Markdown renders without broken HTML tags.
- Display equations use fenced `math` blocks or plain `$$` blocks that GitHub can render.
- Equation numbers are not written with `\tag{...}`; use standalone text such as `**(1)**` immediately after the equation.
- GitHub-targeted math does not use blocked macros such as `\operatorname{...}`.
- LaTeX math is not nested inside raw HTML blocks or inline HTML spans.
- No `Color Legend` section is present unless the user explicitly asks for one.
- The top title does not include `annotated translation`.
- No `Translation note` or internal process note is present in the final deliverable.
- `Paper Information` is compact plain text with authors and institutions when available.
- All explanatory annotations use Markdown callout blocks, not raw HTML spans/divs.
- Section order matches the source paper as closely as extraction allows.
- Figures, tables, captions, and equations appear near their source discussion rather than being reduced to end notes only.
- Visual assets referenced by Markdown image links exist locally and use stable relative paths.
- If a PDF artifact is requested, `scripts/export_markdown_pdf.py` runs successfully. If it cannot make a PDF, explain the missing dependency without keeping HTML unless the user explicitly asks for a debugging preview.
- Display equations are valid LaTeX/high-fidelity math, and inline variables use math markup where useful.
- Every major claim remains linked to its source section, citation, figure, table, or equation where available.
- Limitations and uncertainty are marked in red, not hidden in neutral prose.

## References

- `references/annotation-style.md` - callout type meaning, good annotation targets, and annotation density guidance.
- `scripts/export_markdown_pdf.py` - convert translated Markdown into PDF for stable sharing when GitHub rendering is insufficient.

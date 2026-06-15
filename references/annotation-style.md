# Annotation Style

Use annotations to reduce reader effort, not to decorate the translation.

## Callout Types

- `[!IMPORTANT]`: core concept, key result, main claim, contribution.
- `[!NOTE]`: method, formula, experiment, architecture, metric, algorithm.
- `[!TIP]`: intuition, reading path, comparison, memory hook.
- `[!WARNING]`: limitation, assumption, caveat, uncertainty, possible misreading.

Use Markdown callout blocks for every annotation, including short notes. Do not use raw HTML spans or divs for annotation highlighting, because LaTeX math may fail to render inside raw HTML.

## Good Annotation Targets

- A term that would block comprehension.
- A formula whose symbols or purpose are not obvious.
- A figure/table that carries the paper's main evidence.
- A claim that depends on a hidden assumption.
- A result that is easy to overstate.
- A limitation that affects downstream use.

## Avoid

- Annotating every paragraph.
- Replacing translation with commentary.
- Adding unsupported background facts unless clearly marked as external context.
- Translating citations or changing equation/figure/table numbering.
- Putting LaTeX math inside raw HTML elements such as `<span>`, `<div>`, or `<strong>`.

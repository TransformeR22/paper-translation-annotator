# paper-translation-annotator 示例

本目录包含使用 `paper-translation-annotator` skill 生成并整理后的示例输出。

## 包含示例

- [attention-is-all-you-need.md](attention-is-all-you-need.md)：*Attention Is All You Need* 的中文翻译与注释示例。
- [explainable-token-level-noise-filtering.md](explainable-token-level-noise-filtering.md)：*Explainable Token-Level Noise Filtering for LLM Fine-tuning Datasets* 的中文翻译与注释示例。

## 图表资产

Markdown 示例中使用的图表裁剪图存放在 `assets/<paper-slug>/figures/` 下。

示例目录只包含 Markdown 预览所需的展示资产，不包含 PDF 中间渲染页和临时工作文件。

## 导出 PDF

在仓库根目录运行：

```bash
python3 scripts/export_markdown_pdf.py examples/attention-is-all-you-need.md -o examples/attention-is-all-you-need.pdf
```

也可以把输入文件换成另一个示例 Markdown。脚本会同时生成同名 HTML，便于检查 GitHub 无法稳定显示的公式、callout 和图表。

若需要稳定自动导出 PDF，建议先安装：

```bash
python3 -m pip install markdown weasyprint
```

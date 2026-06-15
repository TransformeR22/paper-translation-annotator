# paper-translation-annotator

将英文论文 PDF 翻译为中文 Markdown，同时尽量保留论文结构、图表、公式、引用和阅读顺序。

## 输出特点

- 标题保持干净，不附加 "annotated translation" 等额外后缀。
- 论文信息只保留作者和机构等必要元数据。
- 图表使用原文裁剪图，并尽量放在正文首次讨论附近。
- 公式、变量、希腊字母和复杂度表达使用 LaTeX 或高还原数学格式。
- 概念、公式、方法、假设、结果、局限和实践提示统一使用 Markdown callout 注释。

## 本地安装

将本目录复制到 Codex skills 目录：

```bash
cp -R skills/paper-translation-annotator ~/.codex/skills/
```

之后在 Codex 中通过 skill 名称调用，例如：

```text
$paper-translation-annotator https://arxiv.org/pdf/1706.03762
```

## 示例

`examples/` 目录包含两篇已生成的翻译示例，并带有对应的图表资产：

- `examples/attention-is-all-you-need.md`
- `examples/explainable-token-level-noise-filtering.md`

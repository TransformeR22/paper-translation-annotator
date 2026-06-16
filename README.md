# paper-translation-annotator

将英文论文 PDF 翻译为中文 Markdown，同时尽量保留论文结构、图表、公式、引用和阅读顺序。

## 兼容性

这个仓库按通用 `SKILL.md` 技能格式组织，根目录直接包含 `SKILL.md`。可用于 Codex，也可被 OpenClaw 及类似支持 `SKILL.md` 的本地代理应用从 Git 仓库或本地目录安装。

## 输出特点

- 论文信息只保留作者和机构等必要元数据。
- 图表使用原文裁剪图，并尽量放在正文首次讨论附近。
- 公式、变量、希腊字母和复杂度表达使用 LaTeX 或高还原数学格式。
- 概念、公式、方法、假设、结果、局限和实践提示统一使用 Markdown callout 注释。

## OpenClaw 安装与更新

若你的 OpenClaw 版本支持 `openclaw skills install`，可从 GitHub 安装到当前 workspace：

```bash
openclaw skills install git:TransformeR22/paper-translation-annotator@main
```

也可以从本地目录安装：

```bash
openclaw skills install ./skills/paper-translation-annotator
```

若 CLI 支持全局安装，可安装为所有本地 OpenClaw agent 共享：

```bash
openclaw skills install git:TransformeR22/paper-translation-annotator@main --global
```

Git/local 安装通常可通过重新执行安装命令刷新；若你的 OpenClaw/ClawHub 版本提供同步命令，则可使用对应的 `skills update` 或 `sync` 命令同步更新。

验证是否加载：

```bash
openclaw skills list
```

OpenClaw 会优先读取 `SKILL.md` frontmatter 中的 `name`、`description`、`homepage` 和 `metadata.openclaw`。本 skill 不需要 API key；辅助脚本需要 Python，完整 PDF 文本抽取建议安装 `pymupdf`。

```bash
python3 -m pip install pymupdf markdown weasyprint
```

## Codex 本地安装

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

- [examples/attention-is-all-you-need.md](examples/attention-is-all-you-need.md)
- [examples/explainable-token-level-noise-filtering.md](examples/explainable-token-level-noise-filtering.md)

## 导出 PDF

GitHub 对 Markdown callout、LaTeX 公式和本地图表的渲染不一定稳定。可以使用内置脚本把翻译结果导出为 PDF：

```bash
python3 scripts/export_markdown_pdf.py examples/attention-is-all-you-need.md -o examples/attention-is-all-you-need.pdf
```

脚本会自动处理本地图表路径、callout 高亮样式和 LaTeX 数学公式。若本机安装了 Chrome/Chromium 或 WeasyPrint，会自动生成 PDF。默认只保留 Markdown 和 PDF；只有显式传入 `--html` 或 `--html-only` 时才保留 HTML。

推荐安装 WeasyPrint 作为 PDF 后端：

```bash
python3 -m pip install markdown weasyprint
```

如果没有可用的 PDF 渲染器，脚本会提示需要安装的后端；默认不会留下 HTML 文件。

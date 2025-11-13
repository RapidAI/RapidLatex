# MathTranslate 使用说明

MathTranslate是一个用于翻译LaTeX数学文档的Python工具，同时保留数学符号。它支持单个LaTeX文件和整个arXiv论文的翻译，并提供Google Translate、Tencent Cloud Translation和OpenAI API等翻译服务。

## 主要功能
- 翻译LaTeX文档同时保留数学符号
- 支持arXiv论文批量翻译
- 自动调整宽表格以适应页面尺寸
- 支持多种翻译引擎
- 提供命令行参数定制翻译

## 安装与配置
```bash
# 安装包
pip install --upgrade mathtranslate

# 设置Tencent API凭据（中国大陆用户需要）
translate_tex --setkey

# 配置OpenAI API密钥
translate_tex --setopenaikey

# 配置默认设置
translate_tex --setdefault
```

## 核心翻译命令

### 1. 翻译单个LaTeX文件
```bash
translate_tex input.tex -o output.tex
```

### 2. 翻译arXiv论文
```bash
# 基本用法
translate_arxiv 2205.15510

# 自动编译生成PDF
translate_arxiv 2205.15510 --compile

# 不编译只生成LaTeX文件
translate_arxiv 2205.15510 --no-compile

# 使用OpenAI翻译引擎
translate_arxiv 2205.15510 --engine openai --nocache
```

### 3. 批量翻译arXiv论文
```bash
# 创建包含arXiv编号的文件（每个编号一行）
echo -e "2106.06295\n2205.15510" > arxiv_list.txt

# 使用-f/--file参数进行批量翻译
translate_arxiv --file arxiv_list.txt --engine openai --nocache
```

## 常用参数说明
| 参数 | 描述 |
|------|------|
| `-f/--file` | 指定包含arXiv编号的文件，每个编号一行 |
| `--engine` | 选择翻译引擎：google/tencent/openai，默认google |
| `-o` | 指定输出路径 |
| `--compile` | 翻译后自动编译生成PDF |
| `--no-compile` | 禁用自动编译 |
| `--nocache` | 禁用缓存，确保获取最新内容 |
| `-from` | 指定源语言，默认en |
| `-to` | 指定目标语言，默认zh-CN |
| `--debug` | 启用调试模式 |

## 高级功能

### 自动表格调整
程序会自动检测宽表格并进行调整：
- 7-10列：使用`\small`字体和0.4em间距
- 11-20列：使用`\footnotesize`字体和0.3em间距
- 21+列：使用`\tiny`字体和0.1em间距
- 表格会被包裹在`\resizebox{\textwidth}{!}{...}`中以适应页面宽度

### 自定义命令
可以通过命令文件添加自定义LaTeX命令：
```bash
translate_tex -commands custom_commands.txt input.tex -o output.tex
```

---

# MathTranslate Usage Guide

MathTranslate is a Python tool for translating LaTeX mathematical documents while preserving mathematical notation. It provides translation services for both single LaTeX files and entire arXiv papers, supporting Google Translate, Tencent Cloud Translation API, and OpenAI API.

## Key Features
- Translate LaTeX documents while preserving mathematical notation
- Support for batch translation of arXiv papers
- Automatic wide table resizing to fit page dimensions
- Multiple translation engines supported
- Command-line parameters for customized translation

## Installation and Configuration
```bash
# Install the package
pip install --upgrade mathtranslate

# Set Tencent API credentials (required for users in mainland China)
translate_tex --setkey

# Set OpenAI API key
translate_tex --setopenaikey

# Configure default settings
translate_tex --setdefault
```

## Core Translation Commands

### 1. Translate Single LaTeX File
```bash
translate_tex input.tex -o output.tex
```

### 2. Translate arXiv Paper
```bash
# Basic usage
translate_arxiv 2205.15510

# Automatically compile to PDF after translation
translate_arxiv 2205.15510 --compile

# Generate only LaTeX file without compilation
translate_arxiv 2205.15510 --no-compile

# Use OpenAI translation engine
translate_arxiv 2205.15510 --engine openai --nocache
```

### 3. Batch Translate arXiv Papers
```bash
# Create a file containing arXiv IDs (one per line)
echo -e "2106.06295\n2205.15510" > arxiv_list.txt

# Use -f/--file parameter for batch translation
translate_arxiv --file arxiv_list.txt --engine openai --nocache
```

## Common Parameter Descriptions
| Parameter | Description |
|-----------|-------------|
| `-f/--file` | Specify a file containing arXiv IDs, one per line |
| `--engine` | Choose translation engine: google/tencent/openai, default is google |
| `-o` | Specify output path |
| `--compile` | Automatically compile to PDF after translation |
| `--no-compile` | Disable automatic compilation |
| `--nocache` | Disable cache to ensure latest content |
| `-from` | Specify source language, default is en |
| `-to` | Specify target language, default is zh-CN |
| `--debug` | Enable debug mode |

## Advanced Features

### Automatic Table Resizing
The program automatically detects wide tables and adjusts them:
- 7-10 columns: Uses `\small` font with 0.4em spacing
- 11-20 columns: Uses `\footnotesize` font with 0.3em spacing
- 21+ columns: Uses `\tiny` font with 0.1em spacing
- Tables are wrapped in `\resizebox{\textwidth}{!}{...}` to fit page width

### Custom Commands
Custom LaTeX commands can be added via command file:
```bash
translate_tex -commands custom_commands.txt input.tex -o output.tex
```

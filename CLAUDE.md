# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MathTranslate is a Python tool for translating LaTeX mathematical documents while preserving mathematical notation. It provides translation services for both single LaTeX files and entire arXiv papers, supporting Google Translate and Tencent Cloud Translation APIs.

## Common Development Commands

### Installation and Setup
```bash
# Install the package
pip install --upgrade mathtranslate

# Set Tencent API credentials (required for users in mainland China)
translate_tex --setkey

# Configure default settings
translate_tex --setdefault
```

### Core Translation Commands
```bash
# Translate single LaTeX file
translate_tex input.tex -o output.tex

# Translate arXiv paper by ID
translate_arxiv 2205.15510

# Change translation engine (for mainland China users)
translate_tex -engine tencent input.tex -o output.tex

# Change source and target languages
translate_tex -from en -to zh-CN input.tex -o output.tex
```

### Compilation
```bash
# Compile translated LaTeX with XeLaTeX (required for Chinese support)
xelatex output.tex

# Automatic compilation after translation
translate_tex input.tex -o output.tex --compile
```

## Architecture Overview

### Core Translation Pipeline
1. **LaTeX Processing** (`process_latex.py`): Parses LaTeX structure, identifies translatable content, and protects mathematical expressions
2. **Text Processing** (`process_text.py`): Handles text segmentation, paragraph connection, and character limits
3. **Translation Engine** (`translate.py`): Manages translation via Google or Tencent APIs with retry logic and rate limiting
4. **File Processing** (`process_file.py`): Orchestrates the complete translation workflow

### Key Components

- **Config Management** (`config.py`): Centralized configuration for API keys, default languages, and paths
- **Caching System** (`cache.py`): LRU cache for translation results to reduce API calls
- **Translation Services**:
  - Google Translate via `mtranslate` library (default, limited in mainland China)
  - Tencent Cloud Translation API for China users (5M chars/month free quota)
- **ArXiv Integration** (`translate_arxiv.py`): Downloads and translates complete arXiv papers
- **Encoding Handling** (`encoding.py`): Manages file encoding detection and conversion

### LaTeX Command Processing
The system maintains extensive lists of LaTeX commands and environments that require special handling:
- Single-argument commands: `\textbf{}`, `\textit{}`
- Multi-argument commands: `\textcolor{red}{text}`
- Mathematical environments: `equation`, `align`, `gather`
- Custom commands can be defined via additional command files

### Translation Preservation Strategy
- Mathematical expressions are replaced with placeholder codes (`XMATHX_n`) during translation
- LaTeX commands and environments are preserved or translated based on context
- Bibliography entries and citations are handled separately to maintain references

## Configuration

### API Keys
- Google Translate: No configuration needed (may not work from mainland China)
- Tencent Cloud: Set via `translate_tex --setkey` or in `config.py`

### Default Settings
- Default engine: Google Translate
- Source language: English (`en`)
- Target language: Simplified Chinese (`zh-CN`)
- Thread count: 0 (auto-detect)

### File Locations
- Configuration: Stored in app data directory (platform-specific)
- Cache: `app_dir/cache/` with 5-item LRU limit
- Logs: `app_dir/translate_log`

## Testing

No formal test suite is present. Manual testing is performed via:
- Single file translation commands
- arXiv paper processing
- Mathematical expression preservation verification

## Dependencies

Key external dependencies:
- `mtranslate`: Google Translate API wrapper
- `selenium`: For Google Translate web interface fallback
- `tencentcloud-sdk-python`: Tencent Cloud API integration
- `tqdm`: Progress bars
- `regex`: Enhanced regular expressions
- `appdata`: Cross-platform app data directories

## Development Notes

- The codebase uses a modular design with clear separation between LaTeX processing, translation services, and file I/O
- Caching is essential for performance and cost control with paid APIs
- Error handling includes retry logic for network failures and rate limiting
- The system is designed to preserve mathematical notation integrity above all else
- Windows users may need to run commands as administrator for proper file access
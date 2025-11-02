# 自定义环境块翻译配置

MathTranslate 现在支持用户自定义需要翻译的 LaTeX 环境块和命令，提供了更精细的控制。

## 🎯 功能特性

### ✅ **自定义翻译环境**
- 可以指定哪些环境块需要翻译
- 可以指定哪些环境块不需要翻译
- 支持数学环境的排除保护

### ✅ **自定义翻译命令**
- 可以指定哪些 LaTeX 命令需要翻译
- 可以指定哪些命令不需要翻译
- 支持引用、标签等命令的排除

## 📝 配置方法

### 1. 创建或修改 `config.json` 文件

在 MathTranslate 目录下创建或修改 `config.json` 文件：

```json
{
  "openai": {
    "api_key": "your-api-key-here",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-3.5-turbo",
    "max_tokens": 8000,
    "temperature": 0.3,
    "chunk_size": 6000
  },

  "custom_environments": [
    "example",
    "definition",
    "lemma",
    "proposition",
    "remark",
    "algorithm",
    "algorithmic",
    "lstlisting"
  ],

  "custom_commands": [
    "newcommand",
    "renewcommand",
    "DeclareMathOperator"
  ],

  "skip_environments": [
    "equation",
    "align",
    "gather",
    "displaymath",
    "eqnarray",
    "multline",
    "tikzpicture",
    "cases",
    "matrix"
  ],

  "skip_commands": [
    "ref",
    "label",
    "cite",
    "bibitem",
    "input",
    "include",
    "bibliography",
    "usepackage",
    "documentclass",
    "begin",
    "end"
  ]
}
```

### 2. 配置选项说明

#### `custom_environments` (自定义环境)
**作用**: 指定需要翻译的额外环境块
**示例**:
```json
"custom_environments": [
  "example",      // 翻译示例环境
  "definition",   // 翻译定义环境
  "lemma",        // 翻译引理环境
  "algorithmic"   // 翻译算法环境
]
```

#### `skip_environments` (跳过环境)
**作用**: 指定不需要翻译的环境块
**默认包含**: 数学环境、图表环境等
**示例**:
```json
"skip_environments": [
  "equation",     // 跳过数学公式
  "align",        // 跳过对齐公式
  "tikzpicture"   // 跳过 TikZ 图形
]
```

#### `custom_commands` (自定义命令)
**作用**: 指定需要翻译的额外命令
**示例**:
```json
"custom_commands": [
  "newcommand",           // 翻译新定义命令内容
  "DeclareMathOperator"   // 翻译数学算子定义
]
```

#### `skip_commands` (跳过命令)
**作用**: 指定不需要翻译的命令
**默认包含**: 引用、标签、结构命令等
**示例**:
```json
"skip_commands": [
  "ref",           // 跳过引用
  "label",         // 跳过标签
  "cite",          // 跳过文献引用
  "input",         // 跳过输入命令
  "include"        // 跳过包含命令
]
```

## 📋 默认设置

### 默认翻译环境
- `abstract` (摘要)
- `acknowledgments` (致谢)
- `itemize` (无序列表)
- `enumerate` (有序列表)
- `description` (描述列表)
- `list` (列表)
- `proof` (证明)
- `quote` (引用)
- `spacing` (间距)

### 默认跳过环境
- `equation` (数学公式)
- `align` (对齐公式)
- `gather` (聚集公式)
- `displaymath` (显示数学)
- `eqnarray` (等式数组)

### 默认翻译命令
- `section` (章节)
- `subsection` (子章节)
- `subsubsection` (子子章节)
- `caption` (标题)
- `subcaption` (子标题)
- `footnote` (脚注)
- `paragraph` (段落)

### 默认跳过命令
- `ref` (引用)
- `label` (标签)
- `cite` (文献引用)
- `bibitem` (文献条目)

## 🧪 测试配置

使用测试脚本验证配置：

```bash
python test_custom_environments.py
```

输出示例：
```
Translation Analysis:
  - 'abstract': WILL BE TRANSLATED
  - 'example': WILL BE TRANSLATED (自定义环境)
  - 'theorem': DEFAULT (默认处理)
  - 'equation': SKIPPED (在跳过列表)
  - 'algorithmic': WILL BE TRANSLATED (自定义环境)
```

## 📖 使用场景

### 1. 学术论文
```json
{
  "custom_environments": ["theorem", "lemma", "proposition", "remark"],
  "skip_environments": ["equation", "align", "figure", "table"]
}
```

### 2. 算法论文
```json
{
  "custom_environments": ["algorithm", "algorithmic", "lstlisting"],
  "skip_environments": ["tikzpicture", "figure", "table"]
}
```

### 3. 技术文档
```json
{
  "custom_environments": ["example", "definition", "note", "warning"],
  "skip_environments": ["verbatim", "lstlisting"]
}
```

## ⚠️ 注意事项

### 1. 数学环境保护
- 所有数学环境默认在跳过列表中
- 确保数学公式不被意外翻译
- 保留 LaTeX 数学符号和公式结构

### 2. 结构完整性
- 跳过文档结构命令 (`documentclass`, `begin`, `end`)
- 保持 LaTeX 文档的基本结构
- 避免破坏文档编译

### 3. 引用一致性
- 跳过引用相关命令 (`ref`, `label`, `cite`)
- 确保交叉引用正常工作
- 保持文献引用的准确性

### 4. 配置优先级
- `skip_environments` > `custom_environments`
- `skip_commands` > `custom_commands`
- 跳过列表优先于翻译列表

## 🔧 高级用法

### 动态配置
可以为不同类型文档创建不同的配置文件：

```bash
# 学术论文配置
cp config_academic.json config.json

# 算法论文配置
cp config_algorithm.json config.json

# 技术文档配置
cp config_technical.json config.json
```

### 批量配置
```json
{
  "custom_environments": [
    "example", "definition", "lemma", "proposition",
    "remark", "corollary", "conjecture", "claim"
  ],
  "custom_commands": [
    "newcommand", "renewcommand", "providecommand",
    "DeclareMathOperator", "newenvironment"
  ]
}
```

通过这种灵活的配置机制，用户可以根据具体的文档类型和翻译需求，精确控制哪些 LaTeX 环境和命令需要翻译，哪些需要保持原样。
# MathTranslate API 文档

## 概述

MathTranslate API 提供文档翻译服务，支持 LaTeX 文档、PDF 文件和压缩包的翻译。支持多种翻译引擎，包括 Google、Tencent Cloud、OpenAI 等。

## 快速开始

### 1. 安装依赖

```bash
pip install -r api_requirements.txt
```

### 2. 启动服务

```bash
python api_app.py
```

服务将在 `http://localhost:5000` 启动。

### 3. 基本使用流程

1. 上传文件或指定 ArXiv ID
2. 启动翻译任务
3. 查询翻译状态
4. 下载翻译结果

## API 端点

### 1. 健康检查

**GET** `/api/health`

检查服务状态。

**响应示例:**
```json
{
  "status": "healthy",
  "timestamp": "2025-11-02T07:30:00.000000",
  "version": "1.0.0"
}
```

### 2. 获取翻译引擎

**GET** `/api/engines`

获取可用的翻译引擎列表。

**响应示例:**
```json
{
  "engines": [
    {
      "id": "google",
      "name": "Google Translate",
      "description": "Free Google translation service"
    },
    {
      "id": "tencent",
      "name": "Tencent Cloud",
      "description": "Tencent Cloud translation service"
    },
    {
      "id": "tencentcloud",
      "name": "Tencent Cloud",
      "description": "Tencent Cloud translation service"
    },
    {
      "id": "openai",
      "name": "OpenAI",
      "description": "OpenAI GPT translation service"
    }
  ]
}
```

### 3. 上传文件

**POST** `/api/upload`

上传文件进行翻译。

**请求参数:**
- `file`: 要翻译的文件（multipart/form-data）

**支持的文件格式:**
- `.tex` - LaTeX 文档
- `.pdf` - PDF 文档
- `.zip` - ZIP 压缩包
- `.tar.gz` - tar.gz 压缩包
- `.tar.bz2` - tar.bz2 压缩包
- `.tar.xz` - tar.xz 压缩包

**响应示例:**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "File uploaded successfully",
  "filename": "document.tex"
}
```

### 4. 翻译 ArXiv 论文

**POST** `/api/arxiv/<arxiv_id>`

翻译指定 ArXiv ID 的论文。

**URL 参数:**
- `arxiv_id`: ArXiv 论文 ID（如: 2301.00001）

**请求体 (可选):**
```json
{
  "engine": "openai",
  "language_from": "en",
  "language_to": "zh-CN",
  "compile": true,
  "nocache": false
}
```

**响应示例:**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174001",
  "message": "ArXiv translation task created for 2301.00001",
  "arxiv_id": "2301.00001"
}
```

### 5. 启动翻译任务

**POST** `/api/translate/<task_id>`

为已上传的文件启动翻译任务。

**URL 参数:**
- `task_id`: 任务 ID

**请求体:**
```json
{
  "engine": "openai",
  "language_from": "en",
  "language_to": "zh-CN",
  "compile": true,
  "nocache": false,
  "notranslate": false
}
```

**参数说明:**
- `engine`: 翻译引擎 (google, tencent, tencentcloud, openai)
- `language_from`: 源语言 (默认: en)
- `language_to`: 目标语言 (默认: zh-CN)
- `compile`: 是否编译 PDF (默认: true)
- `nocache`: 是否禁用缓存 (默认: false)
- `notranslate`: 是否跳过翻译 (默认: false)

**响应示例:**
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "message": "Translation started",
  "options": {
    "engine": "openai",
    "language_from": "en",
    "language_to": "zh-CN",
    "compile": true,
    "nocache": false,
    "notranslate": false
  }
}
```

### 6. 查询任务状态

**GET** `/api/status/<task_id>`

查询翻译任务的当前状态。

**URL 参数:**
- `task_id`: 任务 ID

**响应示例:**
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "completed",
  "message": "Translation completed successfully!",
  "progress": 100,
  "created_at": "2025-11-02T07:30:00.000000",
  "updated_at": "2025-11-02T07:35:00.000000",
  "input_filename": "document.tex",
  "options": {
    "engine": "openai",
    "language_from": "en",
    "language_to": "zh-CN"
  },
  "result": {
    "files": [
      {
        "type": "pdf",
        "filename": "123e4567-e89b-12d3-a456-426614174000_document.pdf",
        "path": "123e4567-e89b-12d3-a456-426614174000_document.pdf"
      },
      {
        "type": "zip",
        "filename": "123e4567-e89b-12d3-a456-426614174000.zip",
        "path": "123e4567-e89b-12d3-a456-426614174000.zip"
      }
    ],
    "translated_files": ["document"]
  }
}
```

**状态说明:**
- `pending`: 等待开始翻译
- `processing`: 正在翻译中
- `completed`: 翻译完成
- `failed`: 翻译失败
- `cancelled`: 任务已取消

### 7. 下载文件

**GET** `/api/download/<task_id>/<filename>`

下载翻译后的文件。

**URL 参数:**
- `task_id`: 任务 ID
- `filename`: 文件名

**示例:**
```
GET /api/download/123e4567-e89b-12d3-a456-426614174000/123e4567-e89b-12d3-a456-426614174000.zip
```

### 8. 列出所有任务

**GET** `/api/tasks`

获取所有任务列表。

**响应示例:**
```json
{
  "tasks": [
    {
      "id": "123e4567-e89b-12d3-a456-426614174000",
      "status": "completed",
      "message": "Translation completed successfully!",
      "progress": 100,
      "created_at": "2025-11-02T07:30:00.000000",
      "updated_at": "2025-11-02T07:35:00.000000"
    }
  ],
  "total": 1
}
```

### 9. 删除任务

**DELETE** `/api/tasks/<task_id>`

删除指定任务及其相关文件。

**URL 参数:**
- `task_id`: 任务 ID

**响应示例:**
```json
{
  "message": "Task deleted successfully"
}
```

## 使用示例

### Python 客户端示例

```python
import requests
import json
import time

# API 基础 URL
BASE_URL = "http://localhost:5000/api"

# 1. 上传文件
def upload_file(file_path):
    with open(file_path, 'rb') as f:
        files = {'file': f}
        response = requests.post(f"{BASE_URL}/upload", files=files)

    if response.status_code == 200:
        return response.json()['task_id']
    else:
        raise Exception(f"Upload failed: {response.json()}")

# 2. 启动翻译
def start_translation(task_id, engine='openai'):
    data = {
        'engine': engine,
        'language_from': 'en',
        'language_to': 'zh-CN',
        'compile': True
    }
    response = requests.post(f"{BASE_URL}/translate/{task_id}", json=data)

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Translation start failed: {response.json()}")

# 3. 查询状态
def check_status(task_id):
    response = requests.get(f"{BASE_URL}/status/{task_id}")

    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Status check failed: {response.json()}")

# 4. 下载文件
def download_file(task_id, filename, save_path):
    response = requests.get(f"{BASE_URL}/download/{task_id}/{filename}")

    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
        return True
    else:
        raise Exception(f"Download failed: {response.status_code}")

# 完整示例
def translate_document(file_path, output_dir, engine='openai'):
    try:
        # 上传文件
        task_id = upload_file(file_path)
        print(f"File uploaded. Task ID: {task_id}")

        # 启动翻译
        start_translation(task_id, engine)
        print("Translation started...")

        # 轮询状态
        while True:
            status = check_status(task_id)
            print(f"Status: {status['status']}, Progress: {status['progress']}%")

            if status['status'] == 'completed':
                break
            elif status['status'] == 'failed':
                raise Exception(f"Translation failed: {status['message']}")

            time.sleep(5)

        # 下载结果
        if 'result' in status and 'files' in status['result']:
            for file_info in status['result']['files']:
                if file_info['type'] == 'zip':
                    output_path = f"{output_dir}/{file_info['filename']}"
                    download_file(task_id, file_info['path'], output_path)
                    print(f"Downloaded: {output_path}")

        print("Translation completed successfully!")

    except Exception as e:
        print(f"Error: {e}")

# 使用示例
if __name__ == "__main__":
    translate_document("document.tex", "./output", "openai")
```

### curl 示例

```bash
# 1. 上传文件
curl -X POST -F "file=@document.tex" http://localhost:5000/api/upload

# 2. 启动翻译 (假设获得 task_id: 123e4567-e89b-12d3-a456-426614174000)
curl -X POST -H "Content-Type: application/json" \
  -d '{"engine":"openai","language_from":"en","language_to":"zh-CN"}' \
  http://localhost:5000/api/translate/123e4567-e89b-12d3-a456-426614174000

# 3. 查询状态
curl http://localhost:5000/api/status/123e4567-e89b-12d3-a456-426614174000

# 4. 下载文件
curl -O http://localhost:5000/api/download/123e4567-e89b-12d3-a456-426614174000/123e4567-e89b-12d3-a456-426614174000.zip
```

### ArXiv 翻译示例

```python
import requests

BASE_URL = "http://localhost:5000/api"

# 翻译 ArXiv 论文
def translate_arxiv(arxiv_id, engine='openai'):
    data = {
        'engine': engine,
        'language_from': 'en',
        'language_to': 'zh-CN',
        'compile': True
    }

    response = requests.post(f"{BASE_URL}/arxiv/{arxiv_id}", json=data)

    if response.status_code == 200:
        return response.json()['task_id']
    else:
        raise Exception(f"ArXiv translation failed: {response.json()}")

# 使用示例
task_id = translate_arxiv("2301.00001", "openai")
print(f"ArXiv translation started. Task ID: {task_id}")
```

## 配置说明

### 翻译引擎配置

确保 `config.json` 包含相应的引擎配置：

```json
{
  "openai": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "your_openai_api_key",
    "model": "gpt-3.5-turbo",
    "max_tokens": 8000,
    "temperature": 0.3,
    "chunk_size": 6000
  },
  "tencent": {
    "secret_id": "your_tencent_secret_id",
    "secret_key": "your_tencent_secret_key",
    "region": "ap-shanghai"
  }
}
```

### 文件大小限制

- 最大文件大小: 100MB
- 支持的压缩格式: ZIP, tar.gz, tar.bz2, tar.xz

### 并发处理

- 每个翻译任务在独立线程中运行
- 支持多个任务并发执行
- 任务状态实时更新

## 错误处理

常见错误码及处理:

- `400`: 请求参数错误
- `403`: 文件访问权限不足
- `404`: 任务或文件不存在
- `413`: 文件过大
- `500`: 服务器内部错误

错误响应格式:
```json
{
  "error": "Error description"
}
```

## 注意事项

1. **文件安全**: 上传的文件会临时存储，任务完成后可删除
2. **资源管理**: 大文件翻译可能需要较长时间，请合理设置超时
3. **引擎配额**: 各翻译引擎可能有调用限制，请合理使用
4. **缓存管理**: 默认启用翻译缓存，可通过 `nocache: true` 禁用

## 故障排除

### 常见问题

1. **文件上传失败**
   - 检查文件格式是否支持
   - 确认文件大小不超过限制
   - 检查磁盘空间是否充足

2. **翻译失败**
   - 检查引擎配置是否正确
   - 确认网络连接正常
   - 查看任务详细错误信息

3. **编译失败**
   - 检查 LaTeX 文档语法
   - 确认系统安装了 XeLaTeX
   - 查看编译日志

### 日志查看

API 服务运行时会输出详细日志，包括：
- 任务创建和状态更新
- 文件处理进度
- 错误信息和调试信息

## 版本信息

- API 版本: 1.0.0
- 支持的 Python 版本: 3.7+
- 依赖框架: Flask 2.3.3
# API 参考文档

本文档提供了文件服务器的详细API参考、使用示例、SDK用法和配置说明。

## 1. FastAPI REST API

### 1.1. 基础信息
- **基础URL**: `http://localhost:8087`
- **认证**: 暂无（开发阶段）
- **内容类型**: `application/json` 或 `multipart/form-data`

### 1.2. 端点列表

---

#### **GET /health**
检查服务健康状态。

**响应示例:**
```json
{
  "status": "ok"
}
```

---

#### **GET /get_supported_file_types**
获取系统支持的文件类型列表。

**响应示例:**
```json
{
  "status": "ok",
  "message": "Supported file types",
  "data": {
    "supported_file_types": [
      ".doc", ".docx", ".pdf", ".png", ".jpg", 
      ".ppt", ".pptx", ".xls", ".xlsx", ".txt"
    ]
  }
}
```

---

#### **POST /upload_minio**
上传文件到对象存储。

**请求参数:**
- `upload_file` (file): 要上传的文件
- `user_id` (string, 可选): 用户ID，默认为 "default"

**响应示例:**
```json
{
  "status": "success",
  "message": "File uploaded successfully",
  "data": {
    "file_id": "uuid-string",
    "filename": "document.pdf",
    "object_path": "user/default_file_space/uuid/document.pdf",
    "public_url": "http://localhost:9000/bucket/path/to/file",
    "file_size": 1024000,
    "content_type": "application/pdf"
  }
}
```

---

#### **POST /process**
处理上传的文档（OCR识别、向量化等）。

**请求参数:**
- `user_id` (string): 用户ID
- `file_url` (string): 文件的公网URL
- `knowledge_base_id` (string, 可选): 知识库ID，默认为 "df_{user_id}"
- `mode` (string, 可选): 处理模式，默认为 "simple"

**处理模式:**
- `simple`: 基础OCR处理和向量化
- `normal`: 基础文件处理
- `ocr`: OCR识别处理
- `graph`: 图谱处理

**响应示例:**
```json
{
  "status": "ok",
  "message": "File processed successfully",
  "data": {
    "user_id": "test_user",
    "knowledge_base_id": "df_test_user",
    "mode": "simple",
    "file_url": "http://example.com/file.pdf",
    "markdown_public_url": "http://example.com/markdown/uuid.md",
    "pdf_file_public_url": "http://example.com/pdf/uuid.pdf",
    "file_uuid": "uuid-string"
  }
}
```

---

#### **POST /delete_file**
从系统中删除文件（包括对象存储和向量数据库）。

**请求参数:**
- `user_id` (string): 用户ID
- `file_id` (string): 文件ID
- `knowledge_base_id` (string, 可选): 知识库ID，默认为 "df_{user_id}"

**响应示例:**
```json
{
  "status": "ok",
  "message": "File deleted successfully"
}
```

---

#### **POST /graph/knowledge_base**
对知识库进行图谱相关操作。

**请求参数:**
- `user_id` (string): 用户ID
- `knowledge_base_id` (string): 知识库ID
- `mode` (string): 操作模式 (`produce` / `get`)
- `level` (string): 图谱层级 (`document` / `subject`)

**响应示例 (获取图谱):**
```json
{
  "status": "ok",
  "message": "Document graph fetched successfully",
  "data": {
    "nodes": [{"id": "node1", "label": "概念A", "type": "concept"}],
    "edges": [{"source": "node1", "target": "node2", "relationship": "related_to"}]
  }
}
```

### 1.3. 错误响应

**标准错误格式:**
```json
{
  "detail": "错误描述信息"
}
```

**常见HTTP状态码:**
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源不存在
- `422 Unprocessable Entity`: 数据验证失败
- `500 Internal Server Error`: 服务器内部错误

## 2. 使用示例

### 2.1. cURL 示例

**健康检查:**
```bash
curl -X GET http://localhost:8087/health
```

**文件上传:**
```bash
curl -X POST http://localhost:8087/upload_minio \
  -F "upload_file=@/path/to/file.pdf" \
  -F "user_id=user123"
```

**文件处理:**
```bash
curl -X POST http://localhost:8087/process \
  -F "user_id=user123" \
  -F "file_url=http://minio_url/bucket/file.pdf" \
  -F "mode=simple"
```

### 2.2. Python `requests` 示例

```python
import requests

# 文件上传
with open('document.pdf', 'rb') as f:
    response = requests.post(
        'http://localhost:8087/upload_minio',
        files={'upload_file': f},
        data={'user_id': 'user123'}
    )
    print(response.json())

# 文件处理
response = requests.post(
    'http://localhost:8087/process',
    data={
        'user_id': 'user123',
        'file_url': 'http://minio_url/bucket/file.pdf',
        'mode': 'simple'
    }
)
print(response.json())
```

## 3. Python SDK

### 3.1. 安装
```bash
pip install -e .
```

### 3.2. 基本使用
```python
from src.file_server_core import OCRProcessor, StorageManager, GraphManager

# OCR处理
processor = OCRProcessor('mistral')
text = await processor.aprocess_file('document.pdf')

# 存储管理
storage = StorageManager(config)
await storage.upload_file(file_data, user_id, filename)

# 图谱操作
graph = GraphManager(config)
result = await graph.produce_document_graph(user_id, kb_id)
```

## 4. 配置与限制

### 4.1. 服务配置
修改 `config/config.yaml`:
```yaml
server_components:
  minio:
    host: "localhost"
    port: 9000
    # ...
  pg_vector:
    host: "localhost"
    port: 5432
    # ...
```

### 4.2. OCR配置
设置环境变量:
```bash
export MISTRAL_API_KEY="your-api-key"
```

### 4.3. 限制说明
- **文件大小**: 单文件最大10MB（OCR处理）。
- **支持格式**: 包含主流文档、文本、图像、PDF和代码文件。
- **并发数**: OCR处理默认为5个并发任务。

## 5. 监控和日志

- **日志位置**: `app/logs/YYYY-MM-DD.log`
- **健康检查**: 定期访问 `/health` 端点。

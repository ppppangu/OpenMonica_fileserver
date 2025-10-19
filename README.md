# 文档处理与知识库管理系统

一个基于 FastAPI 的智能文档处理系统，支持多种格式文档的解析、向量化存储和知识库管理。

## 快速开始

### 自部署方式

1. **克隆项目**
   ```bash
   git clone <your-repo-url>
   cd file_server
   ```

2. **安装依赖**
   ```bash
   uv sync
   ```

3. **配置环境**
   
   编辑 `config.yaml` 文件，配置以下组件：

   ```yaml
   # 数据库配置
   server_components:
     pg_vector:
       host: "your-postgres-host"
       port: "5432"
       user: "postgres"
       password: "your-password"
       database: "postgres"
       active: true
     
     # 对象存储配置
     minio:
       host: "your-minio-host"
       port: 9000
       access_key: "your-access-key"
       secret_key: "your-secret-key"
       bucket_name: "your-bucket"
       region: "us-east-1"
       active: true
   
   # 模型配置
   api:
     # 嵌入模型配置
     language_embedding:
       - name: "bge-m3"
         url: "your-embedding-model-url"
         key: "your-api-key"
         alias: "bge-m3"
     
     # 多模态大模型配置
     multimodal_llm:
       - name: "Qwen/Qwen2.5-VL-32B-Instruct"
         url: "your-multimodal-llm-url" 
         key: "your-api-key"
         alias: "Qwen2.5-VL-32B-Instruct"
   ```

4. **启动服务**
   ```bash
   uv run uvicorn main:app --host 0.0.0.0 --port 8087
   ```

### 云端使用方式

通过 API 密钥初始化用户实例后，可以使用以下功能：

## API 使用说明

### 1. 用户实例初始化

用户填写密钥后自动初始化一个用户实例，获得独立的文档处理空间。

### 2. 知识库管理

#### 创建知识库
```python
# 创建新的知识库
user_instance.create_knowledgebase(
    knowledge_base_name="my_knowledge_base",
    description="知识库描述"
)
```

#### 列出知识库
```python
# 获取用户所有知识库
knowledge_bases = user_instance.list_knowledgebase()
```

#### 删除知识库
```python
# 删除指定知识库
user_instance.delete_knowledgebase(knowledge_base_id="kb_id")
```

### 3. 文档处理流程

#### 上传文件
```python
# 上传文件到知识库（非阻塞）
document_id = user_instance.upload_file(
    file_path="document.pdf",
    knowledge_base_id="kb_id",
    mode="ocr"  # 可选: "simple", "ocr", "graph"
)
```

上传完成后立即返回 `document_id`，文档处理在后台异步进行。

#### 查看文档状态
```python
# 列出知识库中的文档及其状态
documents = user_instance.list_documents(knowledge_base_id="kb_id")

# 文档状态说明：
# - "pending": 等待处理
# - "processing": 处理中
# - "completed": 处理完成
# - "failed": 处理失败
```

#### 获取文档内容
```python
# 等待文档处理完成后，获取完整解析内容
document = user_instance.get_document(document_id="doc_id")
content = document.get_content()  # 获取完整的解析内容
```

## 支持的文件格式

- **文档类型**: PDF, DOC, DOCX, TXT, MD
- **图片类型**: PNG, JPG, JPEG
- **表格类型**: XLS, XLSX, CSV

## 处理模式说明

- **simple**: 基础文本提取，不使用 OCR
- **ocr**: 使用 OCR 技术提取图片和扫描文档中的文字
- **graph**: 构建文档知识图谱，提取实体关系

## 健康检查

```bash
curl http://localhost:8087/health
```

## 依赖组件

- **PostgreSQL with pgvector**: 向量数据库存储
- **MinIO**: 对象存储服务
- **MinerU**: OCR 文档解析服务
- **嵌入模型**: 文档向量化
- **多模态大模型**: 智能文档理解

## 开发说明

项目使用 Python 3.11+ 和 uv 包管理器，基于 FastAPI 框架构建。

### 启动开发服务器
```bash
uv run uvicorn main:app --http httptools --host 0.0.0.0 --port 8087 --log-level debug --access-log --reload
```

## 许可证

[在此添加许可证信息]
# 快速开始指南

## 🚀 5分钟快速部署

### 1. 克隆项目
```bash
git clone <repository-url>
cd file_server
```

### 2. 安装依赖
```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 3. 配置环境

#### 3.1 配置文件
```bash
# 复制示例配置（如果存在）
cp config/config.yaml.example config/config.yaml

# 编辑配置文件
nano config/config.yaml
```

#### 3.2 最小化配置示例
```yaml
# config/config.yaml
api:
  title: "File Server API"
  version: "1.0.0"

server_components:
  minio:
    host: "localhost" 
    port: 9000
    access_key: "minioadmin"
    secret_key: "minioadmin"
    bucket_name: "file-server"
    use_public_url: false
    
  pg_vector:
    host: "localhost"
    port: 5432
    database: "file_server"
    user: "postgres"
    password: "password"
```

#### 3.3 环境变量
```bash
# 创建 .env 文件
cat > .env << 'EOF'
# OCR 配置（可选）
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_OCR_MODEL=mistral-ocr-latest
EOF
```

### 4. 启动服务
```bash
# 开发模式（自动重载）
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8087

# 生产模式
uv run uvicorn main:app --host 0.0.0.0 --port 8087
```

### 5. 验证部署
```bash
# 健康检查
curl http://localhost:8087/health

# 获取支持的文件类型
curl http://localhost:8087/get_supported_file_types
```

## 🧪 快速测试

### 测试文件上传
```bash
curl -X POST "http://localhost:8087/upload_minio" \
  -H "Content-Type: multipart/form-data" \
  -F "upload_file=@test.pdf" \
  -F "user_id=test_user"
```

### 测试OCR处理（需要API密钥）
```bash
# 上传并处理文档
curl -X POST "http://localhost:8087/process" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "user_id=test_user" \
  -d "file_url=http://your-domain/path/to/file.pdf" \
  -d "mode=simple"
```

## 📝 Python SDK 快速使用

### 安装核心库
```bash
pip install -e .
```

### OCR处理示例
```python
import asyncio
from file_server_core.ocr import OCRProcessor

async def quick_ocr_test():
    # 初始化OCR处理器
    processor = OCRProcessor('mistral')
    
    # 检查支持的供应商
    providers = processor.get_supported_providers()
    print(f"支持的OCR供应商: {providers}")
    
    # 处理文档（需要设置MISTRAL_API_KEY）
    if 'mistral' in providers:
        try:
            text = await processor.aprocess_file('test_document.pdf')
            print(f"成功提取 {len(text)} 字符")
        except Exception as e:
            print(f"处理失败: {e}")

# 运行测试
asyncio.run(quick_ocr_test())
```

### 工具函数使用
```python
from file_server_core.utils import get_supported_file_types
from file_server_core.utils.config_utils import read_config

# 获取支持的文件类型
file_types = get_supported_file_types()
print("支持的文档类型:", file_types['document_types'][:5])

# 读取配置
config = read_config()
print("MinIO配置:", config['server_components']['minio']['host'])
```

## 🐳 Docker 快速部署（可选）

### 创建 Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install -e .

EXPOSE 8087

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8087"]
```

### 构建和运行
```bash
# 构建镜像
docker build -t file-server .

# 运行容器
docker run -p 8087:8087 \
  -e MISTRAL_API_KEY=your_api_key \
  -v $(pwd)/config:/app/config \
  file-server
```

## ⚙️ 依赖服务配置

### MinIO 对象存储
```bash
# 使用Docker运行MinIO
docker run -d \
  --name minio \
  -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# 访问MinIO控制台: http://localhost:9001
```

### PostgreSQL + pgvector
```bash
# 使用Docker运行PostgreSQL
docker run -d \
  --name postgres \
  -p 5432:5432 \
  -e POSTGRES_DB=file_server \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  pgvector/pgvector:pg16

# 创建数据库和扩展
psql -h localhost -U postgres -d file_server -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

## 🔍 故障排除

### 常见问题

#### 1. 配置文件找不到
```bash
# 检查配置文件是否存在
ls -la config/config.yaml

# 如果不存在，创建基本配置
mkdir -p config
cp docs/examples/config.yaml config/
```

#### 2. OCR API密钥问题
```bash
# 检查环境变量
echo $MISTRAL_API_KEY

# 或在代码中验证
python -c "
from file_server_core.ocr.config.mistral import MistralConfig
config = MistralConfig()
print('API Key 已设置:', bool(config.validate()))
"
```

#### 3. 依赖安装失败
```bash
# 清理pip缓存
pip cache purge

# 更新pip
pip install --upgrade pip

# 重新安装
pip install -e .
```

#### 4. 端口被占用
```bash
# 检查端口占用
lsof -i :8087

# 使用其他端口
uvicorn main:app --port 8088
```

### 日志调试
```bash
# 查看应用日志
tail -f logs/$(date +%Y-%m-%d).log

# 启用详细日志
export LOG_LEVEL=DEBUG
uvicorn main:app --log-level debug
```

## 🎯 下一步

1. **配置OCR服务** - 获取Mistral API密钥开始使用OCR功能
2. **设置存储** - 配置MinIO和PostgreSQL
3. **探索API** - 查看 [API 参考文档](API_REFERENCE.md)
4. **开发自定义功能** - 参考 [开发文档](DEVELOPMENT.md)
5. **部署到生产** - 配置反向代理、SSL证书等

## 📞 获取帮助

- 查看 [开发文档](DEVELOPMENT.md) 了解详细架构
- 查看 [API参考](API_REFERENCE.md) 了解接口详情
- 运行示例代码: `python examples/basic_usage.py`
- 使用CLI工具: `python -m file_server_core.cli --help`

🎉 恭喜！你已成功部署了文档处理服务器！
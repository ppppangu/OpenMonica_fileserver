# 开发文档

## 项目架构

### 目录结构
```
file_server/
├── file_server_core/          # 🎯 核心PyPI包
│   ├── ocr/                   # OCR文档识别模块
│   │   ├── base.py           # 抽象基类
│   │   ├── factory.py        # 工厂模式
│   │   ├── processor.py      # 统一处理器入口
│   │   ├── config/           # 配置管理
│   │   │   ├── base.py       # 基础配置类
│   │   │   └── mistral.py    # Mistral配置
│   │   └── providers/        # OCR供应商实现
│   │       └── mistral.py    # Mistral OCR实现
│   ├── storage/              # 存储管理（MinIO + 向量数据库）
│   ├── graph/                # 知识图谱生成与查询
│   ├── models/               # 数据模型定义
│   └── utils/                # 工具函数
├── config/                   # 配置文件
├── scripts/                  # 遗留脚本文件
├── examples/                 # 使用示例
├── compatibility_adapter.py  # 兼容性适配器
└── main.py                   # FastAPI应用入口
```

## 快速开始

### 安装依赖
```bash
pip install -r requirements.txt
# 或者安装开发版本
pip install -e .
```

### 环境配置
1. 复制配置文件：
```bash
cp config/config.yaml.example config/config.yaml
```

2. 设置环境变量（用于OCR功能）：
```bash
# .env 文件
MISTRAL_API_KEY=your_mistral_api_key_here
MISTRAL_OCR_MODEL=mistral-ocr-latest
```

### 运行服务
```bash
# 开发模式
uv run uvicorn main:app --reload --host 0.0.0.0 --port 8087

# 生产模式
uv run uvicorn main:app --host 0.0.0.0 --port 8087
```

## 模块使用指南

### 1. OCR模块 - 文档识别

#### 基本使用
```python
from file_server_core.ocr import OCRProcessor

# 初始化处理器
processor = OCRProcessor(provider_name="mistral")

# 同步处理单个文件
text = processor.process_file("document.pdf")

# 异步处理
import asyncio
async def process():
    text = await processor.aprocess_file("document.pdf")
    return text
```

#### 批量处理目录
```python
# 同步批量处理
results = processor.process_directory("documents/", exts=['.pdf', '.png'])

# 异步批量处理（推荐）
results = await processor.aprocess_directory(
    "documents/", 
    exts=['.pdf', '.png'], 
    concurrency=5
)
```

#### 切换OCR供应商
```python
# 查看支持的供应商
providers = processor.get_supported_providers()
print(providers)  # ['mistral']

# 运行时切换供应商
processor.switch_provider('mistral')  # 当前只支持mistral
```

#### 支持的文件类型
- PDF文档 (`.pdf`)
- 图片文件 (`.png`, `.jpg`, `.jpeg`, `.avif`)
- Office文档 (`.pptx`, `.docx`)

#### 输出结果
- **Markdown文件**: `原文件名.md`
- **图片文件**: `原文件名_images/img-{i}.jpeg`

### 2. 存储模块 - 文件存储

```python
from file_server_core.storage import StorageManager
from file_server_core.utils.config_utils import read_config

config = read_config()
storage = StorageManager(config)
await storage.initialize()

# 上传文件
result = await storage.upload_file(file_data, user_id, filename)

# 删除文件
await storage.delete_file(user_id, file_id, knowledge_base_id)
```

### 3. 图谱模块 - 知识图谱

```python
from file_server_core.graph import GraphManager

config = read_config()
graph = GraphManager(config)

# 生成文档级图谱
result = await graph.produce_document_graph(user_id, knowledge_base_id)

# 获取文档图谱
graph_data = await graph.get_documents_graph(user_id, knowledge_base_id)
```

### 4. 工具函数

```python
from file_server_core.utils import get_supported_file_types, upload_file_to_minio
from file_server_core.utils.config_utils import read_config

# 获取支持的文件类型
file_types = get_supported_file_types()

# 读取配置
config = read_config()
```

## API兼容性

现有的FastAPI端点保持完全兼容：

- `GET /health` - 健康检查
- `GET /get_supported_file_types` - 获取支持的文件类型
- `POST /upload_minio` - 文件上传
- `POST /process` - 文档处理
- `POST /delete_file` - 文件删除
- `POST /graph/knowledge_base` - 图谱操作

## CLI工具

```bash
# 查看版本
python -m file_server_core.cli --version

# 健康检查
python -m file_server_core.cli --health

# 测试配置
python -m file_server_core.cli --test-config
```

## 开发指南

### 添加新的OCR供应商

1. **创建配置类** (`file_server_core/ocr/config/your_provider.py`):
```python
from .base import BaseConfig

class YourProviderConfig(BaseConfig):
    def __init__(self):
        super().__init__()
        self.api_key = self._get_env_var('YOUR_PROVIDER_API_KEY')
        self.model = self._get_env_var('YOUR_PROVIDER_MODEL', 'default-model')

    def validate(self) -> bool:
        return bool(self.api_key)
```

2. **实现供应商类** (`file_server_core/ocr/providers/your_provider.py`):
```python
from ..base import BaseOCRProvider
from ..config.your_provider import YourProviderConfig

class YourProviderOCR(BaseOCRProvider):
    def __init__(self, config: YourProviderConfig = None):
        super().__init__(config or YourProviderConfig())

    def process_file(self, file_path):
        # 实现文件处理逻辑
        pass

    def process_url(self, url: str) -> str:
        # 实现URL处理逻辑（可选）
        pass
```

3. **注册到工厂** (`file_server_core/ocr/factory.py`):
```python
from .providers.your_provider import YourProviderOCR
from .config.your_provider import YourProviderConfig

# 在 _providers 字典中添加
_providers['your_provider'] = YourProviderOCR
_configs['your_provider'] = YourProviderConfig
```

### 运行测试

```bash
# 运行基本示例
PYTHONPATH=. python examples/basic_usage.py

# 测试OCR功能（需要API密钥）
PYTHONPATH=. python file_server_core/ocr/example_new_architecture.py
```

### 打包发布

```bash
# 构建包
python setup.py sdist bdist_wheel

# 安装本地包
pip install -e .

# 发布到PyPI（需要配置凭证）
twine upload dist/*
```

## 配置参考

### config.yaml 结构
```yaml
api:
  # API相关配置

server_components:
  minio:
    host: localhost
    port: 9000
    access_key: your_access_key
    secret_key: your_secret_key
    bucket_name: file-server
    use_public_url: false
    public_url_prefix: ""
  
  pg_vector:
    host: localhost
    port: 5432
    database: file_server
    user: postgres
    password: password

# 其他配置...
```

### 环境变量
```bash
# OCR相关
MISTRAL_API_KEY=your_mistral_api_key
MISTRAL_OCR_MODEL=mistral-ocr-latest

# 数据库相关（可选，覆盖config.yaml）
PG_HOST=localhost
PG_PORT=5432
MINIO_ENDPOINT=localhost:9000
```

## 故障排除

### 常见问题

1. **OCR模块导入失败**
   ```bash
   # 安装缺失依赖
   pip install mistralai python-dotenv
   ```

2. **配置文件找不到**
   ```bash
   # 确保配置文件存在
   ls config/config.yaml
   ```

3. **API密钥问题**
   ```bash
   # 检查环境变量
   echo $MISTRAL_API_KEY
   ```

4. **权限问题**
   ```bash
   # 检查目录权限
   chmod 755 logs/ tmp/
   ```

### 调试模式

```python
from loguru import logger

# 启用调试日志
logger.add("debug.log", level="DEBUG")
```

## 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打开 Pull Request

## 许可证

MIT License - 详见 LICENSE 文件

---

# 附录：详细功能设计文档

本部分包含从旧 `documents` 目录迁移过来的详细功能设计文档，为核心开发人员提供参考。

## 文件删除模块 (`delete_file_module`)

### 概述

`delete_file_module.py` 提供了完整的文件删除功能，包括从向量数据库和MinIO对象存储中删除文件及其相关数据。该模块包含两个主要函数：

1. `delete_file_from_vcdb` - 从向量数据库删除文件数据
2. `delete_file_from_minio` - 从MinIO对象存储删除文件

### 数据存储架构
```
┌─────────────────┐    ┌─────────────────┐
│   向量数据库     │    │   MinIO存储     │
│   (PostgreSQL)  │    │   (对象存储)    │
└─────────────────┘    └─────────────────┘
         │                       │
         │                       │
    ┌────▼────┐              ┌───▼───┐
    │ 元数据   │              │ 文件  │
    │ 文本块   │              │ 图片  │
    │ 向量     │              │ 文档  │
    └─────────┘              └───────┘
```

### 删除流程
```
用户请求删除文件
        │
        ▼
┌───────────────┐
│ 参数验证      │
│ 权限检查      │
└───────┬───────┘
        │
        ▼
┌───────────────┐    ┌───────────────┐
│ 删除数据库数据 │    │ 删除MinIO文件 │
│ (vcdb)        │    │ (minio)       │
└───────────────┘    └───────────────┘
        │                    │
        ▼                    ▼
┌───────────────┐    ┌───────────────┐
│ 触发器级联删除 │    │ 递归删除目录  │
│ 更新索引数组  │    │ 清理相关文件  │
└───────────────┘    └───────────────┘
```

---

## 函数 `delete_file_from_vcdb` 设计

### 概述

`delete_file_from_vcdb` 函数用于从向量数据库中删除文件及其所有相关数据。该函数基于对数据库建表逻辑和触发器机制的深入理解，采用最优的删除策略。

### 数据库架构理解

#### 层次结构

```
Users (用户)
  ↓ 1:N
Knowledge Bases (知识库)  
  ↓ 1:N
Documents (文档)
  ↓ 1:N  
Components (组件)
  ↓ 1:1
Chunks/Photos (文本块/图片)
```

#### 触发器机制理解

- **级联删除 (ON DELETE CASCADE)**: 当删除 `documents` 表中的记录时，PostgreSQL会自动删除所有 `components`, `chunks`, `photos` 表中 `document_id` 匹配的记录。
- **触发器自动更新**: `document_after_trigger` 会从 `knowledge_bases.document_ids` 数组中移除被删除的 `document_id`。

### 删除策略

**核心原则：只删除 `documents` 表记录，让触发器处理其余工作。**

```sql
DELETE FROM chunk_schema.documents 
WHERE id = $1 AND knowledge_base_id = $2
```

### 优势分析

- **数据一致性**: 利用数据库级别的约束和触发器。
- **代码简洁性**: 只需一条 `DELETE` 语句。
- **性能优化**: 数据库级别的批量操作比应用层循环删除更高效。

---

## 函数 `save_text_to_vcdb_text_table` 设计

### 概述

`save_text_to_vcdb_text_table` 是一个基础函数，用于将文本段保存到 `chunk_schema.chunks` 表中。该函数遵循数据库架构设计，通过触发器自动同步到 `chunk_schema.components` 表，并处理所有相关的数据更新。

### 核心表与触发器

- **核心表**: `chunk_schema.chunks`
- **触发器自动同步到**: `chunk_schema.components`

### 功能特性

- **自动触发器集成**: 插入数据后，触发器会自动处理位置唯一性、全文搜索索引、文档内容更新等。
- **数据验证**: 验证文本内容、必需参数、组件类型和权限。
- **错误处理**: 详细的异常分类 (`ValueError`, `Exception`)。

---

## 函数 `find_all_text_and_image_index` 设计

### 函数概述

`find_all_text_and_image_index` 函数用于解析 Markdown 文本，找到其中所有图片和文本片段的索引位置。

### 函数签名

```python
def find_all_text_and_image_index(text: str) -> list:
```

### 返回值

返回一个元组列表 `(开始索引, 结束索引, 类型)`，其中类型为 `"image"` 或 `"text"`。

### 算法思路

1. **识别图片**: 使用正则表达式 `r'!\[([^\]]*)\]\(([^)]+)\)'` 找到所有 Markdown 图片。
2. **排序图片位置**: 按开始位置对图片进行排序。
3. **填充文本片段**: 遍历图片位置，在图片之间和前后填充文本片段。
4. **完整性保证**: 确保所有字符都被包含在某个片段中。

### 应用场景

- 文档解析与分解
- 内容分析与统计
- 格式转换
- 向量化处理

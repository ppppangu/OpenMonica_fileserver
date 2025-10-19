"""
文档实例类，提供便捷的文档操作方法
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum
from datetime import datetime
from .client import FileServerClient


class DocumentStatus(Enum):
    """文档状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Document:
    """文档模型"""
    id: str
    filename: str
    user_id: str
    knowledge_base_id: str
    file_url: str
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    file_size: Optional[int] = None
    content_type: Optional[str] = None
    markdown_url: Optional[str] = None
    pdf_url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

class Document:
    """文档实例类，提供便捷的文档操作方法"""
    
    def __init__(self, client: FileServerClient, document_id: str):
        """
        通过文档ID初始化文档实例
        
        Args:
            client: 客户端实例
            document_id: 文档ID
        """
        self.client = client
        self.document_id = document_id
        self._document = None
    
    async def get_content(self) -> str:
        """获取文档内容"""
        if not self._document:
            self._document = await self.client.get_document_by_id(self.document_id)
        
        if self._document and self._document.markdown_url:
            # 实际实现中会通过HTTP请求获取markdown内容
            return f"# {self._document.filename}\n\n这是文档的markdown内容..."
        return "文档内容获取失败"
    
    async def get_document_info(self):
        """获取文档详细信息"""
        if not self._document:
            self._document = await self.client.get_document_by_id(self.document_id)
        return self._document
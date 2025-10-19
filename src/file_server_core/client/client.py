"""
统一的文件服务器客户端

支持云端API和本地部署两种模式, 通过base_url参数区分
"""

import time
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models.knowledge_base import KnowledgeBase
from ..models.document import Document, DocumentStatus


class FileClient:
    """统一文件客户端"""
    
    def __init__(self, api_key: str, base_url: Optional[str]):
        """
        初始化客户端
        
        Args:
            api_key: API密钥
            base_url: 服务器所在地址
        """
        self.api_key = api_key
        self.base_url = base_url or "https://api.fileserver.com"
    
    async def _api_call(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """统一的API调用方法"""
        url = f"{self.base_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        # 实际HTTP请求实现
        print(f"[API] {method} {url}")
        
        # 模拟API响应
        return {"status": "success"}
    
    async def create_knowledge_base(self, name: str, description: Optional[str] = None) -> KnowledgeBase:
        """创建知识库"""
        await self._api_call("POST", "/api/v1/knowledge-bases", 
                            json={"name": name, "description": description})
        
        kb_id = f"kb_{int(time.time())}"
        return KnowledgeBase(
            id=kb_id,
            name=name,
            user_id="current_user",
            description=description,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            document_count=0
        )

    def create_knowledge_base_sync(self, name: str, description: Optional[str] = None) -> KnowledgeBase:
        """创建知识库 (同步版本)"""
        pass

    async def list_knowledge_bases(self) -> List[KnowledgeBase]:
        """获取知识库列表"""
        await self._api_call("GET", "/api/v1/knowledge-bases")
        
        return [
            KnowledgeBase(
                id="kb_123",
                name="示例知识库",
                user_id="current_user",
                document_count=2,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]

    def list_knowledge_bases_sync(self) -> List[KnowledgeBase]:
        """获取知识库列表 (同步版本)"""
        pass

    async def delete_knowledge_base(self, kb_id: str) -> bool:
        """删除知识库"""
        # await self._api_call("DELETE", f"/api/v1/knowledge-bases/{kb_id}")
        print(f"知识库 {kb_id} 已标记为删除（示例中已注释）")
        return True

    def delete_knowledge_base_sync(self, kb_id: str) -> bool:
        """删除知识库 (同步版本)"""
        pass

    async def upload_document(self, knowledge_base: KnowledgeBase, file_path: str) -> Document:
        """上传文档到知识库"""
        import os
        filename = os.path.basename(file_path)
        
        doc_id = f"doc_{int(time.time())}"
        return Document(
            id=doc_id,
            filename=filename,
            user_id="current_user",
            knowledge_base_id=knowledge_base.id,
            file_url=f"{self.base_url}/files/{doc_id}",
            status=DocumentStatus.PROCESSING,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            file_size=1024 * 50
        )

    def upload_document_sync(self, knowledge_base: KnowledgeBase, file_path: str) -> Document:
        """上传文档到知识库 (同步版本)"""
        pass

    async def get_document(self, doc_id: str) -> Optional[Document]:
        """根据文档ID获取文档信息"""
        await self._api_call("GET", f"/api/v1/documents/{doc_id}")
        
        return Document(
            id=doc_id,
            filename="示例文档.pdf",
            user_id="current_user",
            knowledge_base_id="kb_123",
            file_url=f"{self.base_url}/files/{doc_id}",
            status=DocumentStatus.COMPLETED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            markdown_url=f"{self.base_url}/files/{doc_id}/markdown"
        )

    def get_document_sync(self, doc_id: str) -> Optional[Document]:
        """根据文档ID获取文档信息 (同步版本)"""
        pass

    async def list_documents(self, knowledge_base_id: str) -> List[Document]:
        """获取知识库中的文档列表"""
        await self._api_call("GET", f"/api/v1/knowledge-bases/{knowledge_base_id}/documents")
        
        return [
            Document(
                id="doc_001",
                filename="文档1.pdf",
                user_id="current_user",
                knowledge_base_id=knowledge_base_id,
                file_url=f"{self.base_url}/files/doc_001",
                status=DocumentStatus.COMPLETED,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
        ]

    def list_documents_sync(self, knowledge_base_id: str) -> List[Document]:
        """获取知识库中的文档列表 (同步版本)"""
        pass
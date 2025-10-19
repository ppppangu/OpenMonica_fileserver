"""
文件服务器 - 主要服务类，整合所有组件
"""

import asyncio
from typing import Dict, Any, Optional, List
from pathlib import Path

from loguru import logger

from .database import PostgreSQLManager
from .storage import MinIOManager
from .file_manager import FileManager
from ..ocr import OCRProcessor
from ..utils.config_utils import load_config


class FileServer:
    """文件服务器主类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化文件服务器
        
        Args:
            config_path: 配置文件路径
        """
        self.config = self._load_config(config_path)
        
        # 初始化组件
        self.db_manager = PostgreSQLManager(self.config.get("database", {}))
        self.storage_manager = MinIOManager(self.config.get("storage", {}))
        self.ocr_processor = OCRProcessor(self.config.get("ocr", {}))
        
        # 文件管理器（整合所有组件）
        self.file_manager = FileManager(
            self.db_manager,
            self.storage_manager,
            self.ocr_processor
        )
        
        self._initialized = False
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """加载配置文件"""
        if config_path:
            return load_config(config_path)
        
        # 默认配置
        return {
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "file_server",
                "user": "postgres",
                "password": "",
                "min_pool_size": 5,
                "max_pool_size": 20
            },
            "storage": {
                "endpoint": "localhost:9000",
                "access_key": "",
                "secret_key": "",
                "bucket_name": "file-server",
                "secure": False
            },
            "ocr": {
                "provider": "mistral",
                "model_name": "mistral-large-latest",
                "api_key": "",
                "max_retries": 3,
                "timeout": 30
            }
        }
    
    async def initialize(self) -> None:
        """初始化服务器"""
        if self._initialized:
            logger.warning("文件服务器已经初始化")
            return
        
        try:
            logger.info("正在初始化文件服务器...")
            
            # 初始化文件管理器（会自动初始化所有子组件）
            await self.file_manager.initialize()
            
            self._initialized = True
            logger.info("文件服务器初始化完成")
            
        except Exception as e:
            logger.error(f"文件服务器初始化失败: {e}")
            raise
    
    async def close(self) -> None:
        """关闭服务器"""
        if not self._initialized:
            return
        
        try:
            logger.info("正在关闭文件服务器...")
            await self.file_manager.close()
            self._initialized = False
            logger.info("文件服务器已关闭")
            
        except Exception as e:
            logger.error(f"关闭文件服务器时出错: {e}")
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()
    
    def _check_initialized(self) -> None:
        """检查是否已初始化"""
        if not self._initialized:
            raise RuntimeError("文件服务器未初始化，请先调用 initialize() 方法")
    
    # 用户管理方法
    async def create_user(self, user_id: str, username: str, email: Optional[str] = None) -> bool:
        """创建用户"""
        self._check_initialized()
        return await self.db_manager.create_user(user_id, username, email)
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        self._check_initialized()
        return await self.db_manager.get_user(user_id)
    
    # 知识库管理方法
    async def create_knowledge_base(
        self,
        name: str,
        description: str,
        user_id: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """创建知识库"""
        self._check_initialized()
        return await self.file_manager.create_knowledge_base(name, description, user_id, settings)
    
    async def get_knowledge_bases(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的知识库列表"""
        self._check_initialized()
        return await self.file_manager.get_knowledge_bases(user_id)
    
    # 文件管理方法
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        user_id: str,
        knowledge_base_id: str,
        enable_ocr: bool = True
    ) -> Dict[str, Any]:
        """上传文件"""
        self._check_initialized()
        return await self.file_manager.upload_file(
            file_data, filename, user_id, knowledge_base_id, enable_ocr
        )
    
    async def get_documents(
        self,
        user_id: str,
        knowledge_base_id: Optional[str] = None,
        include_content: bool = False
    ) -> List[Dict[str, Any]]:
        """获取文档列表"""
        self._check_initialized()
        return await self.file_manager.get_documents(user_id, knowledge_base_id, include_content)
    
    async def get_document(self, document_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取单个文档信息"""
        self._check_initialized()
        return await self.file_manager.get_document(document_id, user_id)
    
    async def download_file(self, document_id: str, user_id: str):
        """下载文件"""
        self._check_initialized()
        return await self.file_manager.download_file(document_id, user_id)
    
    async def delete_file(self, document_id: str, user_id: str) -> bool:
        """删除文件"""
        self._check_initialized()
        return await self.file_manager.delete_file(document_id, user_id)
    
    async def get_ocr_result(self, document_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取OCR结果"""
        self._check_initialized()
        return await self.file_manager.get_ocr_result(document_id, user_id)
    
    # 系统健康检查
    async def health_check(self) -> Dict[str, Any]:
        """系统健康检查"""
        self._check_initialized()
        
        result = {
            "status": "ok",
            "timestamp": asyncio.get_event_loop().time(),
            "components": {}
        }
        
        try:
            # 检查数据库连接
            user_count = len(await self.db_manager.get_connection().__anext__())
            result["components"]["database"] = {
                "status": "ok",
                "connection_pool": "active"
            }
        except Exception as e:
            result["components"]["database"] = {
                "status": "error",
                "error": str(e)
            }
            result["status"] = "degraded"
        
        try:
            # 检查存储连接
            await self.storage_manager.list_files("health_check")
            result["components"]["storage"] = {
                "status": "ok",
                "bucket": self.storage_manager.bucket_name
            }
        except Exception as e:
            result["components"]["storage"] = {
                "status": "error", 
                "error": str(e)
            }
            result["status"] = "degraded"
        
        # OCR组件状态
        result["components"]["ocr"] = {
            "status": "ok",
            "provider": self.config.get("ocr", {}).get("provider", "unknown")
        }
        
        return result
    
    # 统计信息
    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """获取用户统计信息"""
        self._check_initialized()
        
        try:
            # 获取知识库数量
            knowledge_bases = await self.get_knowledge_bases(user_id)
            kb_count = len(knowledge_bases)
            
            # 获取文档数量和总大小
            documents = await self.get_documents(user_id)
            doc_count = len(documents)
            total_size = sum(doc.get("file_size", 0) for doc in documents)
            
            # 统计文件类型
            mime_types = {}
            ocr_stats = {"pending": 0, "processing": 0, "completed": 0, "failed": 0}
            
            for doc in documents:
                mime_type = doc.get("mime_type", "unknown")
                mime_types[mime_type] = mime_types.get(mime_type, 0) + 1
                
                ocr_status = doc.get("ocr_status", "unknown")
                if ocr_status in ocr_stats:
                    ocr_stats[ocr_status] += 1
            
            return {
                "user_id": user_id,
                "knowledge_bases": kb_count,
                "documents": doc_count,
                "total_size_bytes": total_size,
                "file_types": mime_types,
                "ocr_stats": ocr_stats
            }
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {
                "error": str(e)
            }
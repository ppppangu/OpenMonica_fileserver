"""
文件管理器 - 统一管理文件的存储、元数据和处理流程
"""

import asyncio
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

from loguru import logger

from .database import PostgreSQLManager
from .storage import MinIOManager
from ..ocr import OCRProcessor
from ..models.document import Document
from ..models.knowledge_base import KnowledgeBase


class FileManager:
    """文件管理器 - 整合数据库、对象存储和OCR处理"""
    
    def __init__(
        self,
        db_manager: PostgreSQLManager,
        storage_manager: MinIOManager,
        ocr_processor: OCRProcessor
    ):
        self.db = db_manager
        self.storage = storage_manager  
        self.ocr = ocr_processor
        
    async def initialize(self) -> None:
        """初始化所有组件"""
        await self.db.initialize()
        await self.storage.initialize()
        logger.info("文件管理器初始化完成")
    
    async def close(self) -> None:
        """关闭所有连接"""
        await self.db.close()
        logger.info("文件管理器已关闭")
    
    def _calculate_file_hash(self, file_data: bytes) -> str:
        """计算文件SHA256哈希值"""
        return hashlib.sha256(file_data).hexdigest()
    
    def _detect_mime_type(self, filename: str, file_data: bytes) -> str:
        """检测文件MIME类型"""
        import mimetypes
        
        mime_type, _ = mimetypes.guess_type(filename)
        if mime_type:
            return mime_type
            
        # 基于文件头检测
        if file_data.startswith(b'%PDF'):
            return 'application/pdf'
        elif file_data.startswith(b'\x89PNG'):
            return 'image/png'
        elif file_data.startswith(b'\xff\xd8\xff'):
            return 'image/jpeg'
        elif file_data.startswith(b'GIF8'):
            return 'image/gif'
        elif file_data.startswith(b'PK\x03\x04'):
            if filename.endswith(('.docx', '.xlsx', '.pptx')):
                if filename.endswith('.docx'):
                    return 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif filename.endswith('.xlsx'):
                    return 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                elif filename.endswith('.pptx'):
                    return 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
            return 'application/zip'
        
        return 'application/octet-stream'
    
    async def upload_file(
        self,
        file_data: bytes,
        filename: str,
        user_id: str,
        knowledge_base_id: str,
        enable_ocr: bool = True
    ) -> Dict[str, Any]:
        """
        上传文件并处理
        
        Args:
            file_data: 文件二进制数据
            filename: 原始文件名
            user_id: 用户ID
            knowledge_base_id: 知识库ID
            enable_ocr: 是否启用OCR处理
            
        Returns:
            包含上传结果的字典
        """
        try:
            # 计算文件哈希
            file_hash = self._calculate_file_hash(file_data)
            
            # 检查文件是否已存在
            existing_doc_id = await self.db.check_file_exists(file_hash, user_id)
            if existing_doc_id:
                logger.info(f"文件已存在，跳过上传: {filename}")
                return {
                    "success": True,
                    "document_id": existing_doc_id,
                    "message": "文件已存在，跳过上传",
                    "duplicate": True
                }
            
            # 检测MIME类型
            mime_type = self._detect_mime_type(filename, file_data)
            
            # 生成唯一文档ID
            import uuid
            document_id = str(uuid.uuid4())
            
            # 上传到对象存储
            storage_result = await self.storage.upload_file(
                file_data=file_data,
                user_id=user_id,
                knowledge_base_id=knowledge_base_id,
                filename=f"{document_id}_{filename}",
                content_type=mime_type
            )
            
            # 创建文档对象
            document = Document(
                id=document_id,
                filename=f"{document_id}_{filename}",
                original_filename=filename,
                file_size=len(file_data),
                mime_type=mime_type,
                file_hash=file_hash,
                knowledge_base_id=knowledge_base_id,
                user_id=user_id,
                storage_path=storage_result["object_path"],
                metadata={
                    "etag": storage_result["etag"],
                    "upload_time": datetime.now().isoformat()
                }
            )
            
            # 保存到数据库
            success = await self.db.create_document(document)
            if not success:
                # 如果数据库保存失败，删除已上传的文件
                await self.storage.delete_file(storage_result["object_path"])
                raise RuntimeError("文档元数据保存失败")
            
            logger.info(f"文件上传成功: {filename} -> {document_id}")
            
            # 异步启动OCR处理（如果启用）
            if enable_ocr and self._should_ocr(mime_type):
                asyncio.create_task(self._process_ocr(document_id, file_data))
            
            return {
                "success": True,
                "document_id": document_id,
                "filename": filename,
                "file_size": len(file_data),
                "mime_type": mime_type,
                "file_hash": file_hash,
                "storage_path": storage_result["object_path"],
                "duplicate": False
            }
            
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _should_ocr(self, mime_type: str) -> bool:
        """判断文件是否需要OCR处理"""
        ocr_types = [
            'application/pdf',
            'image/png',
            'image/jpeg',
            'image/gif',
            'image/bmp',
            'image/tiff'
        ]
        return mime_type in ocr_types
    
    async def _process_ocr(self, document_id: str, file_data: bytes) -> None:
        """异步处理OCR"""
        try:
            # 更新状态为处理中
            await self.db.update_document_ocr_status(document_id, "processing")
            
            # 执行OCR处理
            ocr_result = await self.ocr.process_document(file_data)
            
            # 更新处理结果
            await self.db.update_document_ocr_status(
                document_id, 
                "completed", 
                ocr_result
            )
            
            logger.info(f"OCR处理完成: {document_id}")
            
        except Exception as e:
            logger.error(f"OCR处理失败 {document_id}: {e}")
            await self.db.update_document_ocr_status(
                document_id,
                "failed",
                {"error": str(e)}
            )
    
    async def get_documents(
        self, 
        user_id: str, 
        knowledge_base_id: Optional[str] = None,
        include_content: bool = False
    ) -> List[Dict[str, Any]]:
        """
        获取用户的文档列表
        
        Args:
            user_id: 用户ID
            knowledge_base_id: 知识库ID（可选）
            include_content: 是否包含文件内容
            
        Returns:
            文档信息列表
        """
        try:
            documents = await self.db.get_documents(user_id, knowledge_base_id)
            
            if include_content:
                for doc in documents:
                    try:
                        # 生成访问URL
                        url = await self.storage.generate_presigned_url(doc["storage_path"])
                        doc["access_url"] = url
                    except Exception as e:
                        logger.warning(f"生成文档访问URL失败 {doc['id']}: {e}")
                        doc["access_url"] = None
            
            return documents
            
        except Exception as e:
            logger.error(f"获取文档列表失败: {e}")
            return []
    
    async def get_document(self, document_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取单个文档的详细信息"""
        try:
            documents = await self.db.get_documents(user_id)
            document = next((doc for doc in documents if doc["id"] == document_id), None)
            
            if document:
                # 生成访问URL
                url = await self.storage.generate_presigned_url(document["storage_path"])
                document["access_url"] = url
            
            return document
            
        except Exception as e:
            logger.error(f"获取文档信息失败: {e}")
            return None
    
    async def download_file(self, document_id: str, user_id: str) -> Optional[Tuple[bytes, str, str]]:
        """
        下载文件
        
        Returns:
            (文件数据, 文件名, MIME类型) 或 None
        """
        try:
            # 获取文档信息
            document = await self.get_document(document_id, user_id)
            if not document:
                return None
            
            # 从对象存储下载
            file_data = await self.storage.download_file(document["storage_path"])
            
            return (
                file_data,
                document["original_filename"], 
                document["mime_type"]
            )
            
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            return None
    
    async def delete_file(self, document_id: str, user_id: str) -> bool:
        """删除文件"""
        try:
            # 获取文档信息
            document = await self.get_document(document_id, user_id)
            if not document:
                logger.warning(f"文档不存在: {document_id}")
                return False
            
            # 从对象存储删除
            storage_success = await self.storage.delete_file(document["storage_path"])
            
            # 从数据库删除
            db_success = await self.db.delete_document(document_id, user_id)
            
            if db_success:
                logger.info(f"文件删除成功: {document_id}")
                return True
            else:
                logger.error(f"数据库删除失败: {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"文件删除失败: {e}")
            return False
    
    async def get_ocr_result(self, document_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """获取文档的OCR结果"""
        try:
            document = await self.get_document(document_id, user_id)
            if not document:
                return None
            
            return {
                "document_id": document_id,
                "ocr_status": document.get("ocr_status"),
                "ocr_result": document.get("ocr_result")
            }
            
        except Exception as e:
            logger.error(f"获取OCR结果失败: {e}")
            return None
    
    async def create_knowledge_base(
        self,
        name: str,
        description: str,
        user_id: str,
        settings: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """创建知识库"""
        try:
            import uuid
            kb_id = str(uuid.uuid4())
            
            kb = KnowledgeBase(
                id=kb_id,
                name=name,
                description=description,
                user_id=user_id,
                settings=settings or {}
            )
            
            success = await self.db.create_knowledge_base(kb)
            if success:
                logger.info(f"知识库创建成功: {name} -> {kb_id}")
                return kb_id
            else:
                return None
                
        except Exception as e:
            logger.error(f"创建知识库失败: {e}")
            return None
    
    async def get_knowledge_bases(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的知识库列表"""
        try:
            return await self.db.get_knowledge_bases(user_id)
        except Exception as e:
            logger.error(f"获取知识库列表失败: {e}")
            return []
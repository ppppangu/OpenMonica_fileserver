"""
MinIO对象存储管理器 - 处理文件的对象存储操作
"""

import asyncio
import hashlib
from typing import Dict, Any, List, Optional, BinaryIO
from datetime import datetime, timedelta
from pathlib import Path

from minio import Minio
from minio.error import S3Error
from loguru import logger
import aiofiles


class MinIOManager:
    """MinIO对象存储管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[Minio] = None
        self.bucket_name = config.get("bucket_name", "file-server")
        
    async def initialize(self) -> None:
        """初始化MinIO客户端"""
        try:
            self.client = Minio(
                endpoint=self.config.get("endpoint", "localhost:9000"),
                access_key=self.config.get("access_key", ""),
                secret_key=self.config.get("secret_key", ""),
                secure=self.config.get("secure", False)
            )
            
            # 创建bucket（如果不存在）
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
                logger.info(f"创建MinIO bucket: {self.bucket_name}")
            
            logger.info("MinIO客户端初始化成功")
            
        except Exception as e:
            logger.error(f"MinIO客户端初始化失败: {e}")
            raise
    
    def _generate_object_path(self, user_id: str, knowledge_base_id: str, filename: str) -> str:
        """生成对象存储路径"""
        timestamp = datetime.now().strftime("%Y%m%d")
        return f"users/{user_id}/kb/{knowledge_base_id}/{timestamp}/{filename}"
    
    def _calculate_file_hash(self, file_data: bytes) -> str:
        """计算文件SHA256哈希值"""
        return hashlib.sha256(file_data).hexdigest()
    
    async def upload_file(
        self, 
        file_data: bytes, 
        user_id: str, 
        knowledge_base_id: str, 
        filename: str,
        content_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        上传文件到MinIO
        
        Args:
            file_data: 文件二进制数据
            user_id: 用户ID
            knowledge_base_id: 知识库ID
            filename: 文件名
            content_type: MIME类型
            
        Returns:
            包含上传结果信息的字典
        """
        if not self.client:
            raise RuntimeError("MinIO客户端未初始化")
            
        try:
            # 生成对象路径
            object_path = self._generate_object_path(user_id, knowledge_base_id, filename)
            
            # 计算文件哈希
            file_hash = self._calculate_file_hash(file_data)
            
            # 准备元数据
            metadata = {
                "user_id": user_id,
                "knowledge_base_id": knowledge_base_id,
                "original_filename": filename,
                "file_hash": file_hash,
                "upload_time": datetime.now().isoformat()
            }
            
            # 上传文件
            from io import BytesIO
            result = self.client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_path,
                data=BytesIO(file_data),
                length=len(file_data),
                content_type=content_type,
                metadata=metadata
            )
            
            # 生成访问URL（预签名URL，有效期24小时）
            url = self.client.presigned_get_object(
                bucket_name=self.bucket_name,
                object_name=object_path,
                expires=timedelta(hours=24)
            )
            
            logger.info(f"文件上传成功: {object_path}")
            
            return {
                "object_path": object_path,
                "file_hash": file_hash,
                "file_size": len(file_data),
                "url": url,
                "etag": result.etag
            }
            
        except S3Error as e:
            logger.error(f"MinIO上传失败: {e}")
            raise
        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            raise
    
    async def download_file(self, object_path: str) -> bytes:
        """
        从MinIO下载文件
        
        Args:
            object_path: 对象存储路径
            
        Returns:
            文件二进制数据
        """
        if not self.client:
            raise RuntimeError("MinIO客户端未初始化")
            
        try:
            response = self.client.get_object(self.bucket_name, object_path)
            data = response.read()
            response.close()
            response.release_conn()
            
            logger.info(f"文件下载成功: {object_path}")
            return data
            
        except S3Error as e:
            logger.error(f"MinIO下载失败: {e}")
            raise
        except Exception as e:
            logger.error(f"文件下载失败: {e}")
            raise
    
    async def delete_file(self, object_path: str) -> bool:
        """
        删除MinIO中的文件
        
        Args:
            object_path: 对象存储路径
            
        Returns:
            删除是否成功
        """
        if not self.client:
            raise RuntimeError("MinIO客户端未初始化")
            
        try:
            self.client.remove_object(self.bucket_name, object_path)
            logger.info(f"文件删除成功: {object_path}")
            return True
            
        except S3Error as e:
            logger.error(f"MinIO删除失败: {e}")
            return False
        except Exception as e:
            logger.error(f"文件删除失败: {e}")
            return False
    
    async def get_file_info(self, object_path: str) -> Optional[Dict[str, Any]]:
        """
        获取文件信息
        
        Args:
            object_path: 对象存储路径
            
        Returns:
            文件信息字典
        """
        if not self.client:
            raise RuntimeError("MinIO客户端未初始化")
            
        try:
            stat = self.client.stat_object(self.bucket_name, object_path)
            
            return {
                "object_name": stat.object_name,
                "size": stat.size,
                "etag": stat.etag,
                "last_modified": stat.last_modified,
                "content_type": stat.content_type,
                "metadata": stat.metadata
            }
            
        except S3Error as e:
            logger.error(f"获取文件信息失败: {e}")
            return None
        except Exception as e:
            logger.error(f"获取文件信息失败: {e}")
            return None
    
    async def list_files(self, user_id: str, knowledge_base_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出用户的文件
        
        Args:
            user_id: 用户ID
            knowledge_base_id: 知识库ID（可选）
            
        Returns:
            文件信息列表
        """
        if not self.client:
            raise RuntimeError("MinIO客户端未初始化")
            
        try:
            if knowledge_base_id:
                prefix = f"users/{user_id}/kb/{knowledge_base_id}/"
            else:
                prefix = f"users/{user_id}/"
            
            objects = self.client.list_objects(
                bucket_name=self.bucket_name,
                prefix=prefix,
                recursive=True
            )
            
            files = []
            for obj in objects:
                files.append({
                    "object_name": obj.object_name,
                    "size": obj.size,
                    "etag": obj.etag,
                    "last_modified": obj.last_modified,
                    "is_dir": obj.is_dir
                })
            
            return files
            
        except S3Error as e:
            logger.error(f"列出文件失败: {e}")
            return []
        except Exception as e:
            logger.error(f"列出文件失败: {e}")
            return []
    
    async def generate_presigned_url(
        self, 
        object_path: str, 
        expires: timedelta = timedelta(hours=1),
        method: str = "GET"
    ) -> str:
        """
        生成预签名URL
        
        Args:
            object_path: 对象存储路径
            expires: 过期时间
            method: HTTP方法
            
        Returns:
            预签名URL
        """
        if not self.client:
            raise RuntimeError("MinIO客户端未初始化")
            
        try:
            if method.upper() == "GET":
                url = self.client.presigned_get_object(
                    bucket_name=self.bucket_name,
                    object_name=object_path,
                    expires=expires
                )
            elif method.upper() == "PUT":
                url = self.client.presigned_put_object(
                    bucket_name=self.bucket_name,
                    object_name=object_path,
                    expires=expires
                )
            else:
                raise ValueError(f"不支持的HTTP方法: {method}")
            
            return url
            
        except S3Error as e:
            logger.error(f"生成预签名URL失败: {e}")
            raise
        except Exception as e:
            logger.error(f"生成预签名URL失败: {e}")
            raise
    
    async def copy_file(self, source_path: str, dest_path: str) -> bool:
        """
        复制文件
        
        Args:
            source_path: 源文件路径
            dest_path: 目标文件路径
            
        Returns:
            复制是否成功
        """
        if not self.client:
            raise RuntimeError("MinIO客户端未初始化")
            
        try:
            from minio.commonconfig import CopySource
            
            self.client.copy_object(
                bucket_name=self.bucket_name,
                object_name=dest_path,
                source=CopySource(bucket_name=self.bucket_name, object_name=source_path)
            )
            
            logger.info(f"文件复制成功: {source_path} -> {dest_path}")
            return True
            
        except S3Error as e:
            logger.error(f"文件复制失败: {e}")
            return False
        except Exception as e:
            logger.error(f"文件复制失败: {e}")
            return False
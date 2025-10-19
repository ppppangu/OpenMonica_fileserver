"""
PostgreSQL数据库管理器 - 处理文档元数据和关系数据存储
"""

import asyncio
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from contextlib import asynccontextmanager

import asyncpg
from loguru import logger

from ..models.document import Document
from ..models.knowledge_base import KnowledgeBase


class PostgreSQLManager:
    """PostgreSQL数据库管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.pool: Optional[asyncpg.Pool] = None
        
    async def initialize(self) -> None:
        """初始化数据库连接池"""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.config.get("host", "localhost"),
                port=self.config.get("port", 5432),
                database=self.config.get("database", "file_server"),
                user=self.config.get("user", "postgres"),
                password=self.config.get("password", ""),
                min_size=self.config.get("min_pool_size", 5),
                max_size=self.config.get("max_pool_size", 20),
                command_timeout=self.config.get("command_timeout", 30),
                server_settings={
                    "jit": "off"
                }
            )
            await self._create_tables()
            logger.info("PostgreSQL连接池初始化成功")
        except Exception as e:
            logger.error(f"PostgreSQL连接池初始化失败: {e}")
            raise
    
    async def close(self) -> None:
        """关闭数据库连接池"""
        if self.pool:
            await self.pool.close()
            logger.info("PostgreSQL连接池已关闭")
    
    @asynccontextmanager
    async def get_connection(self):
        """获取数据库连接"""
        if not self.pool:
            raise RuntimeError("数据库连接池未初始化")
        
        async with self.pool.acquire() as connection:
            yield connection
    
    async def _create_tables(self) -> None:
        """创建必要的数据表"""
        async with self.get_connection() as conn:
            # 用户表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR(50) PRIMARY KEY,
                    username VARCHAR(100) UNIQUE NOT NULL,
                    email VARCHAR(200),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 知识库表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_bases (
                    id VARCHAR(50) PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    description TEXT,
                    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
                    settings JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 文档表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    id VARCHAR(50) PRIMARY KEY,
                    filename VARCHAR(500) NOT NULL,
                    original_filename VARCHAR(500) NOT NULL,
                    file_size BIGINT NOT NULL,
                    mime_type VARCHAR(100),
                    file_hash VARCHAR(64),
                    knowledge_base_id VARCHAR(50) REFERENCES knowledge_bases(id) ON DELETE CASCADE,
                    user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE,
                    storage_path TEXT,
                    ocr_status VARCHAR(20) DEFAULT 'pending',
                    ocr_result JSONB,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 文档处理状态表
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS document_processing (
                    id SERIAL PRIMARY KEY,
                    document_id VARCHAR(50) REFERENCES documents(id) ON DELETE CASCADE,
                    processing_type VARCHAR(50) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    result JSONB,
                    error_message TEXT,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)
            
            # 创建索引
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_user_id ON documents(user_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_kb_id ON documents(knowledge_base_id)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_hash ON documents(file_hash)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_processing_document_id ON document_processing(document_id)")
            
            logger.info("数据表创建/更新完成")
    
    async def create_user(self, user_id: str, username: str, email: Optional[str] = None) -> bool:
        """创建用户"""
        try:
            async with self.get_connection() as conn:
                await conn.execute(
                    "INSERT INTO users (id, username, email) VALUES ($1, $2, $3)",
                    user_id, username, email
                )
                return True
        except asyncpg.UniqueViolationError:
            logger.warning(f"用户 {username} 已存在")
            return False
        except Exception as e:
            logger.error(f"创建用户失败: {e}")
            return False
    
    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """获取用户信息"""
        try:
            async with self.get_connection() as conn:
                row = await conn.fetchrow("SELECT * FROM users WHERE id = $1", user_id)
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取用户信息失败: {e}")
            return None
    
    async def create_knowledge_base(self, kb_data: KnowledgeBase) -> bool:
        """创建知识库"""
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO knowledge_bases (id, name, description, user_id, settings) 
                    VALUES ($1, $2, $3, $4, $5)
                """, kb_data.id, kb_data.name, kb_data.description, kb_data.user_id, kb_data.settings)
                return True
        except Exception as e:
            logger.error(f"创建知识库失败: {e}")
            return False
    
    async def get_knowledge_bases(self, user_id: str) -> List[Dict[str, Any]]:
        """获取用户的知识库列表"""
        try:
            async with self.get_connection() as conn:
                rows = await conn.fetch(
                    "SELECT * FROM knowledge_bases WHERE user_id = $1 ORDER BY created_at DESC",
                    user_id
                )
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取知识库列表失败: {e}")
            return []
    
    async def create_document(self, doc_data: Document) -> bool:
        """创建文档记录"""
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    INSERT INTO documents (
                        id, filename, original_filename, file_size, mime_type, 
                        file_hash, knowledge_base_id, user_id, storage_path, metadata
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                """, 
                    doc_data.id, doc_data.filename, doc_data.original_filename,
                    doc_data.file_size, doc_data.mime_type, doc_data.file_hash,
                    doc_data.knowledge_base_id, doc_data.user_id, doc_data.storage_path,
                    doc_data.metadata
                )
                return True
        except Exception as e:
            logger.error(f"创建文档记录失败: {e}")
            return False
    
    async def get_documents(self, user_id: str, knowledge_base_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取文档列表"""
        try:
            async with self.get_connection() as conn:
                if knowledge_base_id:
                    rows = await conn.fetch("""
                        SELECT * FROM documents 
                        WHERE user_id = $1 AND knowledge_base_id = $2 
                        ORDER BY created_at DESC
                    """, user_id, knowledge_base_id)
                else:
                    rows = await conn.fetch("""
                        SELECT * FROM documents 
                        WHERE user_id = $1 
                        ORDER BY created_at DESC
                    """, user_id)
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取文档列表失败: {e}")
            return []
    
    async def update_document_ocr_status(self, document_id: str, status: str, result: Optional[Dict] = None) -> bool:
        """更新文档OCR状态"""
        try:
            async with self.get_connection() as conn:
                await conn.execute("""
                    UPDATE documents 
                    SET ocr_status = $1, ocr_result = $2, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $3
                """, status, result, document_id)
                return True
        except Exception as e:
            logger.error(f"更新文档OCR状态失败: {e}")
            return False
    
    async def delete_document(self, document_id: str, user_id: str) -> bool:
        """删除文档"""
        try:
            async with self.get_connection() as conn:
                result = await conn.execute(
                    "DELETE FROM documents WHERE id = $1 AND user_id = $2",
                    document_id, user_id
                )
                return result.endswith("1")
        except Exception as e:
            logger.error(f"删除文档失败: {e}")
            return False
    
    async def check_file_exists(self, file_hash: str, user_id: str) -> Optional[str]:
        """检查文件是否已存在（基于哈希值）"""
        try:
            async with self.get_connection() as conn:
                row = await conn.fetchrow(
                    "SELECT id FROM documents WHERE file_hash = $1 AND user_id = $2",
                    file_hash, user_id
                )
                return row["id"] if row else None
        except Exception as e:
            logger.error(f"检查文件是否存在失败: {e}")
            return None
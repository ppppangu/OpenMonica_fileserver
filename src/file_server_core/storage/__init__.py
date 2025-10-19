"""
存储模块 - 对象存储和向量数据库

提供MinIO对象存储和向量数据库的统一接口
"""

from .manager import StorageManager

__all__ = ["StorageManager"]
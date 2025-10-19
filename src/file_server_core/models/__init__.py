"""
数据模型 - 核心数据结构定义

定义文档处理过程中使用的数据模型
"""

from .document import Document, DocumentStatus
from .knowledge_base import KnowledgeBase
from .processing import ProcessingRequest, ProcessingResult

__all__ = [
    "Document", 
    "DocumentStatus",
    "KnowledgeBase", 
    "ProcessingRequest", 
    "ProcessingResult"
]
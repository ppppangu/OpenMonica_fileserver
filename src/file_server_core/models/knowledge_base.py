"""
知识库相关数据模型
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass 
class KnowledgeBase:
    """知识库模型"""
    id: str
    name: str
    user_id: str
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    document_count: int = 0
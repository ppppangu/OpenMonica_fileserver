"""
用户相关数据模型
"""

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime


@dataclass 
class User:
    """用户模型"""
    id: str
    name: str
    user_id: str
    created_at: Optional[datetime] = None
    
    document_count: int = 0
    is_default: bool = False
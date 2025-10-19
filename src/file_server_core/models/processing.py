"""
处理请求和结果相关数据模型
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ProcessingMode(Enum):
    """处理模式"""
    SIMPLE = "simple"
    OCR = "ocr"


@dataclass
class ProcessingRequest:
    """处理请求模型"""
    file_url: str
    user_id: str
    knowledge_base_id: str
    mode: ProcessingMode = ProcessingMode.SIMPLE
    options: Optional[Dict[str, Any]] = None


@dataclass  
class ProcessingResult:
    """处理结果模型"""
    success: bool
    file_uuid: str
    markdown_url: Optional[str] = None
    pdf_url: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
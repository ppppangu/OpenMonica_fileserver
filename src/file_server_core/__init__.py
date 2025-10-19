"""
File Server Core - 文档处理核心库

提供文档处理、OCR识别、向量化存储等核心功能的Python库
"""

__version__ = "0.1.0"
__author__ = "File Server Team"

from .ocr import OCRProcessor
from .storage import StorageManager
from .models import *
from .server import FileServer, PostgreSQLManager, MinIOManager, FileManager

__all__ = [
    "OCRProcessor",
    "StorageManager",
    "FileServer",
    "PostgreSQLManager",
    "MinIOManager", 
    "FileManager",
]
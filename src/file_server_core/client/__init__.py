"""
File Server Client - 统一客户端模块

提供统一的客户端接口，支持云端和本地部署两种模式
"""

from .client import FileServerClient
from .document import DocumentInstance

__all__ = ["FileServerClient", "DocumentInstance"]
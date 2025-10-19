"""
文件处理工具函数
"""

from pathlib import Path
from typing import Dict, Optional, Tuple, List
import uuid
import io
from loguru import logger
from .config_utils import read_minio_config
from minio import Minio


# 支持的文件类型定义
DOCUMENT_FILE_TYPES = [
    ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", 
    ".odt", ".ods", ".odp", ".txt", ".rtf", ".jpg", 
    ".jpeg", ".png", ".tiff", ".tif", ".bmp", ".html", 
    ".htm", ".md", ".csv", ".tsv", ".xml"
]

PDF_FILE_TYPES = [".pdf"]

SUPPORTED_FILE_TYPES = DOCUMENT_FILE_TYPES + PDF_FILE_TYPES + [".py", ".ipynb", ".js", ".json"]


def validate_file_type(filename: str) -> bool:
    """验证文件类型是否受支持"""
    if not filename:
        return False
    file_type = Path(filename).suffix.lower()
    return file_type in SUPPORTED_FILE_TYPES


def validate_file_content(file_content: bytes, filename: str) -> Tuple[bool, str]:
    """验证文件内容"""
    if not filename:
        return False, "No filename provided"
    if not validate_file_type(filename):
        file_type = Path(filename).suffix.lower()
        return False, f"Unsupported file type: {file_type}"
    if len(file_content) == 0:
        return False, "Empty file provided"
    return True, ""


def detect_content_type(filename: str) -> str:
    """根据文件扩展名检测MIME类型"""
    suffix = Path(filename).suffix.lower()
    content_type_map = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".ppt": "application/vnd.ms-powerpoint",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".xls": "application/vnd.ms-excel",
        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ".txt": "text/plain",
        ".md": "text/markdown",
        ".html": "text/html",
        ".htm": "text/html",
        ".csv": "text/csv",
        ".json": "application/json",
        ".xml": "application/xml",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".tiff": "image/tiff",
        ".tif": "image/tiff",
        ".bmp": "image/bmp",
    }
    return content_type_map.get(suffix, "application/octet-stream")


def create_minio_client() -> Minio:
    """创建MinIO客户端"""
    minio_config = read_minio_config()
    return Minio(
        f"{minio_config['host']}:{int(minio_config['port'])}",
        access_key=minio_config["access_key"],
        secret_key=minio_config["secret_key"],
        secure=False
    )


def ensure_bucket_exists(minio_client: Minio, bucket_name: str) -> None:
    """确保桶存在，不存在则创建"""
    if not minio_client.bucket_exists(bucket_name):
        minio_client.make_bucket(bucket_name)
        logger.info(f"Created bucket: {bucket_name}")


def generate_object_path(user_id: str, filename: str, file_uuid: Optional[str] = None) -> Tuple[str, str]:
    """生成MinIO对象路径"""
    if not file_uuid:
        file_uuid = str(uuid.uuid4())
    object_path = f"{user_id}/default_file_space/{file_uuid}/{filename}"
    return object_path, file_uuid


def generate_public_url(bucket_name: str, object_path: str) -> str:
    """生成文件的公网URL"""
    minio_config = read_minio_config()
    if minio_config.get("use_public_url", False) and minio_config.get("public_url_prefix"):
        public_url = f"{minio_config['public_url_prefix']}/{bucket_name}/{object_path}"
    else:
        public_url = f"http://{minio_config['host']}:{minio_config['port']}/{bucket_name}/{object_path}"
    return public_url


def upload_file_to_minio(
    filename: str,
    file_content: bytes,
    content_type: Optional[str],
    user_id: str = "default",
    file_uuid: Optional[str] = None
) -> Dict[str, any]:
    """上传文件到MinIO存储"""
    try:
        if not filename:
            raise ValueError("No filename provided")

        file_size = len(file_content)

        is_valid, error_msg = validate_file_content(file_content, filename)
        if not is_valid:
            raise ValueError(error_msg)

        logger.info(f"File info - name: {filename}, size: {file_size} bytes")

        object_path, generated_uuid = generate_object_path(user_id, filename, file_uuid)

        minio_client = create_minio_client()
        minio_config = read_minio_config()
        bucket_name = minio_config["bucket_name"]

        ensure_bucket_exists(minio_client, bucket_name)

        # 如果未提供 content_type，则尝试检测
        if not content_type or content_type == "application/octet-stream":
            content_type = detect_content_type(filename)

        minio_client.put_object(
            bucket_name,
            object_path,
            io.BytesIO(file_content),
            length=file_size,
            content_type=content_type,
            part_size=10 * 1024 * 1024
        )

        logger.info(f"File uploaded successfully to MinIO: {object_path}")

        public_url = generate_public_url(bucket_name, object_path)
        logger.info(f"Generated public URL: {public_url}")

        return {
            "file_id": generated_uuid,
            "filename": filename,
            "object_path": object_path,
            "public_url": public_url,
            "file_size": file_size,
            "content_type": content_type
        }

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Error uploading file to MinIO: {str(e)}")
        raise IOError(f"Upload failed: {str(e)}")


def get_supported_file_types() -> Dict[str, List[str]]:
    """获取支持的文件类型"""
    return {
        "document_types": DOCUMENT_FILE_TYPES,
        "pdf_types": PDF_FILE_TYPES,
        "all_supported": SUPPORTED_FILE_TYPES
    }

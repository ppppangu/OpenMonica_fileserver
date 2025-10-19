# Web框架和异步生命周期依赖
import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# 使用兼容性适配器导入所有原有功能
# 注意：由于此文件已在 legacy 目录中，导入路径需要调整
from .compatibility_adapter import (
    delete_file_from_minio,
    delete_file_from_vcdb,
    get_documents_graph,
    produce_document_graph,
    mineru_process,
    read_config,
    DOCUMENT_FILE_TYPES,
    get_supported_file_types,
)
# 导入重构后的核心模块功能
from src.file_server_core.utils.file_utils import upload_file_to_minio

# 创建一个专门用于旧版 API 的路由器
router = APIRouter()

# 读取相关配置
config = read_config()


async def get_client_ip(request: Request):
    """从请求中提取客户端真实IP地址"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else None
    return client_ip


# 健康检查
@router.get("/health")
async def health():
    return {"status": "ok"}


# 获取支持的文件类型
@router.get("/get_supported_file_types")
async def get_supported_file_types_endpoint():
    file_types = get_supported_file_types()
    return {
        "status": "ok",
        "message": "Supported file types",
        "data": {"supported_file_types": file_types["all_supported"]},
    }


# 上传文件到云端
@router.post("/upload_minio")
async def upload_minio_endpoint(
    request: Request,
    upload_file: UploadFile = File(...),
    user_id: str = Form(default="default"),
):
    try:
        logger.info("--> enter upload_minio")
        client_ip = await get_client_ip(request)
        logger.info(
            f"Upload request received - user_id: {user_id} - client_ip: {client_ip}"
        )
        file_content = await upload_file.read()
        upload_result = upload_file_to_minio(
            filename=upload_file.filename,
            file_content=file_content,
            content_type=upload_file.content_type,
            user_id=user_id,
        )
        logger.info("File uploaded successfully via utils")
        return {
            "status": "success",
            "message": "File uploaded successfully",
            "data": upload_result,
        }
    except ValueError as e:
        logger.error(f"Validation error during file upload: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:
        logger.error(f"IO error during file upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Error uploading file to MinIO: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# ---------------------- 公共辅助函数 ----------------------

def _fix_public_url(original_url: str) -> str:
    """修正公共访问地址"""
    try:
        public_prefix = config["server_components"]["minio"].get("public_url_prefix")
        if not public_prefix or original_url.startswith(public_prefix):
            return original_url
        from urllib.parse import urlparse
        parsed = urlparse(original_url)
        fixed = f"{public_prefix}{parsed.path}"
        logger.info(f"_fix_public_url: 将 URL 从 {original_url} 修正为 {fixed}")
        return fixed
    except Exception as e:
        logger.warning(f"_fix_public_url 处理异常: {e}")
        return original_url


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
)
async def convert_document_to_pdf(file_url: str):
    """文档格式转换函数"""
    try:
        if not file_url or not isinstance(file_url, str):
            logger.error(f"无效的文件URL: {file_url}")
            return None
        file_extension = file_url.split(".")[-1].lower() if "." in file_url else ""
        if file_url.lower().endswith(".pdf"):
            return _fix_public_url(file_url)
        is_supported = any(file_url.lower().endswith(ext) for ext in DOCUMENT_FILE_TYPES)
        if not is_supported:
            logger.error(f"不支持的文件类型: {file_extension}")
            return None
        convert_url = config["server_components"]["convert_format_server"][0]["url"] + "/convert"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(convert_url, data={"file_url": file_url})
            response.raise_for_status()
            result = response.json()
            if "converted_url" not in result or not result["converted_url"]:
                logger.error(f"转换服务返回无效结果: {result}")
                return None
            converted_url = _fix_public_url(result["converted_url"])
            logger.info(f"文件转换成功: {file_url} -> {converted_url}")
            return converted_url
    except httpx.HTTPStatusError as e:
        logger.error(f"转换服务HTTP错误: {e.response.status_code} - {e.response.reason_phrase}")
        raise
    except httpx.RequestError as e:
        logger.error(f"转换服务请求错误: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"文件转换过程中发生未预期的错误: {str(e)}")
        return None


# 处理文件
@router.post("/process")
async def process(
    request: Request,
    user_id: str = Form(...),
    file_url: str = Form(...),
    knowledge_base_id: str = Form(default=None),
    mode: str = Form(default="simple"),
):
    """文档处理端点"""
    try:
        client_ip = await get_client_ip(request)
        logger.info(f"Process request received - user_id: {user_id} - client_ip: {client_ip} - file_url: {file_url} - knowledge_base_id: {knowledge_base_id} - mode: {mode}")
        if not file_url.startswith(("http://", "https://")):
            raise HTTPException(status_code=400, detail="Invalid file URL format")
        if not knowledge_base_id:
            knowledge_base_id = "df_" + user_id
        if not mode:
            mode = "simple"
        raw_file = file_url
        pdf_url = await convert_document_to_pdf(file_url)
        if not pdf_url:
            raise HTTPException(status_code=400, detail="Unsupported file type or conversion failed")
        if mode == "simple":
            return_url = await mineru_process(pdf_url, knowledge_base_id, mode, user_id, raw_file_url_to_return=raw_file)
            if not return_url:
                raise HTTPException(status_code=500, detail="File processing failed")
            return {"status": "ok", "message": "File processed successfully", "data": {"user_id": user_id, "knowledge_base_id": knowledge_base_id, "mode": mode, "file_url": raw_file, "markdown_public_url": return_url["markdown_public_url"], "pdf_file_public_url": return_url["pdf_file_public_url"], "file_uuid": return_url["file_uuid"]}}
        elif mode == "normal":
            return {"status": "ok", "message": "File processed successfully", "data": {"user_id": user_id, "file_url": pdf_url, "knowledge_base_id": knowledge_base_id, "mode": mode, "file_uuid": "", "markdown_public_url": "", "pdf_file_public_url": ""}}
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported mode: {mode}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"处理文件时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


# 删除文件
@router.post("/delete_file")
async def delete_file(
    request: Request,
    user_id: str = Form(...),
    file_id: str = Form(...),
    knowledge_base_id: str = Form(default=None),
):
    """文档删除端点"""
    client_ip = await get_client_ip(request)
    logger.info(f"Delete file request received - user_id: {user_id} - client_ip: {client_ip} - file_id: {file_id} - knowledge_base_id: {knowledge_base_id}")
    if not knowledge_base_id:
        knowledge_base_id = "df_" + user_id
    await delete_file_from_vcdb(user_id, file_id, knowledge_base_id)
    await delete_file_from_minio(user_id, file_id, knowledge_base_id)
    return {"status": "ok", "message": "File deleted successfully"}


@router.post("/graph/knowledge_base")
async def graph_knowledge_base(
    request: Request,
    user_id: str = Form(...),
    knowledge_base_id: str = Form(...),
    mode: str = Form(...),
    level: str = Form(...),
):
    """知识图谱管理端点"""
    client_ip = await get_client_ip(request)
    logger.info(f"Knowledge base request received - user_id: {user_id} - client_ip: {client_ip} - knowledge_base_id: {knowledge_base_id}")
    if level == "document":
        if mode == "produce":
            result = await produce_document_graph(user_id, knowledge_base_id)
            return {"status": "ok", "message": "Document graph produced successfully", "data": result}
        elif mode == "get":
            result = await get_documents_graph(user_id, knowledge_base_id)
            return {"status": "ok", "message": "Document graph fetched successfully", "data": result}
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported mode: {mode}")
    elif level == "subject":
        # Subject level logic to be implemented
        raise HTTPException(status_code=501, detail="Subject level not implemented")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported level: {level}")

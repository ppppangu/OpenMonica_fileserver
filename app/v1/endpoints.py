import httpx
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from loguru import logger
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

# Import legacy functionality through compatibility adapter
from app.legacy.compatibility_adapter import (
    delete_file_from_minio,
    delete_file_from_vcdb,
    get_documents_graph,
    produce_document_graph,
    mineru_process,
    read_config,
    DOCUMENT_FILE_TYPES,
    get_supported_file_types,
)

# Import core functionality
from src.file_server_core.utils.file_utils import upload_file_to_minio

router = APIRouter()
config = read_config()


async def get_client_ip(request: Request):
    """Extract client IP from request headers"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else None
    return client_ip


def _fix_public_url(original_url: str) -> str:
    """Fix public access URL"""
    try:
        public_prefix = config["server_components"]["minio"].get("public_url_prefix")
        if not public_prefix or original_url.startswith(public_prefix):
            return original_url
        from urllib.parse import urlparse
        parsed = urlparse(original_url)
        fixed = f"{public_prefix}{parsed.path}"
        logger.info(f"_fix_public_url: Fixed URL from {original_url} to {fixed}")
        return fixed
    except Exception as e:
        logger.warning(f"_fix_public_url error: {e}")
        return original_url


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.RequestError, httpx.HTTPStatusError)),
)
async def convert_document_to_pdf(file_url: str):
    """Convert document to PDF format"""
    try:
        if not file_url or not isinstance(file_url, str):
            logger.error(f"Invalid file URL: {file_url}")
            return None
        file_extension = file_url.split(".")[-1].lower() if "." in file_url else ""
        if file_url.lower().endswith(".pdf"):
            return _fix_public_url(file_url)
        is_supported = any(file_url.lower().endswith(ext) for ext in DOCUMENT_FILE_TYPES)
        if not is_supported:
            logger.error(f"Unsupported file type: {file_extension}")
            return None
        convert_url = config["server_components"]["convert_format_server"][0]["url"] + "/convert"
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(convert_url, data={"file_url": file_url})
            response.raise_for_status()
            result = response.json()
            if "converted_url" not in result or not result["converted_url"]:
                logger.error(f"Convert service returned invalid result: {result}")
                return None
            converted_url = _fix_public_url(result["converted_url"])
            logger.info(f"File converted successfully: {file_url} -> {converted_url}")
            return converted_url
    except httpx.HTTPStatusError as e:
        logger.error(f"Convert service HTTP error: {e.response.status_code} - {e.response.reason_phrase}")
        raise
    except httpx.RequestError as e:
        logger.error(f"Convert service request error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during file conversion: {str(e)}")
        return None


# Health check endpoint
@router.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "ok"}


# Get supported file types - RESTful: GET /v1/files/types
@router.get("/files/types")
async def get_supported_file_types_endpoint():
    """Get supported file types"""
    file_types = get_supported_file_types()
    return {
        "status": "success",
        "message": "Supported file types retrieved",
        "data": {"supported_file_types": file_types["all_supported"]},
    }


# Upload file - RESTful: POST /v1/files
@router.post("/files")
async def create_file(
    request: Request,
    file: UploadFile = File(...),
    user_id: str = Form(default="default"),
):
    """Upload a new file"""
    try:
        logger.info("--> Creating new file")
        client_ip = await get_client_ip(request)
        logger.info(f"File creation request - user_id: {user_id} - client_ip: {client_ip}")
        
        file_content = await file.read()
        upload_result = upload_file_to_minio(
            filename=file.filename,
            file_content=file_content,
            content_type=file.content_type,
            user_id=user_id,
        )
        logger.info("File uploaded successfully")
        
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
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


# Process file - RESTful: POST /v1/files/process
@router.post("/files/process")
async def process_file(
    request: Request,
    user_id: str = Form(...),
    file_url: str = Form(...),
    knowledge_base_id: str = Form(default=None),
    mode: str = Form(default="simple"),
):
    """Process a file for knowledge extraction"""
    try:
        client_ip = await get_client_ip(request)
        logger.info(f"File processing request - user_id: {user_id} - client_ip: {client_ip} - file_url: {file_url}")
        
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
            return {
                "status": "success",
                "message": "File processed successfully",
                "data": {
                    "user_id": user_id,
                    "knowledge_base_id": knowledge_base_id,
                    "mode": mode,
                    "file_url": raw_file,
                    "markdown_public_url": return_url["markdown_public_url"],
                    "pdf_file_public_url": return_url["pdf_file_public_url"],
                    "file_uuid": return_url["file_uuid"]
                }
            }
        elif mode == "normal":
            return {
                "status": "success",
                "message": "File processed successfully",
                "data": {
                    "user_id": user_id,
                    "file_url": pdf_url,
                    "knowledge_base_id": knowledge_base_id,
                    "mode": mode,
                    "file_uuid": "",
                    "markdown_public_url": "",
                    "pdf_file_public_url": ""
                }
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported mode: {mode}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


# Delete file - RESTful: DELETE /v1/files/{file_id}
@router.delete("/files/{file_id}")
async def delete_file(
    file_id: str,
    request: Request,
    user_id: str = Form(...),
    knowledge_base_id: str = Form(default=None),
):
    """Delete a file"""
    client_ip = await get_client_ip(request)
    logger.info(f"File deletion request - user_id: {user_id} - client_ip: {client_ip} - file_id: {file_id}")
    
    if not knowledge_base_id:
        knowledge_base_id = "df_" + user_id
        
    await delete_file_from_vcdb(user_id, file_id, knowledge_base_id)
    await delete_file_from_minio(user_id, file_id, knowledge_base_id)
    
    return {
        "status": "success",
        "message": "File deleted successfully"
    }


# Knowledge base graph management - RESTful: POST /v1/knowledge-bases/{kb_id}/graph
@router.post("/knowledge-bases/{knowledge_base_id}/graph")
async def manage_knowledge_base_graph(
    knowledge_base_id: str,
    request: Request,
    user_id: str = Form(...),
    mode: str = Form(...),
    level: str = Form(...),
):
    """Manage knowledge base graph"""
    client_ip = await get_client_ip(request)
    logger.info(f"Knowledge base graph request - user_id: {user_id} - client_ip: {client_ip} - kb_id: {knowledge_base_id}")
    
    if level == "document":
        if mode == "produce":
            result = await produce_document_graph(user_id, knowledge_base_id)
            return {
                "status": "success",
                "message": "Document graph produced successfully",
                "data": result
            }
        elif mode == "get":
            result = await get_documents_graph(user_id, knowledge_base_id)
            return {
                "status": "success",
                "message": "Document graph fetched successfully",
                "data": result
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported mode: {mode}")
    elif level == "subject":
        raise HTTPException(status_code=501, detail="Subject level not implemented")
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported level: {level}")
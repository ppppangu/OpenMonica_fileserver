"""
兼容性适配器 - 为main.py提供旧接口的兼容性

这个文件提供了所有原始模块的兼容接口，让main.py可以正常运行
"""

# 从新的模块结构导入功能
from file_server_core.utils.legacy_bridge import (
    read_config_legacy as read_config,
    read_pg_config,
    read_minio_config,
    mk_need_path,
    detect_content_type,
    convert_to_internal_minio_url
)

from file_server_core.utils.file_utils import (
    upload_file_to_minio,
    get_supported_file_types,
    DOCUMENT_FILE_TYPES,
    SUPPORTED_FILE_TYPES
)

from file_server_core.graph.manager import GraphManager

# 临时创建图谱管理器实例
_graph_manager = None


def _get_graph_manager():
    """获取图谱管理器实例"""
    global _graph_manager
    if _graph_manager is None:
        config = read_config()
        _graph_manager = GraphManager(config)
    return _graph_manager


# 兼容性函数 - 图谱相关
async def produce_document_graph(user_id: str, knowledge_base_id: str):
    """兼容性包装：生成文档图谱"""
    manager = _get_graph_manager()
    return await manager.produce_document_graph(user_id, knowledge_base_id)


async def get_documents_graph(user_id: str, knowledge_base_id: str):
    """兼容性包装：获取文档图谱"""
    manager = _get_graph_manager()
    return await manager.get_documents_graph(user_id, knowledge_base_id)


# 兼容性函数 - 文件删除相关（临时实现）
async def delete_file_from_minio(user_id: str, file_id: str, knowledge_base_id: str):
    """临时实现：从MinIO删除文件"""
    # TODO: 实现真正的删除逻辑
    from loguru import logger
    logger.info(f"删除MinIO文件: user_id={user_id}, file_id={file_id}, kb_id={knowledge_base_id}")
    

async def delete_file_from_vcdb(user_id: str, file_id: str, knowledge_base_id: str):
    """临时实现：从向量数据库删除文件"""
    # TODO: 实现真正的删除逻辑
    from loguru import logger
    logger.info(f"删除向量数据库文件: user_id={user_id}, file_id={file_id}, kb_id={knowledge_base_id}")


# OCR处理相关（临时实现）
async def mineru_process(
    file_url: str,
    knowledge_base_id: str,
    mode: str,
    user_id: str,
    raw_file_url_to_return: str = None
):
    """临时实现：MinErU文档处理"""
    # TODO: 使用新的OCR系统
    from loguru import logger
    import uuid
    
    logger.info(f"处理文档: {file_url}, mode: {mode}")
    
    # 临时返回值
    file_uuid = str(uuid.uuid4())
    return {
        "markdown_public_url": f"http://example.com/markdown/{file_uuid}.md",
        "pdf_file_public_url": raw_file_url_to_return or file_url,
        "file_uuid": file_uuid
    }


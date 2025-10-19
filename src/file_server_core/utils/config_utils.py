"""
配置管理工具函数
"""

import yaml
from pathlib import Path
from typing import Dict, Any


def read_config() -> Dict[str, Any]:
    """读取主配置文件"""
    config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return config


def read_pg_config() -> Dict[str, Any]:
    """读取PostgreSQL配置"""
    config = read_config()
    pg_config = config["server_components"]["pg"]
    return pg_config


def read_minio_config() -> Dict[str, Any]:
    """读取MinIO配置"""
    config = read_config()
    minio_config = config["server_components"]["minio"]
    return minio_config


def mk_logs_path() -> None:
    """创建日志目录"""
    log_path = Path(__file__).parent.parent.parent / "logs"
    log_path.mkdir(mode=0o777, exist_ok=True)


def mk_temp_path() -> None:
    """创建临时目录"""
    temp_path = Path(__file__).parent.parent.parent / "tmp"
    temp_path.mkdir(mode=0o777, exist_ok=True)


def mk_need_path() -> None:
    """创建必要目录"""
    mk_logs_path()
    mk_temp_path()
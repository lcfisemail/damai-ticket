"""TOML 配置加载与保存"""
import tomllib
from pathlib import Path
from typing import Any

import tomli_w
from loguru import logger


def load_config(path: str | Path) -> dict[str, Any]:
    """加载 TOML 配置文件"""
    path = Path(path)
    if not path.exists():
        logger.warning(f"配置文件不存在: {path}")
        return {}
    with open(path, "rb") as f:
        return tomllib.load(f)


def save_config(data: dict[str, Any], path: str | Path) -> None:
    """保存 TOML 配置文件"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        tomli_w.dump(data, f)


def merge_configs(*configs: dict[str, Any]) -> dict[str, Any]:
    """深度合并多个配置字典，后者覆盖前者"""
    result: dict[str, Any] = {}
    for config in configs:
        _deep_merge(result, config)
    return result


def _deep_merge(base: dict, override: dict) -> None:
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value

"""账号级 API Key 凭据解析：Key 存 SQLite，无 .env 回退、无跨账号回退。

凭据解析基于鉴权 token 的用户，绝不基于可伪造的请求体字段。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import config, db


@dataclass(frozen=True)
class Credentials:
    # repr/compare=False：明文 Key 不进 repr/日志/比较逻辑
    api_key: str = field(repr=False, compare=False)
    base_url: str
    model: str
    configured: bool  # api_key 非空


def mask(key: str) -> str:
    """脱敏回显：保留前 6 位（含 sk-）+ **** + 末 4 位；过短则全星号。"""
    if not key:
        return ""
    if len(key) <= 12:
        return "*" * 8
    return f"{key[:6]}****{key[-4:]}"


def llm_credentials(user: dict[str, Any] | None) -> Credentials:
    """对话大模型（DeepSeek）凭据：只取该账号自己的 Key。user 为 None → 未配置。"""
    if not user:
        return Credentials("", config.LLM_BASE_URL, config.LLM_MODEL, False)
    key = db.get_user_api_key(int(user["id"]), "deepseek")
    return Credentials(key, config.LLM_BASE_URL, config.LLM_MODEL, bool(key))


def embed_credentials() -> Credentials:
    """向量模型（百炼）凭据：只取管理员账号的 Key。"""
    admin_id = db.get_admin_user_id()
    if admin_id is None:
        return Credentials("", config.DASHSCOPE_BASE_URL, config.EMBEDDING_MODEL, False)
    key = db.get_user_api_key(admin_id, "dashscope")
    return Credentials(key, config.DASHSCOPE_BASE_URL, config.EMBEDDING_MODEL, bool(key))


def system_llm_credentials() -> Credentials:
    """数据刷新等系统级任务的 DeepSeek 凭据（管理员账号）。"""
    admin_id = db.get_admin_user_id()
    if admin_id is None:
        return Credentials("", config.LLM_BASE_URL, config.LLM_MODEL, False)
    return llm_credentials({"id": admin_id})

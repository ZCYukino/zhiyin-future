"""标准 JWT 签发与校验（HS256，无状态鉴权）。"""
from __future__ import annotations

import logging
import time
from typing import Any

import jwt

from . import config, db

logger = logging.getLogger("auth")
_LEGACY_SECRET = "zhiyin-future-jwt-secret-change-me"
_warned_legacy_secret = False


def _signing_secret() -> str:
    """旧公开密钥自动废弃；随机值随用户库持久化，不依赖进程生命周期。"""
    global _warned_legacy_secret
    configured = config.JWT_SECRET
    if configured and configured != _LEGACY_SECRET:
        return configured
    if configured == _LEGACY_SECRET and not _warned_legacy_secret:
        logger.warning("检测到旧模板公开 JWT_SECRET，已改用数据库内的随机密钥；旧会话需重新登录")
        _warned_legacy_secret = True
    return db.get_or_create_app_secret("jwt_signing")


def create_token(user_id: int, username: str, *, token_version: int) -> str:
    """签发时显式绑定认证/创建账号时的版本，不重新读取可能已被改密推进的版本。"""
    """签发 JWT，过期时间由 config.JWT_EXPIRE_HOURS 决定。"""
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + config.JWT_EXPIRE_HOURS * 3600,
        "ver": token_version,
    }
    return jwt.encode(payload, _signing_secret(), algorithm=config.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """校验签名与过期，返回载荷；无效/过期返回 None。"""
    try:
        payload = jwt.decode(
            token, _signing_secret(), algorithms=[config.JWT_ALGORITHM],
            options={"require": ["sub", "username", "iat", "exp", "ver"]},
        )
        if (
            not isinstance(payload["sub"], str) or not payload["sub"].isascii()
            or not payload["sub"].isdigit() or len(payload["sub"]) > 19
            or not 0 < int(payload["sub"]) <= 2**63 - 1
            or not isinstance(payload["username"], str) or not payload["username"]
            or type(payload["ver"]) is not int or payload["ver"] < 0
            or type(payload["iat"]) is not int or type(payload["exp"]) is not int
            or payload["exp"] <= payload["iat"]
        ):
            return None
        return payload
    except jwt.PyJWTError:
        return None

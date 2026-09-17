"""标准 JWT 签发与校验（HS256，无状态鉴权）。

token 载荷：sub（用户 id 字符串）、username、iat（签发时间）、exp（过期时间）。
前端通过 `Authorization: Bearer <token>` 回传，服务端解码后按 sub 查库取用户。
"""
from __future__ import annotations

import time
from typing import Any

import jwt

from . import config


def create_token(user_id: int, username: str) -> str:
    """签发 JWT，过期时间由 config.JWT_EXPIRE_HOURS 决定。"""
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "username": username,
        "iat": now,
        "exp": now + config.JWT_EXPIRE_HOURS * 3600,
    }
    return jwt.encode(payload, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any] | None:
    """校验签名与过期，返回载荷；无效/过期返回 None。"""
    try:
        return jwt.decode(token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None

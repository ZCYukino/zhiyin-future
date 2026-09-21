"""SQLite 用户存储：连接、建表、密码哈希与用户 CRUD。

密码 PBKDF2-HMAC-SHA256，token 见 auth.py，对外返回 camelCase 字段；
基于内置 sqlite3（单文件 backend/data/users.db），零外部数据库依赖。
"""
from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from typing import Any

from . import config

# 建表（新增列由 _MIGRATIONS 补齐）
_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    name TEXT NOT NULL DEFAULT '',
    email TEXT NOT NULL DEFAULT '',
    phone TEXT NOT NULL DEFAULT '',
    education TEXT NOT NULL DEFAULT '',
    school TEXT NOT NULL DEFAULT '',
    major TEXT NOT NULL DEFAULT '',
    experience TEXT NOT NULL DEFAULT '',
    skills TEXT,
    certificates TEXT NOT NULL DEFAULT '',
    internship TEXT,
    has_resume INTEGER NOT NULL DEFAULT 0,
    resume_name TEXT NOT NULL DEFAULT '',
    resume_text TEXT,
    resume_years TEXT NOT NULL DEFAULT '',
    awards TEXT NOT NULL DEFAULT '',
    projects TEXT,
    skill_evidence TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    ability_profile TEXT,
    match_report TEXT
)
"""

# 旧库缺列迁移：列名 → 补齐 DDL
_MIGRATIONS = (
    ("role", "ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'"),
    ("has_resume", "ALTER TABLE users ADD COLUMN has_resume INTEGER NOT NULL DEFAULT 0"),
    ("resume_name", "ALTER TABLE users ADD COLUMN resume_name TEXT NOT NULL DEFAULT ''"),
    ("resume_text", "ALTER TABLE users ADD COLUMN resume_text TEXT"),
    ("resume_years", "ALTER TABLE users ADD COLUMN resume_years TEXT NOT NULL DEFAULT ''"),
    ("certificates", "ALTER TABLE users ADD COLUMN certificates TEXT NOT NULL DEFAULT ''"),
    ("internship", "ALTER TABLE users ADD COLUMN internship TEXT"),
    ("awards", "ALTER TABLE users ADD COLUMN awards TEXT NOT NULL DEFAULT ''"),
    ("projects", "ALTER TABLE users ADD COLUMN projects TEXT"),
    ("skill_evidence", "ALTER TABLE users ADD COLUMN skill_evidence TEXT"),
    ("ability_profile", "ALTER TABLE users ADD COLUMN ability_profile TEXT"),
    ("match_report", "ALTER TABLE users ADD COLUMN match_report TEXT"),
)

# 每账号每 provider 一行，接口只回显脱敏值
_KEYS_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_api_keys (
    user_id    INTEGER NOT NULL,
    provider   TEXT    NOT NULL,
    api_key    TEXT    NOT NULL,
    updated_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
    PRIMARY KEY (user_id, provider)
)
"""


# 建表已在哪个库文件跑过（按路径记录，测试 monkeypatch 后自动重建）
_initialized_path: str | None = None


def _connect() -> sqlite3.Connection:
    global _initialized_path
    path = str(config.DB_PATH)
    if _initialized_path != path:
        # 先置位再建表，避免 init_db 递归；建表连接用完即关
        _initialized_path = path
        try:
            init_db()
        except Exception:
            _initialized_path = None  # 建表失败，下次连接重试
            raise
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.isolation_level = None  # 自动提交
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """幂等建表（含列迁移），由 _connect() 在首次连接某库文件时自动调用。"""
    conn = _connect()
    try:
        conn.execute(_SCHEMA)
        conn.execute(_KEYS_SCHEMA)
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
        for col, ddl in _MIGRATIONS:
            if col not in cols:
                conn.execute(ddl)
    finally:
        conn.close()


PBKDF2_ITERATIONS = 100_000


def hash_password(password: str) -> str:
    """PBKDF2-HMAC-SHA256：`pbkdf2_sha256$迭代次数$盐$摘要`，盐随机防彩虹表。"""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """校验密码；兼容历史加盐 MD5（`salt:md5hex`）旧账号。"""
    if not stored.startswith("pbkdf2_sha256$"):
        try:
            salt, digest = stored.split(":", 1)
        except ValueError:
            return False
        calc = hashlib.md5((salt + password).encode("utf-8")).hexdigest()
        return secrets.compare_digest(calc, digest)
    try:
        _, iters_s, salt, digest = stored.split("$", 3)
        iters = int(iters_s)
    except (ValueError, TypeError):
        return False
    calc = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), iters
    )
    return secrets.compare_digest(calc.hex(), digest)


def _row_to_user(row: sqlite3.Row | dict[str, Any] | None) -> dict[str, Any] | None:
    if not row:
        return None
    row = dict(row)
    try:
        skills = json.loads(row.get("skills") or "[]")
    except (json.JSONDecodeError, TypeError):
        skills = []
    if not isinstance(skills, list):
        skills = []
    return {
        "id": str(row["id"]),
        "username": row["username"],
        "role": row.get("role") or "user",
        "name": row["name"],
        "email": row["email"],
        "phone": row["phone"],
        "education": row["education"],
        "school": row["school"],
        "major": row["major"],
        "experience": row["experience"],
        "certificates": row.get("certificates") or "",
        "internship": row.get("internship") or "",
        "hasResume": bool(row["has_resume"]),
        "resumeName": row["resume_name"],
        "resumeText": row.get("resume_text") or "",
        "resumeYears": row.get("resume_years") or "",
        "awards": row.get("awards") or "",
        "projects": row.get("projects") or "",
        "skillEvidence": row.get("skill_evidence") or "",
        "userSkills": skills,
    }


def is_reserved_username(username: str) -> bool:
    """内置管理员用户名为系统保留，不允许注册抢占。"""
    return bool(config.ADMIN_USERNAME) and username.strip() == config.ADMIN_USERNAME


def create_user(username: str, password: str) -> dict[str, Any] | None:
    """创建用户并返回 user；用户名已存在返回 None。JWT 由上层签发。"""
    if is_reserved_username(username):
        return None
    conn = _connect()
    try:
        pwd = hash_password(password)
        cur = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, pwd),
        )
        uid = cur.lastrowid
        row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
        return _row_to_user(row)
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def ensure_admin(username: str, password: str) -> None:
    """确保管理员账号存在且具备 admin 角色；密码仅首次创建时用初始值，重启不重置。"""
    conn = _connect()
    try:
        row = conn.execute("SELECT id FROM users WHERE username = ?", (username,)).fetchone()
        if row:
            conn.execute("UPDATE users SET role = 'admin' WHERE id = ?", (row["id"],))
        else:
            conn.execute(
                "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
                (username, hash_password(password)),
            )
    finally:
        conn.close()


def authenticate(username: str, password: str) -> dict[str, Any] | None:
    """校验用户名密码，成功返回 user（JWT 由上层 auth 模块签发）。"""
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if not row or not verify_password(password, row["password_hash"]):
            return None
        return _row_to_user(row)
    finally:
        conn.close()


# 前端 camelCase 字段 → users 表列名
_FIELD_TO_COLUMN = {
    "name": "name",
    "email": "email",
    "phone": "phone",
    "education": "education",
    "school": "school",
    "major": "major",
    "experience": "experience",
    "certificates": "certificates",
    "internship": "internship",
    "hasResume": "has_resume",
    "resumeName": "resume_name",
    "resumeText": "resume_text",
    "resumeYears": "resume_years",
    "awards": "awards",
    "projects": "projects",
    "skillEvidence": "skill_evidence",
}


def update_user(user_id: int, fields: dict[str, Any]) -> dict[str, Any] | None:
    """按 id 更新资料；skills 以 userSkills 数组传入。返回更新后 user。"""
    sets: list[str] = []
    params: list[Any] = []

    for key, value in fields.items():
        if key == "userSkills":
            if isinstance(value, list):
                sets.append("skills = ?")
                params.append(json.dumps(value, ensure_ascii=False))
            continue
        col = _FIELD_TO_COLUMN.get(key)
        if col is None:
            continue
        if key == "hasResume":
            value = 1 if value else 0
        sets.append(f"{col} = ?")
        params.append(value)

    if not sets:
        return get_user_by_id(user_id)

    conn = _connect()
    try:
        params.append(user_id)
        conn.execute(f"UPDATE users SET {', '.join(sets)} WHERE id = ?", params)
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_user(row)
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    conn = _connect()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_user(row)
    finally:
        conn.close()


def change_password(user_id: int, old_password: str, new_password: str) -> bool:
    """校验旧密码后更新，成功返回 True。"""
    conn = _connect()
    try:
        row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row or not verify_password(old_password, row["password_hash"]):
            return False
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hash_password(new_password), user_id),
        )
        return True
    finally:
        conn.close()


def _save_json_column(user_id: int, column: str, data: dict[str, Any] | None) -> None:
    """把 dict 写入 users 表的指定 JSON 列；data 为 None 时清空该列。"""
    payload = json.dumps(data, ensure_ascii=False) if data is not None else None
    conn = _connect()
    try:
        conn.execute(
            f'UPDATE users SET "{column}" = ? WHERE id = ?',
            (payload, user_id),
        )
    finally:
        conn.close()


def _get_json_column(user_id: int, column: str) -> dict[str, Any] | None:
    conn = _connect()
    try:
        row = conn.execute(f'SELECT "{column}" FROM users WHERE id = ?', (user_id,)).fetchone()
        if not row or not row[column]:
            return None
        try:
            return json.loads(row[column])
        except (json.JSONDecodeError, TypeError):
            return None
    finally:
        conn.close()


def save_ability_profile(user_id: int, data: dict[str, Any] | None) -> None:
    _save_json_column(user_id, "ability_profile", data)


def get_ability_profile(user_id: int) -> dict[str, Any] | None:
    return _get_json_column(user_id, "ability_profile")


def save_match_report(user_id: int, data: dict[str, Any] | None) -> None:
    _save_json_column(user_id, "match_report", data)


def get_match_report(user_id: int) -> dict[str, Any] | None:
    return _get_json_column(user_id, "match_report")


def get_user_api_key(user_id: int, provider: str) -> str:
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT api_key FROM user_api_keys WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        ).fetchone()
        return str(row["api_key"]) if row else ""
    finally:
        conn.close()


def set_user_api_key(user_id: int, provider: str, api_key: str) -> None:
    """UPSERT：同 (user_id, provider) 已有行则覆盖并刷新 updated_at。"""
    conn = _connect()
    try:
        conn.execute(
            """INSERT INTO user_api_keys (user_id, provider, api_key, updated_at)
               VALUES (?, ?, ?, datetime('now','localtime'))
               ON CONFLICT(user_id, provider) DO UPDATE SET
                 api_key = excluded.api_key,
                 updated_at = excluded.updated_at""",
            (user_id, provider, api_key),
        )
    finally:
        conn.close()


def delete_user_api_key(user_id: int, provider: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "DELETE FROM user_api_keys WHERE user_id = ? AND provider = ?",
            (user_id, provider),
        )
    finally:
        conn.close()


def get_user_api_keys(user_id: int) -> dict[str, dict[str, Any]]:
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT provider, api_key, updated_at FROM user_api_keys WHERE user_id = ?",
            (user_id,),
        ).fetchall()
        return {
            str(r["provider"]): {"apiKey": str(r["api_key"]), "updatedAt": str(r["updated_at"])}
            for r in rows
        }
    finally:
        conn.close()


def get_admin_user_id() -> int | None:
    """管理员账号行 id：按 config.ADMIN_USERNAME 查；找不到则回退 role='admin' 的最小 id。"""
    conn = _connect()
    try:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?", (config.ADMIN_USERNAME,)
        ).fetchone()
        if row:
            return int(row["id"])
        row = conn.execute(
            "SELECT id FROM users WHERE role = 'admin' ORDER BY id LIMIT 1"
        ).fetchone()
        return int(row["id"]) if row else None
    finally:
        conn.close()

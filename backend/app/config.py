"""全局配置：读取 .env、路径与模型名。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 目录：app/config.py -> backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data"
VECTOR_DIR = DATA_DIR / "vector"
SNAPSHOT_DIR = DATA_DIR / "snapshots"  # AI 清洗后的知识快照 JSON

DATA_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# 加载 .env（override=True：项目 .env 优先于系统环境变量）
load_dotenv(BACKEND_ROOT / ".env", override=True)


def _env(key: str, default: str = "") -> str:
    """读环境变量；**空值一律按「未设置」处理**，回落到默认值。

    .env 里写了 `KEY=`（冒号后留空）时 dotenv 会把变量设成空串，此时
    `os.getenv(key, default)` 拿到的是空串而不是默认值。事故：.env.example 里
    有一行空的 `DB_PATH=`，用户照 README `copy .env.example .env` 之后 DB_PATH 变成空串，
    SQLite 会落到**私有临时库**上——账号、简历、报告重启后全没。
    同理空的 `JWT_EXPIRE_HOURS=` 会让下面 int() 直接抛错，后端起不来。
    """
    return os.getenv(key, "").strip() or default


# ===== 大模型（对话 / 生成）：DeepSeek =====
LLM_BASE_URL = _env("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = _env("LLM_MODEL", "deepseek-flash")

# ===== 向量模型：阿里云百炼（DashScope）=====
DASHSCOPE_BASE_URL = _env("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBEDDING_MODEL = _env("EMBEDDING_MODEL", "text-embedding-v3")

# ===== 数据落地 =====
SNAPSHOT_KEEP = 2  # 只保留最近 2 版快照
COLLECTION_NAME = "jd_fragments"

# ===== SQLite 用户存储（零外部依赖，单文件） =====
DB_PATH = _env("DB_PATH", str(DATA_DIR / "users.db"))

# ===== JWT 鉴权 =====
JWT_SECRET = _env("JWT_SECRET", "zhiyin-future-jwt-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(_env("JWT_EXPIRE_HOURS", "24"))

# ===== 内置管理员账号（.env 可配置，改后重启生效） =====
# 每次启动时按此处配置强同步管理员账号：存在则把角色提升为 admin（不动密码），
# 不存在则用 ADMIN_PASSWORD 作为初始密码创建。改密码只在网页端进行，重启不会重置。
ADMIN_USERNAME = _env("ADMIN_USERNAME", "ZCY")
ADMIN_PASSWORD = _env("ADMIN_PASSWORD", "123456")

# ===== 其他 =====
EMBEDDING_DIM = 1024
REQUEST_TIMEOUT = 60

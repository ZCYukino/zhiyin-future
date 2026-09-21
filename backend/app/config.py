"""全局配置：读取 .env、路径与模型名。"""
import os
from pathlib import Path

from dotenv import load_dotenv

# 目录：app/config.py -> backend/
BACKEND_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_ROOT / "data"
VECTOR_DIR = DATA_DIR / "vector"
SNAPSHOT_DIR = DATA_DIR / "snapshots"  # 知识快照 JSON

DATA_DIR.mkdir(parents=True, exist_ok=True)
VECTOR_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)

# 项目 .env 优先于系统环境变量
load_dotenv(BACKEND_ROOT / ".env", override=True)


def _env(key: str, default: str = "") -> str:
    """读环境变量；空值按未设置处理，回落默认值（.env 里 KEY= 会设成空串而非默认值）。"""
    return os.getenv(key, "").strip() or default


# DeepSeek
LLM_BASE_URL = _env("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = _env("LLM_MODEL", "deepseek-flash")

# 阿里云百炼（DashScope）
DASHSCOPE_BASE_URL = _env("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
EMBEDDING_MODEL = _env("EMBEDDING_MODEL", "text-embedding-v3")

SNAPSHOT_KEEP = 2  # 只保留最近 2 版快照
COLLECTION_NAME = "jd_fragments"

# SQLite 用户存储
DB_PATH = _env("DB_PATH", str(DATA_DIR / "users.db"))

# JWT
JWT_SECRET = _env("JWT_SECRET", "zhiyin-future-jwt-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(_env("JWT_EXPIRE_HOURS", "24"))

# 内置管理员账号
# 每次启动强同步：存在则提权（不动密码），不存在则用初始密码创建
ADMIN_USERNAME = _env("ADMIN_USERNAME", "ZCY")
ADMIN_PASSWORD = _env("ADMIN_PASSWORD", "123456")

EMBEDDING_DIM = 1024
REQUEST_TIMEOUT = 60

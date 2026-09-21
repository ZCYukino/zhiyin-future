"""pytest 全局引导：在导入任何 `app.*` 之前，把存储重定向到进程级临时目录。

app.server 在导入时就会执行 ensure_seed_snapshot / init_db / ensure_admin，
不提前重定向会直接写开发机真实 data 目录。config 在导入时读环境变量，
故先设 os.environ["DB_PATH"]；其余目录属性在 import config 之后、import server 之前改写。
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

# 会话级临时根目录：import 期就要用
_TMP_ROOT = Path(tempfile.mkdtemp(prefix="zc-backend-tests-"))

# 必须在 import app.* 之前：config 在导入时即读取该环境变量
os.environ["DB_PATH"] = str(_TMP_ROOT / "users.db")

from app import config  # noqa: E402  必须晚于上面的 os.environ 设置

# 必须早于 app.server 的导入，否则 ensure_seed_snapshot / init_db 已打到真实目录
config.DATA_DIR = _TMP_ROOT / "data"
config.SNAPSHOT_DIR = config.DATA_DIR / "snapshots"
config.VECTOR_DIR = config.DATA_DIR / "vector"
# ingest 导入时固化了 JD_ARCHIVE_PATH，raw_jds 也一并落到临时目录
for _d in (config.SNAPSHOT_DIR, config.VECTOR_DIR, config.DATA_DIR / "raw_jds"):
    _d.mkdir(parents=True, exist_ok=True)

# 兜底：若有人把 DB_PATH 写进 .env，此处再钉回临时目录
if not Path(config.DB_PATH).is_relative_to(_TMP_ROOT):
    config.DB_PATH = str(_TMP_ROOT / "users.db")


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """收尾清理临时存储；Windows 上句柄可能未释放，删除失败不影响结果。"""
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)

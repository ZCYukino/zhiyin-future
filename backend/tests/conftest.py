"""pytest 全局引导：在导入任何 `app.*` 之前，把存储重定向到进程级临时目录。

为什么必须发生在「导入之前」
----------------------------
`app/server.py` 在**模块导入时**就执行 `store.ensure_seed_snapshot()`、`db.init_db()`
与 `db.ensure_admin(...)`（server.py 约 39-47 行），而 `tests/test_server_apikey.py` 在
模块级 `from app import ... server`。那一刻 `config.DB_PATH` 仍指向真实路径
`backend/data/users.db`，于是「跑一次 pytest」就是对开发者本机数据动手：

* 全新克隆（`data/` 不存在）→ 导入即**创建**真实 `data/users.db` 并写入管理员行（实测）；
* 管理员行缺失或被降级 → 导入即把它 **UPDATE 回 admin**（实测文件 bytes 改变）；
* 快照目录为空 → `ensure_seed_snapshot()` 会在真实 `data/snapshots/` 落一份种子快照。

本机此刻的 `data/users.db` 恰好已存在且 `ZCY` 已是 admin，`ensure_admin` 发的是同值
UPDATE，SQLite 未改动页面 → 该文件的 bytes 与 mtime 恰好不变。这是巧合而非保证：换一台
机器 / 换一份 data 目录就会真的写进去。

做法
----
`config.py` 用 `_env("DB_PATH", ...)` 在导入时读环境变量，故本文件最顶部先设
`os.environ["DB_PATH"]`（`.env` 中不含 `DB_PATH` 键，`load_dotenv(override=True)`
不会覆盖它）。`DATA_DIR` / `SNAPSHOT_DIR` / `VECTOR_DIR` 是无环境变量覆盖的普通模块
属性，只能在 `import app.config` 之后、导入 `app.server` 之前直接改写。

pytest 保证 `conftest.py` 先于所有测试模块被导入，因此无论测试文件的导入顺序如何，
`app.server` 等模块被导入时看到的都已经是临时路径。各测试内部继续用 `monkeypatch`
把 `config.DB_PATH` 指到自己的 `tmp_path`（更细粒度的隔离），本文件不与之冲突。
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

# 会话级临时根目录：import 期就要用，故不能依赖 tmp_path_factory 这类夹具。
_TMP_ROOT = Path(tempfile.mkdtemp(prefix="zc-backend-tests-"))

# 必须在 `import app.*` 之前：config 在导入时即读取该环境变量。
os.environ["DB_PATH"] = str(_TMP_ROOT / "users.db")

from app import config  # noqa: E402  必须晚于上面的 os.environ 设置

# 这些是普通模块属性（无 env 覆盖），导入 config 之后直接改写；
# 必须早于 `app.server` 的导入，否则 ensure_seed_snapshot / init_db 已打到真实目录。
config.DATA_DIR = _TMP_ROOT / "data"
config.SNAPSHOT_DIR = config.DATA_DIR / "snapshots"
config.VECTOR_DIR = config.DATA_DIR / "vector"
# ingest 在导入时把 JD_ARCHIVE_PATH 固化为 DATA_DIR/raw_jds/jd_archive.json（其 main()
# 无论结果如何都会重写该文件），故 raw_jds 也一并落到临时目录。
for _d in (config.SNAPSHOT_DIR, config.VECTOR_DIR, config.DATA_DIR / "raw_jds"):
    _d.mkdir(parents=True, exist_ok=True)

# 兜底：万一将来有人把 DB_PATH 写进 .env，load_dotenv(override=True) 会盖掉上面的环境变量，
# 此处再把属性钉回临时目录，保证真实库文件永远不在测试的写入范围内。
if not Path(config.DB_PATH).is_relative_to(_TMP_ROOT):
    config.DB_PATH = str(_TMP_ROOT / "users.db")


def pytest_sessionfinish(session, exitstatus):  # noqa: ARG001
    """收尾清理临时存储；Windows 上 ChromaDB/SQLite 句柄可能未释放，删除失败不影响结果。"""
    shutil.rmtree(_TMP_ROOT, ignore_errors=True)

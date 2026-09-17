"""测试自身的隔离性：跑 pytest 不得碰仓库里的 backend/data/。

对应 tests/conftest.py 的临时目录重定向。这不是洁癖：`app/server.py` 在**模块导入时**
就执行 `store.ensure_seed_snapshot()` / `db.init_db()` / `db.ensure_admin(...)`，而
`tests/test_server_apikey.py` 在模块级导入 server —— 一旦存储指向真实路径，仅仅「跑一次
pytest」就会在开发者的仓库里建出 users.db、把管理员行提权、或在 data/snapshots/ 落一份
种子快照。此用例把「已重定向」钉成不变量，防止将来 conftest 被改动后悄悄回归。
"""
from __future__ import annotations

from pathlib import Path

from app import config


def test_storage_is_redirected_away_from_repo_data_dir():
    repo_data = (config.BACKEND_ROOT / "data").resolve()
    targets = {
        "DB_PATH": Path(config.DB_PATH),
        "SNAPSHOT_DIR": Path(config.SNAPSHOT_DIR),
        "VECTOR_DIR": Path(config.VECTOR_DIR),
        "DATA_DIR": Path(config.DATA_DIR),
    }
    for name, path in targets.items():
        assert not path.resolve().is_relative_to(repo_data), f"{name} 仍指向仓库 data/：{path}"

"""测试自身的隔离性：跑 pytest 不得碰仓库里的 backend/data/。

server 在导入时就会建库/落快照，故此处把 conftest 的临时目录重定向钉成不变量。
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

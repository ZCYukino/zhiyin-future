"""数据落地：JSON 快照版本管理（保留最近 2 版）+ ChromaDB 向量存储。"""
from __future__ import annotations

import json
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

import chromadb

from . import config

SNAPSHOT_PREFIX = "knowledge-"
SNAPSHOT_SUFFIX = ".json"

# 内置种子快照：随仓库分发，离线（无爬虫/无 LLM key）也能秒级加载完整数据
SEED_SNAPSHOT = config.BACKEND_ROOT / "seed" / "knowledge-seed.json"

# ===== JSON 快照管理 =====


def _snapshot_path(ts: str) -> Path:
    return config.SNAPSHOT_DIR / f"{SNAPSHOT_PREFIX}{ts}{SNAPSHOT_SUFFIX}"


def save_snapshot(data: dict[str, Any]) -> Path:
    """写入快照（原子替换），保留最近 N 版并删除更旧的。"""
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = _snapshot_path(ts)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)
    _prune_snapshots()
    return path


def _prune_snapshots() -> None:
    snaps = list_snapshots()
    for p in snaps[:-config.SNAPSHOT_KEEP]:
        p.unlink(missing_ok=True)


def list_snapshots() -> list[Path]:
    return sorted(
        config.SNAPSHOT_DIR.glob(f"{SNAPSHOT_PREFIX}*{SNAPSHOT_SUFFIX}"),
        key=lambda p: p.name,
    )


def load_latest_snapshot() -> dict[str, Any] | None:
    """读最新快照，**每次返回一份全新解析的对象**。

    写方（ingest / enrich）用这个：它们会就地改这份 dict 再 save_snapshot()，
    必须拿到私有副本，否则改到一半会被别的请求读到。
    只读的请求路径请用 load_cached_snapshot()。
    """
    snaps = list_snapshots()
    if not snaps:
        return None
    return json.loads(snaps[-1].read_text(encoding="utf-8"))


# 只读快照缓存：450KB 的快照每次 glob + 读盘 + json.loads 约 4.5ms，
# 而 analyze / 列表类接口每次请求都要读一遍。按 (路径, mtime) 缓存，
# ingest/enrich 写出新快照后 mtime 变化 → 自动失效，无需重启。
_snapshot_cache: dict[str, Any] = {"path": None, "mtime": 0.0, "data": None}
_snapshot_lock = threading.Lock()


def load_cached_snapshot() -> dict[str, Any]:
    """读最新快照（进程内缓存，跨请求复用同一份对象）。

    ⚠️ 返回的是**共享对象**，调用方一律只读。要改快照请用 load_latest_snapshot()
    拿副本，改完 save_snapshot()。目前唯一的写方是 ingest / enrich。
    """
    snaps = list_snapshots()
    if not snaps:
        return {}
    latest = snaps[-1]
    path = str(latest)
    with _snapshot_lock:
        # stat 必须在锁内做：管理端刷新失败回滚（_rollback_partial_snapshots）会
        # 删除最新的快照文件，stat 在锁外可能刚好撞上文件被删 → FileNotFoundError → 500
        mtime = latest.stat().st_mtime
        if _snapshot_cache["path"] == path and _snapshot_cache["mtime"] == mtime:
            return _snapshot_cache["data"]
        data = json.loads(latest.read_text(encoding="utf-8"))
        _snapshot_cache.update(path=path, mtime=mtime, data=data)
        return data


def ensure_seed_snapshot() -> None:
    """首次启动且无任何快照时，从内置种子快照复制一份（带当前时间戳），保证离线可演示。"""
    if list_snapshots():
        return
    if not SEED_SNAPSHOT.exists():
        return
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copyfile(SEED_SNAPSHOT, _snapshot_path(ts))


# ===== ChromaDB =====

# ChromaDB 底层为 SQLite，并发读写会触发 "database is locked"。此锁覆盖所有对集合的
# 读（rag.search）、写（upsert_fragments）与重建（reset_collection），确保 admin 刷新
# 与用户检索并发时互斥。embedding（HTTP 调用）在锁外执行，保持并发。
col_lock = threading.Lock()

_chroma_client: chromadb.ClientAPI | None = None


def _get_chroma() -> chromadb.ClientAPI:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=str(config.VECTOR_DIR))
    return _chroma_client


def get_collection():
    return _get_chroma().get_or_create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def reset_collection():
    """重建向量库（全量采集时调用）。"""
    with col_lock:
        try:
            _get_chroma().delete_collection(config.COLLECTION_NAME)
        except Exception:
            pass
        return get_collection()


def upsert_fragments(ids, texts, metadatas, embeddings) -> None:
    with col_lock:
        col = get_collection()
        col.upsert(ids=ids, documents=texts, metadatas=metadatas, embeddings=embeddings)

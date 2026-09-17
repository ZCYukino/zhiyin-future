"""RAG 检索：从 ChromaDB 检索相关 JD 片段，用于 LLM 生成时的检索增强与幻觉防控。"""
from __future__ import annotations

import logging
from typing import Any

from . import settings
from .llm import LLMNotConfigured, embed
from .store import col_lock, get_collection

logger = logging.getLogger("rag")


def search(query: str, top_k: int = 6) -> list[dict[str, Any]]:
    """向量检索相关 JD 片段。未配置 Key 抛 LLMNotConfigured（配置问题不静默）；网络异常/空库返回空。"""
    try:
        # embedding（HTTP 调用）在锁外执行以充分利用推理；锁只覆盖集合读段。
        # 显式传入管理员百炼 Key（检索只服务于管理员触发的采集/画像链路，非用户请求）。
        qe = embed([query], credentials=settings.embed_credentials())[0]
    except LLMNotConfigured:
        raise  # 未配置 Key 是配置问题，向上抛让调用方明确处理，不静默降级
    except Exception as e:  # noqa: BLE001 网络异常 → 降级为空（降级但必须留痕，否则向量库坏了看起来像「没结果」）
        logger.warning("向量检索失败，本次降级为空结果（query=%r）：%s", query, e)
        return []
    with col_lock:
        col = get_collection()
        count = col.count()
        if count == 0:
            return []
        res = col.query(
            query_embeddings=[qe],
            n_results=min(top_k, count),
            include=["documents", "metadatas", "distances"],
        )
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    dists = res.get("distances", [[]])[0]
    out: list[dict[str, Any]] = []
    for d, m, dist in zip(docs, metas, dists):
        out.append({"text": d, "meta": m or {}, "distance": dist})
    return out


def build_context(query: str, top_k: int = 6) -> str:
    """构建供 LLM 引用的上下文块（含来源标注，供报告溯源）。"""
    hits = search(query, top_k=top_k)
    if not hits:
        return ""
    parts: list[str] = []
    for i, h in enumerate(hits, 1):
        src = h["meta"].get("source", "未知来源")
        parts.append(f"[{i}]（来源：{src}）\n{h['text']}")
    return "\n\n".join(parts)

"""一次性快照富化：对现有快照逐岗位调用 RAG+LLM 画像生成，回写富文本字段并落盘。

用法：cd backend && D:/Anaconda/python.exe -m app.enrich
不重新爬取 JD，仅对已有岗位做 LLM 润色，画像写入快照 jobProfiles。
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from . import store
from .extract import _infer_stack
from .ingest import index_vectors
from .llm import LLMNotConfigured
# server 内已惰性导入 enrich，此处不能在 server 顶层新增 import enrich（循环导入）
from .server import generate_job_profile

logger = logging.getLogger("enrich")


def _enrich_one(job: dict[str, Any], k: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    jid = job.get("id")
    try:
        return jid, generate_job_profile(job, k)
    except LLMNotConfigured:
        raise  # 未配置/失效的 Key 是配置问题，向上抛让整轮富化尽早失败（同 ingest 的抽取与演化）
    except Exception as e:  # noqa: BLE001
        logger.warning("富化失败 %s：%s", job.get("name"), e)
        return jid, None


def enrich_snapshot(
    reindex: bool = True,
    workers: int = 4,
    progress: Callable[[str, int], None] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    k = store.load_latest_snapshot() or {}
    jobs = k.get("jobs", []) or []
    if not jobs:
        logger.warning("无快照可富化")
        return k, []
    jobs_by_id = {j["id"]: j.get("name") or j["id"] for j in jobs}

    def report(pct: int) -> None:
        if progress:
            progress("岗位画像富化", pct)

    # 并行生成；已有画像的岗位跳过
    existing = k.get("jobProfiles") or {}
    todo = [j for j in jobs if j["id"] not in existing]
    if not todo:
        logger.info("所有岗位均已富化，无需重复生成")
        report(100)
        return k, []
    profiles: dict[str, dict[str, Any]] = dict(existing)
    failed: list[str] = []
    report(0)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_enrich_one, j, k): j for j in todo}
        done = 0
        for fut in as_completed(futs):
            jid, p = fut.result()
            done += 1
            if p:
                profiles[jid] = p
            else:
                failed.append(jobs_by_id.get(jid, jid))
            report(int(done / len(todo) * 100))
            if done % 5 == 0 or done == len(todo):
                logger.info("富化进度 %d/%d", done - len(failed), len(todo))

    # 回写快照（串行，避免并发写 dict）
    job_intro = k.setdefault("jobIntro", {})
    job_req = k.setdefault("jobRequirements", {})
    job_prog = k.setdefault("jobSkillProgression", {})
    job_profiles = k.setdefault("jobProfiles", {})
    for job in jobs:
        jid = job["id"]
        p = profiles.get(jid)
        if not p:
            continue
        job_profiles[jid] = p
        job_intro[jid] = {
            "duties": p.get("duties") or [],
            "scenarios": p.get("scenarios") or [],
        }
        req = p.get("requirements") or {}
        job_req[jid] = {
            "education": req.get("education") or "",
            "experience": req.get("experience") or "",
            "extra": req.get("extra") or [],
        }
        skills = p.get("skills") or {}
        job_prog[jid] = {
            lv: [
                {"name": s.get("name", ""), "stack": _infer_stack(s.get("name", "")), "desc": s.get("desc", "")}
                for s in (skills.get(lv) or [])
                if s.get("name")
            ]
            for lv in ("junior", "mid", "senior")
        }
        if p.get("overview"):
            job["description"] = p["overview"]
        names = [s.get("name") for lv in ("junior", "mid", "senior") for s in (skills.get(lv) or [])]
        if names:
            job["skills"] = names[:8]
            job["tags"] = names[:3]

    k["meta"] = {**(k.get("meta") or {}), "enriched": True, "jobProfiles": len(job_profiles)}
    # 先落盘快照、再重建向量：向量库不能比被服务的快照新
    path = store.save_snapshot(k)
    if reindex:
        index_vectors(k)
    logger.info("富化完成，快照：%s（%d 岗位，画像 %d 份，失败 %d）", path.name, len(jobs), len(job_profiles), len(failed))
    report(100)
    return k, failed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    enrich_snapshot()

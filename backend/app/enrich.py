"""一次性快照富化：对现有快照逐岗位调用 RAG+LLM 画像生成，回写富文本字段并落盘。

用法：cd backend && D:/Anaconda/python.exe -m app.enrich
（不重新爬取 JD，仅对已有岗位做 LLM 润色，产出更详细的职责/场景/技能/要求，
  并把完整岗位画像写入快照 jobProfiles，使详情页接口毫秒级返回、无需再调 LLM。）
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from . import store
from .extract import _infer_stack
from .ingest import index_vectors
from .llm import LLMNotConfigured
# 注意：server 模块内有指向 enrich 的惰性导入（_run_refresh 内），
# 切勿在 server 顶层新增 `import enrich`，否则启动即循环导入。
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

    # 并行生成（DeepSeek 推理是主要耗时，串行 34×35s≈20min，4 并发可压到 ~6min）
    # 幂等：已有画像的岗位跳过，重跑只补齐缺失项
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
        # 岗位介绍：职责 + 典型行业应用场景
        job_intro[jid] = {
            "duties": p.get("duties") or [],
            "scenarios": p.get("scenarios") or [],
        }
        # 任职要求：学历 / 经验 / 证书专业背景等
        req = p.get("requirements") or {}
        job_req[jid] = {
            "education": req.get("education") or "",
            "experience": req.get("experience") or "",
            "extra": req.get("extra") or [],
        }
        # 技能矩阵：三级资历，每项带 stack + desc（在本岗位的具体用途）
        skills = p.get("skills") or {}
        job_prog[jid] = {
            lv: [
                {"name": s.get("name", ""), "stack": _infer_stack(s.get("name", "")), "desc": s.get("desc", "")}
                for s in (skills.get(lv) or [])
                if s.get("name")
            ]
            for lv in ("junior", "mid", "senior")
        }
        # 岗位一句话定位：润色 description
        if p.get("overview"):
            job["description"] = p["overview"]
        # 技能标签：合并富技能名
        names = [s.get("name") for lv in ("junior", "mid", "senior") for s in (skills.get(lv) or [])]
        if names:
            job["skills"] = names[:8]
            job["tags"] = names[:3]

    k["meta"] = {**(k.get("meta") or {}), "enriched": True, "jobProfiles": len(job_profiles)}
    # 顺序：先落盘快照、再重建向量。向量库绝不能比被服务的快照更新——否则 RAG 会检索到
    # 快照里根本不存在的内容；反过来（快照新、向量旧）只是检索略滞后，可接受。
    # 且向量化失败不应让一份已生成好的快照作废（反之则会）。
    path = store.save_snapshot(k)
    if reindex:
        index_vectors(k)
    logger.info("富化完成，快照：%s（%d 岗位，画像 %d 份，失败 %d）", path.name, len(jobs), len(job_profiles), len(failed))
    report(100)
    return k, failed


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    enrich_snapshot()

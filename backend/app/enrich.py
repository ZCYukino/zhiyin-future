"""候选知识库富化：不读/写活动快照，不访问上一版向量库。"""
from __future__ import annotations

import copy
import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from . import config, settings, store
from .extract import CATEGORIES, _infer_stack
from .llm import LLMNotConfigured, generate_json
from .prompts import JOB_PROFILE_PROMPT

logger = logging.getLogger("enrich")

_CATEGORY_NAMES = {c["id"]: c["name"] for c in CATEGORIES}


def _build_job_context(job: dict[str, Any], k: dict[str, Any]) -> str:
    """把本地知识库中该岗位的全部结构化信息汇总为 LLM 参考上下文。"""
    jid = job.get("id")
    lines = [
        f"名称：{job.get('name', '')}",
        f"分类：{_CATEGORY_NAMES.get(job.get('categoryId', ''), '')}",
        f"薪资：{job.get('salaryMin', '')}-{job.get('salaryMax', '')} {job.get('salaryUnit', 'K/月')}",
        # 字段为 None 时用 or，dict 默认值对显式 None 不生效
        f"招聘公司数：{job.get('companyCount') or ''}家",
        f"热度：{job.get('hotScore') or ''}",
        f"技能标签：{'、'.join(job.get('skills', []) or [])}",
    ]
    prog = (k.get("jobSkillProgression") or {}).get(jid)
    if prog:
        for lv, label in (("junior", "初级·必备"), ("mid", "中级·重要"), ("senior", "高级·加分")):
            names = [s["name"] if isinstance(s, dict) else str(s) for s in (prog.get(lv) or [])]
            if names:
                lines.append(f"技能矩阵 {label}：{'、'.join(names)}")
    req = (k.get("jobRequirements") or {}).get(jid)
    if req:
        lines.append(f"任职要求：学历 {req.get('education', '')}，经验 {req.get('experience', '')}")
    intro = (k.get("jobIntro") or {}).get(jid)
    if intro:
        duties = intro.get("duties") or []
        if duties:
            lines.append(f"已知职责：{'；'.join(duties)}")
        scen = intro.get("scenarios") or []
        if scen:
            lines.append(f"已知场景：{'；'.join(s.get('name', '') for s in scen if isinstance(s, dict))}")
    changes = [c for c in (k.get("capabilityChanges") or []) if c.get("jobId") == jid]
    if changes:
        # 取 period 最大的一条作为近期
        recent = max(changes, key=lambda c: str(c.get("period", "")))
        parts = []
        if recent.get("addedSkills"):
            parts.append(f"新增 {'、'.join(recent['addedSkills'])}")
        if recent.get("importanceUp"):
            parts.append(f"重要性上升 {'、'.join(recent['importanceUp'])}")
        if parts:
            lines.append(f"近期能力演化（{recent.get('period', '')}）：{'；'.join(parts)}")
    return "\n".join(lines)


def _build_profile_prompt(job: dict[str, Any], knowledge: dict[str, Any]) -> str:
    """生成与缓存共享同一份完整模型输入，避免遗漏字段使旧画像误命中。"""
    context = "\n\n".join(
        (entry.get("text") or "")
        for entry in (knowledge.get("jobEvidence") or {}).get(job["id"], [])
    )
    return JOB_PROFILE_PROMPT.format(
        name=job["name"], structured=_build_job_context(job, knowledge), context=context[:6000],
    )


def generate_job_profile(job: dict[str, Any], k: dict[str, Any]) -> dict[str, Any] | None:
    """用当前候选的原始 JD 与结构化信息生成画像；失败时不拼装模板。"""
    credentials = settings.system_llm_credentials()
    prompt = _build_profile_prompt(job, k)
    data = generate_json(prompt, system="你是严谨的岗位研究专家。", credentials=credentials)
    if not isinstance(data, dict):
        return None
    return _parse_job_profile(data)


def _parse_job_profile(data: dict[str, Any]) -> dict[str, Any]:
    """只把 LLM 输出里的合法字段转成标准结构；LLM 未给的字段留空，绝不填模板。"""

    def strl(v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        return [x for x in v if isinstance(x, str) and x.strip()]

    def strs(v: Any) -> str:
        return v.strip() if isinstance(v, str) else ""

    def dicts(v: Any) -> list[dict[str, Any]]:
        if not isinstance(v, list):
            return []
        return [x for x in v if isinstance(x, dict)]

    def named(v: Any) -> list[dict[str, Any]]:
        return [
            {"name": x.get("name", "").strip(), "desc": str(x.get("desc") or "").strip()}
            for x in dicts(v)
            if isinstance(x.get("name"), str) and x.get("name", "").strip()
        ]

    req = data.get("requirements") if isinstance(data.get("requirements"), dict) else {}
    extra = [
        {"label": str(x.get("label") or "").strip(), "value": str(x.get("value") or "").strip()}
        for x in dicts(req.get("extra"))
        if str(x.get("label") or "").strip() and str(x.get("value") or "").strip()
    ]
    skills = data.get("skills") if isinstance(data.get("skills"), dict) else {}
    return {
        "overview": strs(data.get("overview")),
        "duties": strl(data.get("duties"))[:6],
        "scenarios": named(data.get("scenarios"))[:4],
        "requirements": {
            "education": strs(req.get("education")),
            "experience": strs(req.get("experience")),
            "extra": extra,
        },
        "skills": {
            lv: named(skills.get(lv))[:5]
            for lv in ("junior", "mid", "senior")
        },
        "softSkills": named(data.get("softSkills"))[:5],
        "careerPath": [
            {
                "stage": str(x.get("stage") or "").strip(),
                "title": str(x.get("title") or "").strip(),
                "desc": str(x.get("desc") or "").strip(),
            }
            for x in dicts(data.get("careerPath"))
            if isinstance(x.get("title"), str) and x.get("title", "").strip()
        ][:4],
        "salaryReference": strs(data.get("salaryReference")),
        "industryOutlook": strs(data.get("industryOutlook")),
    }
def _enrich_one(job: dict[str, Any], k: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    try:
        return job["id"], generate_job_profile(job, k)
    except LLMNotConfigured:
        raise
    except Exception as error:
        logger.warning("岗位画像生成失败 %s: %s", job.get("name"), error)
        return job["id"], None


def _profile_input(job: dict[str, Any], knowledge: dict[str, Any]) -> str:
    data = {
        "prompt": _build_profile_prompt(job, knowledge),
        "model": config.LLM_MODEL,
        "baseUrl": config.LLM_BASE_URL,
    }
    return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _valid_profile(profile: Any) -> bool:
    return (isinstance(profile, dict) and bool(profile.get("overview")) and bool(profile.get("duties"))
            and any((profile.get("skills") or {}).get(level) for level in ("junior", "mid", "senior")))


def enrich_knowledge(k: dict[str, Any], previous: dict[str, Any] | None = None, workers: int = 4,
                     progress: Callable[[str, int], None] | None = None) -> tuple[dict[str, Any], list[str]]:
    """只改内存候选；跳过失败新岗，保留旧完整真实岗位，统一重建图谱。"""
    from .ingest import build_graph

    jobs = k.get("jobs") or []
    previous = previous or {}
    old_profiles = previous.get("jobProfiles") or {}
    old_inputs = (previous.get("meta") or {}).get("profileInputs") or {}
    inputs = {job["id"]: _profile_input(job, k) for job in jobs}
    profiles = {}
    for job in jobs:
        jid = job["id"]
        if old_inputs.get(jid) == inputs[jid] and _valid_profile(old_profiles.get(jid)):
            profiles[jid] = copy.deepcopy(old_profiles[jid])
    todo = [job for job in jobs if job["id"] not in profiles]
    failed = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_enrich_one, job, k): job for job in todo}
        for done, future in enumerate(as_completed(futures), 1):
            jid, result = future.result()
            if _valid_profile(result):
                profiles[jid] = result
            else:
                failed.append(futures[future]["name"])
            if progress:
                progress("岗位画像富化", int(done / max(1, len(todo)) * 100))
    jobs = [job for job in jobs if job["id"] in profiles]
    mapping_fields = ("jobIntro", "jobRequirements", "jobSkillProgression", "jobEvidence", "jobDetailNotes")
    accepted_ids = {job["id"] for job in jobs}
    for field in mapping_fields:
        k[field] = {jid: value for jid, value in (k.get(field) or {}).items() if jid in accepted_ids}
    accepted_evidence = {
        (evidence.get("source"), evidence.get("url"))
        for job in jobs for evidence in (job.get("evidence") or [])
        if evidence.get("source") and evidence.get("url")
    }
    # 模型故障不应删除已发布的真实岗位
    for old_job in previous.get("jobs") or []:
        jid = old_job["id"]
        if jid in accepted_ids or not (old_job.get("evidence") or (previous.get("meta") or {}).get("mode") == "real"):
            continue
        old_evidence = old_job.get("evidence") or (previous.get("jobEvidence") or {}).get(jid) or []
        # 身份不明或仍有失败证据时保留旧岗位
        if old_evidence and all(
            (evidence.get("source"), evidence.get("url")) in accepted_evidence
            for evidence in old_evidence
        ):
            continue
        if not _valid_profile(old_profiles.get(jid)):
            raise RuntimeError("上一版真实岗位缺少完整画像，停止发布以保留原数据")
        jobs.append(copy.deepcopy(old_job))
        accepted_ids.add(jid)
        profiles[jid] = copy.deepcopy(old_profiles[jid])
        inputs[jid] = old_inputs.get(jid) or _profile_input(old_job, previous)
        for field in mapping_fields:
            if jid in (previous.get(field) or {}):
                k[field][jid] = copy.deepcopy(previous[field][jid])
    k["jobs"] = jobs
    k["discoveryLog"] = [entry for entry in k.get("discoveryLog") or [] if entry.get("jobId") in accepted_ids]
    for job in jobs:
        jid = job["id"]
        profile = profiles[jid]
        k.setdefault("jobIntro", {})[jid] = {"duties": profile.get("duties") or [], "scenarios": profile.get("scenarios") or []}
        req = profile.get("requirements") or {}
        extracted_req = (k.get("jobRequirements") or {}).get(jid) or {}
        requirements = {
            "education": req.get("education") or extracted_req.get("education") or "",
            "experience": req.get("experience") or extracted_req.get("experience") or "",
            "extra": req.get("extra") or extracted_req.get("extra") or [],
        }
        # 富化结果不能覆盖已抽取的任职要求
        profile["requirements"] = copy.deepcopy(requirements)
        k.setdefault("jobRequirements", {})[jid] = requirements
        skills = profile.get("skills") or {}
        observed = job.get("observedSkills")
        observed_names = {name.strip().casefold() for name in observed} if isinstance(observed, list) else None
        for level in ("junior", "mid", "senior"):
            for skill in skills.get(level) or []:
                skill["evidenceKind"] = (
                    "unverified" if observed_names is None else
                    "observed" if skill["name"].strip().casefold() in observed_names else "inferred"
                )
        levels = {level: [{"name": skill["name"], "stack": _infer_stack(skill["name"]), "desc": skill.get("desc") or "",
                          "evidenceKind": skill["evidenceKind"]}
                           for skill in skills.get(level) or [] if isinstance(skill, dict) and skill.get("name")]
                  for level in ("junior", "mid", "senior")}
        k.setdefault("jobSkillProgression", {})[jid] = levels
        names = list(dict.fromkeys(skill["name"] for level in levels.values() for skill in level))
        job.update(description=profile["overview"], skills=names, tags=names[:3],
                   skillEvidence={skill["name"]: skill["evidenceKind"] for level in levels.values() for skill in level})
    k["jobProfiles"] = profiles
    must_bonus = {job["id"]: (
        [skill["name"] for level in ("junior", "mid") for skill in k["jobSkillProgression"][job["id"]][level]],
        [skill["name"] for skill in k["jobSkillProgression"][job["id"]]["senior"]]) for job in jobs}
    k["graph"] = build_graph(jobs, must_bonus)
    k["meta"] = {**(k.get("meta") or {}), "jobCount": len(jobs), "enriched": True,
                 "skillEvidenceVersion": 1,
                 "jobProfiles": len(profiles), "profileInputs": {jid: value for jid, value in inputs.items() if jid in accepted_ids}}
    if progress:
        progress("岗位画像富化", 100)
    return k, failed


def enrich_snapshot(reindex: bool = True, workers: int = 4,
                    progress: Callable[[str, int], None] | None = None) -> tuple[dict[str, Any], list[str]]:
    """兼容手动富化入口，仍按完整候选和版本化向量一次发布。"""
    from .ingest import publish_knowledge
    previous = store.load_latest_snapshot() or {}
    candidate, failed = enrich_knowledge(copy.deepcopy(previous), previous, workers, progress)
    if failed:
        raise RuntimeError("岗位画像不完整，未发布：" + "、".join(failed))
    if candidate.get("jobs"):
        if not reindex:
            raise ValueError("画像改变后必须同步准备向量索引")
        publish_knowledge(candidate)
    return candidate, failed

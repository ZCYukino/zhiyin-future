"""个人能力画像：后端 LLM 生成（真实 AI，无规则降级）。

对齐前端 AbilityProfile 结构：简历事实驱动，聚焦「技能达标度 / 学历 / 经验 /
项目含金量 / 证书获奖」，每一项都基于简历内部证据，可溯源、可落地。
"""
from __future__ import annotations

import json
import re
from typing import Any

from . import settings
from .llm import LLMNotConfigured, generate_json
from .prompts import ABILITY_PROFILE_PROMPT

# 画像 LLM 单次超时（秒）：失败返回 None（由路由转 502），保证响应有硬上限。
PROFILE_LLM_TIMEOUT = 45.0


def _split_items(text: str) -> list[str]:
    return [c.strip() for c in re.split(r"[，,;；、/\s]+", text or "") if c.strip()]


def _parse_projects(text: str) -> list[dict[str, Any]]:
    """解析 projects 字段（JSON 字符串）→ [{name, signals}]；兼容普通文本退化。"""
    if not text:
        return []
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return [{"name": s, "signals": []} for s in _split_items(text)][:8]
    if not isinstance(data, list):
        return []
    out: list[dict[str, Any]] = []
    for p in data:
        if isinstance(p, dict):
            name = str(p.get("name") or "项目").strip() or "项目"
            signals = p.get("signals") if isinstance(p.get("signals"), list) else []
            signals = [str(s) for s in signals if isinstance(s, str) and s.strip()]
            out.append({"name": name, "signals": signals})
        elif isinstance(p, str) and p.strip():
            out.append({"name": p.strip(), "signals": []})
    return out[:8]


def _parse_evidence(text: str) -> dict[str, str]:
    if not text:
        return {}
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items()}


def _validate(data: dict[str, Any]) -> dict[str, Any] | None:
    """只校验 LLM 输出的结构/类型/范围，不回填任何规则值。

    任一必需字段缺失或非法 → 返回 None（整份画像作废），宁可明确失败也不拼装。
    列表字段必须是 list（可为空——"无证书/无获奖"是合法输出），元素过滤非字符串。
    """

    def strl(v: Any) -> list[str] | None:
        if not isinstance(v, list):
            return None
        return [x for x in v if isinstance(x, str) and x.strip()][:8]

    def strs(v: Any) -> str | None:
        return v if isinstance(v, str) and v.strip() else None

    def num(v: Any, lo: int, hi: int) -> int | None:
        try:
            n = int(v)
        except (TypeError, ValueError):
            return None
        return n if lo <= n <= hi else None

    overall = num(data.get("overallScore"), 0, 100)
    level = data.get("competitivenessLevel")
    if overall is None or level not in ("竞争力强", "竞争力较强", "竞争力中等", "有待提升"):
        return None

    sa = data.get("skillAssessment") if isinstance(data.get("skillAssessment"), dict) else {}
    sa_mastered = strl(sa.get("mastered"))
    sa_listed = strl(sa.get("listed"))
    sa_missing = strl(sa.get("missing"))
    if sa_mastered is None or sa_listed is None or sa_missing is None:
        return None

    ea = data.get("educationAssessment") if isinstance(data.get("educationAssessment"), dict) else {}
    ea_level = strs(ea.get("level"))
    ea_score = num(ea.get("score"), 0, 100)
    ea_analysis = strs(ea.get("analysis"))
    if ea_level is None or ea_score is None or ea_analysis is None:
        return None

    xa = data.get("experienceAssessment") if isinstance(data.get("experienceAssessment"), dict) else {}
    xa_years = num(xa.get("years"), 0, 100)
    xa_level = strs(xa.get("level"))
    xa_analysis = strs(xa.get("analysis"))
    if xa_years is None or xa_level is None or xa_analysis is None:
        return None

    pa = data.get("projectAssessment") if isinstance(data.get("projectAssessment"), dict) else {}
    pa_count = num(pa.get("count"), 0, 1000)
    pa_quality = strs(pa.get("quality"))
    pa_signals = strl(pa.get("signals"))
    pa_analysis = strs(pa.get("analysis"))
    if pa_count is None or pa_quality is None or pa_signals is None or pa_analysis is None:
        return None

    ca = data.get("credentialAssessment") if isinstance(data.get("credentialAssessment"), dict) else {}
    ca_certs = strl(ca.get("certificates"))
    ca_awards = strl(ca.get("awards"))
    ca_analysis = strs(ca.get("analysis"))
    if ca_certs is None or ca_awards is None or ca_analysis is None:
        return None

    strengths = strl(data.get("strengths"))
    shortcomings = strl(data.get("shortcomings"))
    improvement = strl(data.get("improvementPriority"))
    if strengths is None or shortcomings is None or improvement is None:
        return None

    return {
        "overallScore": overall,
        "competitivenessLevel": level,
        "skillAssessment": {"mastered": sa_mastered, "listed": sa_listed, "missing": sa_missing},
        "educationAssessment": {"level": ea_level, "score": ea_score, "analysis": ea_analysis},
        "experienceAssessment": {"years": xa_years, "level": xa_level, "analysis": xa_analysis},
        "projectAssessment": {"count": pa_count, "quality": pa_quality, "signals": pa_signals, "analysis": pa_analysis},
        "credentialAssessment": {"certificates": ca_certs, "awards": ca_awards, "analysis": ca_analysis},
        "strengths": strengths,
        "shortcomings": shortcomings,
        "improvementPriority": improvement,
    }


def _format_projects(projects: list[dict[str, Any]]) -> str:
    lines = []
    for p in projects:
        sig = f"（{'、'.join(p['signals']) }）" if p.get("signals") else ""
        lines.append(f"{p['name']}{sig}")
    return "；".join(lines)


def build_ability_profile(
    user: dict[str, Any],
    credentials: settings.Credentials | None = None,
) -> dict[str, Any] | None:
    """生成个人能力画像（真实 LLM，无规则降级）。

    未配置 Key → raise LLMNotConfigured（由路由转 400 引导配置）；
    LLM 失败或输出校验不过 → None（由路由转 502）。
    """
    cred = credentials or settings.llm_credentials(user)
    if not cred.configured:
        raise LLMNotConfigured("请先配置 DeepSeek API Key")
    skills = [s for s in (user.get("userSkills") or []) if isinstance(s, str)]
    evidence = _parse_evidence(user.get("skillEvidence") or "")
    mastered = [s for s in skills if evidence.get(s) == "mastered"]
    listed = [s for s in skills if evidence.get(s) != "mastered"]
    certs = _split_items(user.get("certificates") or "")
    awards = _split_items(user.get("awards") or "")
    projects = _parse_projects(user.get("projects") or "")

    prompt = ABILITY_PROFILE_PROMPT.format(
        name=user.get("name") or "候选人",
        education=user.get("education") or "未填写",
        school=user.get("school") or "未填写",
        major=user.get("major") or "未填写",
        experience=user.get("experience") or "未填写",
        years=user.get("resumeYears") or "未填写",
        mastered="、".join(mastered) or "无",
        listed="、".join(listed) or "无",
        certificates="、".join(certs) or "无",
        awards="、".join(awards) or "无",
        projects=_format_projects(projects) or "无",
        resume=user.get("resumeText") or "未提供",
    )
    data = generate_json(
        prompt, system="你是严谨的职业规划师。",
        timeout=PROFILE_LLM_TIMEOUT, max_retries=2, credentials=cred,
    )
    if not isinstance(data, dict):
        return None
    return _validate(data)

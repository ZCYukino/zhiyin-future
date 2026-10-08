"""FastAPI 在线服务：路由定义见本文件，启动后可在 /docs 查看完整接口清单。

基路径 /api/v1；读知识库快照 + RAG 实时图谱生成。
运行：cd backend && uvicorn app.server:app --reload --port 8000
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from . import auth, config, db, llm, matching, profile, settings, store
from .extract import CATEGORIES
from .llm import LLMNotConfigured, generate_json
from .prompts import JOB_PROFILE_PROMPT
from .rag import build_context

logger = logging.getLogger("server")

app = FastAPI(title="职引未来——岗位职能图谱与人岗精准适配系统", version="1.0")

app.add_middleware(
    CORSMiddleware,
    # Bearer 鉴权（非 Cookie），避免 allow_origins=["*"] + credentials 的 CORS 冲突
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 岗位画像生成缓存
_profile_cache: dict[str, dict[str, Any]] = {}


# 首次启动且无快照时，从内置种子快照载入
store.ensure_seed_snapshot()

try:
    db.init_db()
    # 内置管理员账号，用户名/密码取自 config
    db.ensure_admin(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
except Exception as e:  # noqa: BLE001
    print(f"[warn] 用户存储初始化失败，注册/登录不可用：{e}")

def load_knowledge() -> dict[str, Any]:
    """读取最新快照；写入新快照后自动失效并重载。返回的是共享对象，调用方只读。"""
    return store.load_cached_snapshot()


def _with_details(lst: list[dict[str, Any]], k: dict[str, Any]) -> list[dict[str, Any]]:
    """把 AI 生成的技能矩阵/任职要求内嵌进每个岗位对象，前端卡片可直接渲染，避免按 id 撞库。"""
    prog = k.get("jobSkillProgression", {}) or {}
    req = k.get("jobRequirements", {}) or {}
    # 返回新 dict：lst 里的 job 对象属于快照缓存，就地改会污染后续请求
    return [
        {**j, "progression": prog.get(j.get("id")), "requirements": req.get(j.get("id"))}
        for j in lst
    ]


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


def generate_job_profile(job: dict[str, Any], k: dict[str, Any]) -> dict[str, Any] | None:
    """RAG + LLM 生成岗位画像（富文本详情）；LLM 失败/非 dict 返回 None（不拼装模板内容）。

    本函数只被 enrich 后台富化调用（系统级任务），故在此显式取管理员账号的 Key，
    不做任何隐式回退。
    """
    credentials = settings.system_llm_credentials()
    context = build_context(job["name"], top_k=8)
    structured = _build_job_context(job, k)
    prompt = JOB_PROFILE_PROMPT.format(name=job["name"], structured=structured, context=context[:6000])
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


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UserUpdateRequest(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    education: str | None = None
    school: str | None = None
    major: str | None = None
    experience: str | None = None
    certificates: str | None = None
    internship: str | None = None
    userSkills: list[str] | None = None
    hasResume: bool | None = None
    resumeName: str | None = None
    resumeText: str | None = None
    resumeYears: str | None = None
    awards: str | None = None
    projects: str | None = None
    skillEvidence: str | None = None


class ChangePasswordRequest(BaseModel):
    oldPassword: str
    newPassword: str


class MatchRequest(BaseModel):
    jobId: str
    user: dict[str, Any]


class ApiKeyRequest(BaseModel):
    provider: str
    apiKey: str


# PUT / DELETE 共用一份白名单，避免校验漂移
_PROVIDERS = ("deepseek", "dashscope")


def _masked_entry(provider: str, user_id: int) -> dict[str, Any]:
    row = db.get_user_api_keys(user_id).get(provider) or {}
    key = str(row.get("apiKey") or "")
    return {
        "configured": bool(key),
        "masked": settings.mask(key),
        "updatedAt": str(row.get("updatedAt") or ""),
    }


def _current_user(authorization: str | None) -> dict[str, Any] | None:
    """从 Bearer JWT 解析当前用户：校验签名与过期后按 sub 查库。"""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization[7:].strip()
    payload = auth.decode_token(token)
    if not payload or not payload.get("sub"):
        return None
    try:
        return db.get_user_by_id(int(payload["sub"]))
    except (TypeError, ValueError):
        return None


def _require_admin(authorization: str | None) -> dict[str, Any]:
    """校验 Bearer JWT 且用户具备 admin 角色，否则抛 401/403。"""
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="无权限：仅管理员可执行此操作")
    return user


_refresh_state: dict[str, Any] = {
    "running": False,
    "stage": "idle",
    "progress": 0,
    "startedAt": None,
    "finishedAt": None,
    "error": None,
    "result": None,
}
_refresh_lock = threading.Lock()


def _rollback_partial_snapshots(previous: set[str]) -> None:
    """刷新失败时删掉本次新写入的快照，回退到上一版好快照。

    ingest 先落采集快照、enrich 再补 jobProfiles；enrich 失败后最新快照是残缺版。
    SNAPSHOT_KEEP=2，上一版仍在盘上。
    """
    written = [p for p in store.list_snapshots() if p.name not in previous]
    removed: list[str] = []
    for p in written:
        try:
            p.unlink(missing_ok=True)
            removed.append(p.name)
        except OSError as e:  # noqa: BLE001 单个文件删不掉不应掩盖原始异常
            logger.warning("删除残缺快照失败 %s：%s", p.name, e)
    if removed:
        logger.warning(
            "刷新失败，已回滚本次写入的残缺快照 %s，回退到上一版完整快照", "、".join(removed)
        )


def _run_refresh() -> None:
    """后台线程：跑一遍完整采集 + 富化管道；running 标志由路由持锁置位。"""
    from . import enrich, ingest  # 惰性导入，避免循环依赖

    # 本次运行开始前已存在的快照名，失败时据此回滚
    previous_snapshots = {p.name for p in store.list_snapshots()}

    def report(stage: str, pct: int) -> None:
        with _refresh_lock:
            _refresh_state["stage"] = stage
            _refresh_state["progress"] = max(0, min(100, int(pct)))

    try:
        # 阶段一：采集→清洗→抽取→组装→向量化→快照（0–85%）
        def ingest_progress(stage: str, pct: int) -> None:
            report(stage, int(pct * 0.85))

        k, failed_jobs = ingest.main(use_crawler=True, progress=ingest_progress)

        # 阶段二：岗位画像富化（85–100%）
        def enrich_progress(stage: str, pct: int) -> None:
            report(stage, 85 + int(pct * 0.15))

        k, failed_profiles = enrich.enrich_snapshot(reindex=True, workers=4, progress=enrich_progress)
        with _refresh_lock:
            _refresh_state["result"] = {
                "jobCount": len(k.get("jobs", []) or []),
                "profileCount": len(k.get("jobProfiles") or {}),
                "failedJobs": failed_jobs,
                "failedProfiles": failed_profiles,
            }
        report("刷新完成", 100)
    except Exception as e:  # noqa: BLE001
        _rollback_partial_snapshots(previous_snapshots)
        with _refresh_lock:
            _refresh_state["error"] = str(e)
    finally:
        # 刷新重写了画像，清空缓存避免返回旧富文本
        _profile_cache.clear()
        with _refresh_lock:
            _refresh_state["running"] = False
            _refresh_state["finishedAt"] = datetime.now().isoformat(timespec="seconds")


@app.get("/health")
def health() -> dict[str, Any]:
    k = load_knowledge()
    return {"ok": True, "jobCount": len(k.get("jobs", []) or [])}


@app.get("/api/v1/jobs")
def jobs(
    categoryId: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    newOnly: bool = Query(default=False),
    hot: bool = Query(default=False),
) -> list[dict[str, Any]]:
    k = load_knowledge()
    lst = list(k.get("jobs", []) or [])
    if categoryId:
        lst = [j for j in lst if j.get("categoryId") == categoryId]
    if newOnly:
        lst = [j for j in lst if j.get("isNew")]
    if keyword:
        kw = keyword.strip().lower()
        if kw:
            lst = [
                j
                for j in lst
                if kw in (j.get("name", "").lower())
                or kw in (j.get("description", "").lower())
                or any(kw in s.lower() for s in (j.get("skills", []) or []))
                or any(kw in t.lower() for t in (j.get("tags", []) or []))
            ]
    if hot:
        lst = sorted(lst, key=lambda j: j.get("hotScore") or 0, reverse=True)[:10]
    return _with_details(lst, k)


@app.get("/api/v1/jobs/hot")
def jobs_hot() -> list[dict[str, Any]]:
    k = load_knowledge()
    lst = list(k.get("jobs", []) or [])
    return _with_details(sorted(lst, key=lambda j: j.get("hotScore") or 0, reverse=True)[:10], k)


@app.get("/api/v1/jobs/featured")
def jobs_featured() -> list[dict[str, Any]]:
    """岗位介绍页精选：最热门 30 条（含 5 条新兴），整体按热门程度降序。"""
    k = load_knowledge()
    lst = sorted(k.get("jobs", []) or [], key=lambda j: j.get("hotScore") or 0, reverse=True)
    new_jobs = [j for j in lst if j.get("isNew")][:5]
    hot_jobs = [j for j in lst if not j.get("isNew")][: 30 - len(new_jobs)]
    featured = sorted(new_jobs + hot_jobs, key=lambda j: j.get("hotScore") or 0, reverse=True)
    return _with_details(featured, k)


@app.get("/api/v1/jobs/{job_id}")
def job_detail(job_id: str) -> dict[str, Any]:
    k = load_knowledge()
    job = next((j for j in (k.get("jobs", []) or []) if j.get("id") == job_id), None)
    if not job:
        raise HTTPException(status_code=404, detail="未找到目标岗位")
    graph = k.get("graph", {}) or {}
    job_node = next(
        (n for n in (graph.get("nodes", []) or []) if n.get("jobId") == job_id or n.get("id") == f"job-{job_id}"),
        None,
    )
    changes = [c for c in (k.get("capabilityChanges", []) or []) if c.get("jobId") == job_id]
    return {
        "job": job,
        "intro": (k.get("jobIntro") or {}).get(job_id),
        "requirements": (k.get("jobRequirements") or {}).get(job_id),
        "progression": (k.get("jobSkillProgression") or {}).get(job_id),
        "graphNodeId": job_node["id"] if job_node else None,
        "graphNode": job_node,
        "evolution": changes,
        "adjacentJobs": [],
        "discovered": (
            {"source": job.get("source"), "confidence": job.get("confidence"), "discoveredDate": job.get("discoveredDate")}
            if job.get("isNew")
            else None
        ),
    }


@app.get("/api/v1/graph")
def graph() -> dict[str, Any]:
    return load_knowledge().get("graph", {"nodes": [], "edges": []})


@app.get("/api/v1/capability-changes")
def capability_changes(jobId: str | None = Query(default=None)) -> list[dict[str, Any]]:
    k = load_knowledge()
    lst = k.get("capabilityChanges", []) or []
    if jobId:
        lst = [c for c in lst if c.get("jobId") == jobId]
    return lst


@app.get("/api/v1/discoveries")
def discoveries() -> list[dict[str, Any]]:
    k = load_knowledge()
    logs = k.get("discoveryLog", []) or []
    if logs:
        return logs
    # 降级：从 isNew 岗位派生
    out: list[dict[str, Any]] = []
    for j in (k.get("jobs", []) or []):
        if j.get("isNew"):
            out.append(
                {
                    "date": j.get("discoveredDate", ""),
                    "jobName": j.get("name"),
                    "jobId": j.get("id"),
                    "source": j.get("source", "多源数据挖掘"),
                    "confidence": j.get("confidence", 0.7),
                    "description": j.get("description", ""),
                }
            )
    return out


@app.post("/api/v1/auth/register")
def auth_register(body: RegisterRequest) -> dict[str, Any]:
    username = body.username.strip()
    password = body.password
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="密码至少 6 位")
    # 管理员用户名保留，create_user 里还有一道同样的闸
    if db.is_reserved_username(username):
        raise HTTPException(status_code=400, detail="该用户名为系统保留，不可注册")
    user = db.create_user(username, password)
    if not user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    token = auth.create_token(int(user["id"]), user["username"])
    return {"token": token, "user": user}


@app.post("/api/v1/auth/login")
def auth_login(body: LoginRequest) -> dict[str, Any]:
    user = db.authenticate(body.username.strip(), body.password)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = auth.create_token(int(user["id"]), user["username"])
    return {"token": token, "user": user}


@app.get("/api/v1/auth/me")
def auth_me(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    return user


@app.put("/api/v1/auth/me")
def auth_update(body: UserUpdateRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    fields = body.model_dump(exclude_none=True)
    updated = db.update_user(int(user["id"]), fields)
    return updated or user


@app.post("/api/v1/auth/change-password")
def auth_change_password(body: ChangePasswordRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    if len(body.newPassword) < 6:
        raise HTTPException(status_code=400, detail="新密码至少 6 位")
    if not db.change_password(int(user["id"]), body.oldPassword, body.newPassword):
        raise HTTPException(status_code=400, detail="原密码错误")
    return {"ok": True}


@app.get("/api/v1/apikey")
def apikey_get(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """当前账号的 Key 状态（只回显脱敏值）；普通用户只见 deepseek，管理员见两者。"""
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    data: dict[str, Any] = {"deepseek": _masked_entry("deepseek", int(user["id"]))}
    if user.get("role") == "admin":
        data["dashscope"] = _masked_entry("dashscope", int(user["id"]))
    data["effective"] = {
        "llmBaseUrl": config.LLM_BASE_URL,
        "llmModel": config.LLM_MODEL,
        "embeddingModel": config.EMBEDDING_MODEL,
    }
    return data


@app.put("/api/v1/apikey")
def apikey_put(body: ApiKeyRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """保存 Key：先校验可用性（deepseek 最小对话 / dashscope 最短向量化），失败拒绝保存。"""
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    if body.provider not in _PROVIDERS:
        raise HTTPException(status_code=400, detail="不支持的 provider")
    if body.provider == "dashscope" and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    key = body.apiKey.strip()
    if not key.startswith("sk-") or len(key) < 16:
        raise HTTPException(status_code=400, detail="Key 格式不正确")
    err = llm.verify_api_key(body.provider, key)
    if err:
        raise HTTPException(status_code=400, detail=err)
    db.set_user_api_key(int(user["id"]), body.provider, key)
    return {"ok": True, **{body.provider: _masked_entry(body.provider, int(user["id"]))}}


@app.delete("/api/v1/apikey")
def apikey_delete(authorization: str | None = Header(default=None), provider: str = "deepseek") -> dict[str, Any]:
    """清除该账号的 Key（换 Key / 配错时用）。"""
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    # 与 PUT 同一份白名单
    if provider not in _PROVIDERS:
        raise HTTPException(status_code=400, detail="不支持的 provider")
    if provider == "dashscope" and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    db.delete_user_api_key(int(user["id"]), provider)
    return {"ok": True}


@app.post("/api/v1/profile/analyze")
def profile_analyze(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """基于当前用户资料生成个人能力画像，生成后持久化。"""
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    try:
        result = profile.build_ability_profile(user)
    except LLMNotConfigured:
        raise HTTPException(status_code=400, detail="请先配置 DeepSeek API Key")
    if result is None:
        raise HTTPException(status_code=502, detail="画像生成失败，请稍后重试")
    try:
        db.save_ability_profile(int(user["id"]), result)
    except Exception as e:  # noqa: BLE001
        print(f"[warn] 能力画像持久化失败：{e}")
    return result


@app.get("/api/v1/profile")
def profile_get(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    """返回该用户上次生成并持久化的能力画像；未生成过返回 null。"""
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    return db.get_ability_profile(int(user["id"]))


@app.delete("/api/v1/profile")
def profile_clear(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """删除已持久化的能力画像（上传新简历后旧画像失效）。"""
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    db.save_ability_profile(int(user["id"]), None)
    return {"ok": True}


@app.post("/api/v1/matching/analyze")
def matching_analyze(body: MatchRequest, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    # 凭据按鉴权 token 的用户解析；未登录则 llmStatus=no_api_key
    au = _current_user(authorization)
    credentials = settings.llm_credentials(au)
    report = matching.build_match_report(body.jobId, body.user, credentials=credentials)
    if report is None:
        raise HTTPException(status_code=404, detail="未找到目标岗位")
    # 仅当已登录才持久化；不信任 body.user.id（可伪造）
    if au is not None:
        try:
            db.save_match_report(int(au["id"]), {"jobId": body.jobId, "report": report})
        except Exception as e:  # noqa: BLE001
            print(f"[warn] 匹配报告持久化失败：{e}")
    return report


@app.get("/api/v1/matching/report")
def matching_report_get(authorization: str | None = Header(default=None)) -> dict[str, Any] | None:
    """返回该用户上次生成并持久化的匹配报告（含 jobId）；未生成过返回 null。"""
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    return db.get_match_report(int(user["id"]))


@app.delete("/api/v1/matching/report")
def matching_report_clear(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """删除已持久化的匹配报告（上传新简历后旧报告失效）。"""
    user = _current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    db.save_match_report(int(user["id"]), None)
    return {"ok": True}


@app.get("/api/v1/jobs/{job_id}/profile")
def job_profile(job_id: str) -> dict[str, Any]:
    """岗位画像（详情页富文本）：只读快照预生成结果；快照缺失返回 404（不再实时调 LLM）。"""
    if job_id in _profile_cache:
        return _profile_cache[job_id]
    k = load_knowledge()
    # 快照含预生成画像，直接返回
    profiles = k.get("jobProfiles") or {}
    if job_id in profiles:
        _profile_cache[job_id] = profiles[job_id]
        return profiles[job_id]
    raise HTTPException(status_code=404, detail="该岗位暂无画像")


@app.post("/api/v1/admin/refresh")
def admin_refresh(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    """触发一次完整数据刷新（采集 + 富化），在后台线程执行。"""
    _require_admin(authorization)
    # 预检与后台任务用同一套（系统级）凭据解析，多管理员并存时才不会中途失败
    missing: list[str] = []
    if not settings.system_llm_credentials().configured:
        missing.append("DeepSeek API Key")
    if not settings.embed_credentials().configured:
        missing.append("阿里云百炼 API Key")
    if missing:
        raise HTTPException(status_code=400, detail=f"请先在下方配置 {'、'.join(missing)} 后再刷新")
    # check-and-set 必须在同一把锁内完成
    with _refresh_lock:
        if _refresh_state["running"]:
            raise HTTPException(status_code=409, detail="数据刷新已在进行中")
        _refresh_state.update(
            running=True,
            stage="初始化",
            progress=0,
            startedAt=datetime.now().isoformat(timespec="seconds"),
            finishedAt=None,
            error=None,
            result=None,
        )
    try:
        threading.Thread(target=_run_refresh, daemon=True).start()
    except Exception:  # noqa: BLE001 线程起不来就把 running 复位
        with _refresh_lock:
            _refresh_state["running"] = False
        raise
    return {"ok": True, "message": "数据刷新已启动"}


@app.get("/api/v1/admin/refresh/status")
def admin_refresh_status(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _require_admin(authorization)
    with _refresh_lock:
        return dict(_refresh_state)


# 单容器部署：backend/dist 存在时托管前端构建产物（hash 路由，html=True 回退）
_dist = config.BACKEND_ROOT / "dist"
if _dist.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_dist), html=True), name="spa")

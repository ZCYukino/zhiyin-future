"""FastAPI 在线服务：路由定义见本文件，启动后可在 /docs 查看完整接口清单。"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from typing import Annotated, Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from . import auth, config, db, llm, matching, profile, settings, store
from .llm import LLMNotConfigured

logger = logging.getLogger("server")
SkillText = Annotated[str, StringConstraints(max_length=160)]

app = FastAPI(title="职引未来——岗位职能图谱与人岗精准适配系统", version="1.0")

app.add_middleware(
    CORSMiddleware,
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
    """把技能矩阵与任职要求内嵌进每个岗位对象，前端卡片可直接渲染，避免按 id 撞库。"""
    prog = k.get("jobSkillProgression", {}) or {}
    req = k.get("jobRequirements", {}) or {}
    # 返回新 dict：lst 里的 job 对象属于快照缓存，就地改会污染后续请求
    return [
        {**j, "progression": prog.get(j.get("id")), "requirements": req.get(j.get("id"))}
        for j in lst
    ]


class RegisterRequest(BaseModel):
    username: str = Field(max_length=128)
    password: str = Field(max_length=1024)


class LoginRequest(BaseModel):
    username: str = Field(max_length=128)
    password: str = Field(max_length=1024)


class UserUpdateRequest(BaseModel):
    model_config = ConfigDict(str_max_length=5000)
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    education: str | None = None
    school: str | None = None
    major: str | None = None
    experience: str | None = None
    certificates: str | None = None
    internship: str | None = None
    userSkills: list[SkillText] | None = Field(default=None, max_length=200)
    hasResume: bool | None = None
    resumeName: str | None = None
    resumeText: str | None = Field(default=None, max_length=100000)
    resumeYears: str | None = None
    awards: str | None = None
    projects: str | None = Field(default=None, max_length=20000)
    skillEvidence: str | None = Field(default=None, max_length=20000)


class ChangePasswordRequest(BaseModel):
    oldPassword: str = Field(max_length=1024)
    newPassword: str = Field(max_length=1024)


class MatchUserRequest(BaseModel):
    model_config = ConfigDict(str_max_length=5000)
    userSkills: list[SkillText] = Field(default_factory=list, max_length=200)
    resumeText: str | None = Field(default=None, max_length=100000)
    education: str | None = None
    major: str | None = None
    resumeYears: str | None = None
    experience: str | None = None


class MatchRequest(BaseModel):
    jobId: str = Field(max_length=128)
    user: MatchUserRequest


class ApiKeyRequest(BaseModel):
    provider: str = Field(max_length=32)
    apiKey: str = Field(max_length=512)


# PUT / DELETE 共用白名单
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
        user_id = int(payload["sub"])
        user = db.get_user_by_id(user_id)
        if not user or payload["ver"] != db.get_token_version(user_id):
            return None
        return user
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
    """兼容旧调用；刷新现在只在所有候选准备成功后提交，失败不再删除活动数据。"""
    return None


def _run_refresh() -> None:
    """后台执行一次完整候选构建；ingest 内只有一个最终发布点。"""
    from . import ingest

    def report(stage: str, pct: int) -> None:
        with _refresh_lock:
            _refresh_state["stage"] = stage
            _refresh_state["progress"] = max(0, min(100, int(pct)))

    try:
        knowledge, failed_jobs = ingest.main(use_crawler=True, progress=report)
        with _refresh_lock:
            _refresh_state["result"] = {
                "jobCount": len(knowledge.get("jobs") or []),
                "profileCount": len(knowledge.get("jobProfiles") or {}),
                "failedJobs": failed_jobs,
                "failedProfiles": (knowledge.get("meta") or {}).get("failedProfiles") or [],
                **((knowledge.get("meta") or {}).get("crawlStats") or {}),
            }
        report("刷新完成", 100)
    except Exception as error:
        logger.exception("数据刷新失败，继续提供上一版完整数据")
        with _refresh_lock:
            _refresh_state["error"] = str(error)
    finally:
        _profile_cache.clear()
        with _refresh_lock:
            _refresh_state["running"] = False
            _refresh_state["finishedAt"] = datetime.now().isoformat(timespec="seconds")


@app.get("/health")
def health() -> dict[str, Any]:
    k = load_knowledge()
    return {"ok": True, "jobCount": len(k.get("jobs", []) or [])}


@app.get("/api/v1/data-status")
def data_status() -> dict[str, Any]:
    """公开已发布快照的数据性质；历史的 crawler 标签不能证明真实采集。"""
    knowledge = load_knowledge()
    meta = knowledge.get("meta") or {}
    mode = meta.get("mode")
    if mode not in ("real", "demo"):
        mode = "demo" if meta.get("source") == "seed" else "unknown"
    return {
        "mode": mode,
        "jobCount": len(knowledge.get("jobs") or []),
        "archiveCount": (meta.get("crawlStats") or {}).get("archiveCount"),
        "capabilityChangesKind": meta.get("capabilityChangesKind") or ("demo" if mode == "demo" else "unknown"),
    }


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
    token = auth.create_token(int(user["id"]), user["username"], token_version=0)
    return {"token": token, "user": user}


@app.post("/api/v1/auth/login")
def auth_login(body: LoginRequest) -> dict[str, Any]:
    authenticated = db.authenticate_with_token_version(body.username.strip(), body.password)
    if authenticated is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    user = authenticated.user
    token = auth.create_token(int(user["id"]), user["username"], token_version=authenticated.token_version)
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
        saved = db.save_ability_profile(int(user["id"]), result, expected_revision=user["analysisRevision"])
    except Exception as e:  # noqa: BLE001
        logger.warning("能力画像持久化失败：%s", e)
        raise HTTPException(status_code=503, detail="画像保存失败，请稍后重试") from e
    if not saved:
        raise HTTPException(status_code=409, detail="个人资料已更新，请重新生成画像")
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
    if authorization is not None and au is None:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")
    credentials = settings.llm_credentials(au)
    analysis_user = au if au is not None else body.user.model_dump()
    report = matching.build_match_report(body.jobId, analysis_user, credentials=credentials)
    if report is None:
        raise HTTPException(status_code=404, detail="未找到目标岗位")
    # 仅当已登录才持久化；不信任 body.user.id（可伪造）
    if au is not None:
        try:
            saved = db.save_match_report(
                int(au["id"]), {"jobId": body.jobId, "report": report},
                expected_revision=au["analysisRevision"],
            )
        except Exception as e:  # noqa: BLE001
            logger.warning("匹配报告持久化失败：%s", e)
            raise HTTPException(status_code=503, detail="匹配报告保存失败，请稍后重试") from e
        if not saved:
            raise HTTPException(status_code=409, detail="个人资料已更新，请重新生成匹配报告")
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
    k = load_knowledge()
    # 快照含预生成画像，直接返回
    profiles = k.get("jobProfiles") or {}
    if job_id in profiles:
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


for _candidate in [os.environ.get("FRONTEND_DIR"), "dist", "webapp"]:
    if not _candidate:
        continue
    _dist = config.BACKEND_ROOT / _candidate
    if _dist.is_dir():
        from fastapi.staticfiles import StaticFiles

        app.mount("/", StaticFiles(directory=str(_dist), html=True), name="spa")
        break

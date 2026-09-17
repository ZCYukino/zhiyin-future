"""apikey 接口单元测试：权限、脱敏、无明文回显、未配 Key 拦截刷新、匹配报告的零相交凭据。"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app import auth, config, db, llm, server, store


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test-users.db"))
    db.init_db()
    db.ensure_admin(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)


def _auth_for(user: dict) -> str:
    return f"Bearer {auth.create_token(int(user['id']), user['username'])}"


def _mk_user(name: str) -> dict:
    u = db.create_user(name, "123456")
    assert u is not None
    return u


def _admin() -> dict:
    u = db.authenticate(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
    assert u is not None
    return u


def test_apikey_requires_login():
    with pytest.raises(HTTPException) as ei:
        server.apikey_get(None)
    assert ei.value.status_code == 401


def test_user_save_and_mask_no_plaintext(tmp_db, monkeypatch):
    monkeypatch.setattr(llm, "verify_api_key", lambda p, k: None)
    u = _mk_user("alice")
    authz = _auth_for(u)
    server.apikey_put(server.ApiKeyRequest(provider="deepseek", apiKey="sk-test1234567890abcd"), authz)
    data = server.apikey_get(authz)
    assert set(data.keys()) == {"deepseek", "effective"}
    assert data["deepseek"]["configured"] is True
    assert data["deepseek"]["masked"] == "sk-tes****abcd"
    assert "dashscope" not in data
    assert "sk-test1234567890abcd" not in repr(data)


def test_user_dashscope_forbidden(tmp_db, monkeypatch):
    monkeypatch.setattr(llm, "verify_api_key", lambda p, k: None)
    u = _mk_user("alice")
    with pytest.raises(HTTPException) as ei:
        server.apikey_put(server.ApiKeyRequest(provider="dashscope", apiKey="sk-test1234567890abcd"), _auth_for(u))
    assert ei.value.status_code == 403


def test_admin_can_save_both(tmp_db, monkeypatch):
    monkeypatch.setattr(llm, "verify_api_key", lambda p, k: None)
    admin = _admin()
    authz = _auth_for(admin)
    server.apikey_put(server.ApiKeyRequest(provider="deepseek", apiKey="sk-a111111111111111"), authz)
    server.apikey_put(server.ApiKeyRequest(provider="dashscope", apiKey="sk-ws-abcdefghijklmnop"), authz)
    data = server.apikey_get(authz)
    assert set(data.keys()) == {"deepseek", "dashscope", "effective"}
    assert data["deepseek"]["configured"] and data["dashscope"]["configured"]
    assert "llmModel" in data["effective"]


def test_invalid_key_format(tmp_db, monkeypatch):
    monkeypatch.setattr(llm, "verify_api_key", lambda p, k: None)
    u = _mk_user("alice")
    with pytest.raises(HTTPException) as ei:
        server.apikey_put(server.ApiKeyRequest(provider="deepseek", apiKey="not-a-key"), _auth_for(u))
    assert ei.value.status_code == 400


def test_verify_failure_rejected(tmp_db, monkeypatch):
    monkeypatch.setattr(llm, "verify_api_key", lambda p, k: "Key 无效或已被删除（认证失败）")
    u = _mk_user("alice")
    authz = _auth_for(u)
    with pytest.raises(HTTPException) as ei:
        server.apikey_put(server.ApiKeyRequest(provider="deepseek", apiKey="sk-test1234567890abcd"), authz)
    assert ei.value.status_code == 400
    assert server.apikey_get(authz)["deepseek"]["configured"] is False


def test_delete_clears(tmp_db, monkeypatch):
    monkeypatch.setattr(llm, "verify_api_key", lambda p, k: None)
    u = _mk_user("alice")
    authz = _auth_for(u)
    server.apikey_put(server.ApiKeyRequest(provider="deepseek", apiKey="sk-test1234567890abcd"), authz)
    server.apikey_delete(authz, "deepseek")
    assert server.apikey_get(authz)["deepseek"]["configured"] is False


def test_refresh_requires_keys(tmp_db):
    admin = _admin()
    with pytest.raises(HTTPException) as ei:
        server.admin_refresh(_auth_for(admin))
    assert ei.value.status_code == 400
    assert "DeepSeek" in ei.value.detail


# ===== DELETE 的 provider 白名单与权限（此前未断言）=====

def test_delete_unknown_provider_rejected(tmp_db):
    """未知 provider 必须 400：不能「删了个空」还回 {"ok": true} 假装成功。"""
    u = _mk_user("alice")
    with pytest.raises(HTTPException) as ei:
        server.apikey_delete(_auth_for(u), "openai")
    assert ei.value.status_code == 400
    assert "provider" in ei.value.detail


def test_delete_dashscope_forbidden_for_normal_user(tmp_db):
    u = _mk_user("alice")
    with pytest.raises(HTTPException) as ei:
        server.apikey_delete(_auth_for(u), "dashscope")
    assert ei.value.status_code == 403


# ===== PUT 响应体同样不得回显明文 Key（此前只断言了 GET 路径）=====

def test_put_response_has_no_plaintext_key(tmp_db, monkeypatch):
    monkeypatch.setattr(llm, "verify_api_key", lambda p, k: None)
    u = _mk_user("alice")
    plaintext = "sk-test1234567890abcd"

    resp = server.apikey_put(
        server.ApiKeyRequest(provider="deepseek", apiKey=plaintext), _auth_for(u)
    )

    assert set(resp.keys()) == {"ok", "deepseek"}
    assert resp["ok"] is True
    assert set(resp["deepseek"].keys()) == {"configured", "masked", "updatedAt"}
    assert resp["deepseek"]["configured"] is True
    assert resp["deepseek"]["masked"] == "sk-tes****abcd"
    assert plaintext not in repr(resp)


# ===== 管理员刷新：普通用户 403（_require_admin 的分支此前无覆盖）=====

def test_admin_refresh_forbidden_for_normal_user(tmp_db):
    u = _mk_user("alice")
    authz = _auth_for(u)

    with pytest.raises(HTTPException) as ei:
        server.admin_refresh(authz)
    assert ei.value.status_code == 403

    with pytest.raises(HTTPException) as ei2:
        server.admin_refresh_status(authz)
    assert ei2.value.status_code == 403

    # 被拒的请求不得留下任何刷新状态副作用
    assert server._refresh_state["running"] is False


# ===== 零相交：匹配报告一律按「鉴权 token 的用户」解析凭据 =====

def _first_job_id() -> str:
    """取种子快照中的真实岗位 id（app.server 导入时 ensure_seed_snapshot 已落盘）。"""
    snapshot = store.load_latest_snapshot() or {}
    jobs = snapshot.get("jobs") or []
    assert jobs, "缺少种子快照，无法构造匹配请求"
    return str(jobs[0]["id"])


def _capture_plan(seen: list[str]):
    """打桩 LLM 调用本身，只记录实际拿到的 api_key（避免真实网络请求）。"""
    def _plan(job_name, mastered, partial, missing, credentials):
        seen.append(credentials.api_key)
        return {
            "oneLineSummary": "总体匹配良好。",
            "learningPath": [{"stage": "阶段一", "steps": [{"skill": "Python", "stack": "ai"}]}],
        }
    return _plan


def test_matching_uses_caller_credentials_not_body_user(tmp_db, monkeypatch):
    """A 已登录，body.user.id 伪造成 B：必须用 A 的凭据，且报告落在 A 名下。

    凭据若从可伪造的 body.user 解析，任何人都能借别人的 Key 花钱；
    报告若按 body.user.id 落库，则能覆写他人的报告。
    """
    admin = _admin()
    db.set_user_api_key(int(admin["id"]), "deepseek", "sk-admin-key-0000000000")
    a = _mk_user("alice")
    b = _mk_user("bob")
    db.set_user_api_key(int(a["id"]), "deepseek", "sk-alice-key-1111111111")
    db.set_user_api_key(int(b["id"]), "deepseek", "sk-bob-key-2222222222")

    seen: list[str] = []
    monkeypatch.setattr(server.matching, "_llm_plan", _capture_plan(seen))

    body = server.MatchRequest(jobId=_first_job_id(), user={"id": str(b["id"]), "userSkills": []})
    report = server.matching_analyze(body, _auth_for(a))

    assert seen == ["sk-alice-key-1111111111"]  # 只有 A 的 Key 被解析到
    assert report["llmStatus"] == "ok"
    assert db.get_match_report(int(a["id"])) is not None  # 落在 A 名下
    assert db.get_match_report(int(b["id"])) is None  # 绝不动 B 的记录


def test_anonymous_matching_never_spends_admin_quota(tmp_db, monkeypatch):
    """未登录：即使管理员已配 deepseek Key，也必须 llmStatus=no_api_key 且一次 LLM 都不调。

    body.user 在这里直接伪造成管理员自己的 id —— 匿名请求没有任何可信身份，
    若按它解析凭据，任何人都能白嫖管理员的配额。
    """
    admin = _admin()
    admin_id = int(admin["id"])
    db.set_user_api_key(admin_id, "deepseek", "sk-admin-key-0000000000")

    seen: list[str] = []
    monkeypatch.setattr(server.matching, "_llm_plan", lambda *a, **k: seen.append("called"))

    body = server.MatchRequest(jobId=_first_job_id(), user={"id": str(admin_id), "userSkills": []})
    report = server.matching_analyze(body, None)

    assert report["llmStatus"] == "no_api_key"
    assert seen == []  # LLM 一次都没被调用
    assert db.get_match_report(admin_id) is None  # 匿名请求也不落库

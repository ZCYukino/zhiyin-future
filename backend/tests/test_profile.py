"""profile.py 单元测试：LLM 输出校验（只校验不回填）、未配置 Key 抛 LLMNotConfigured。"""
from __future__ import annotations

import pytest

from app import config, db, profile

VALID_PROFILE = {
    "overallScore": 78,
    "competitivenessLevel": "竞争力较强",
    "skillAssessment": {"mastered": ["Python"], "listed": ["Java"], "missing": ["Go"]},
    "educationAssessment": {"level": "本科", "score": 70, "analysis": "本科，达到基本门槛。"},
    "experienceAssessment": {"years": 2, "level": "初级", "analysis": "约 2 年经验。"},
    "projectAssessment": {"count": 1, "quality": "中", "signals": ["已上线/交付"], "analysis": "1 个项目。"},
    "credentialAssessment": {"certificates": ["软考"], "awards": [], "analysis": "证书 软考。"},
    "strengths": ["基础扎实"],
    "shortcomings": ["经验较浅"],
    "improvementPriority": ["补齐 Go"],
}


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test-users.db"))
    db.init_db()


def _user_with_key() -> dict:
    u = db.create_user("alice", "123456")
    assert u is not None
    db.set_user_api_key(int(u["id"]), "deepseek", "sk-test")
    return u


def test_validate_ok():
    assert profile._validate(VALID_PROFILE) is not None


@pytest.mark.parametrize("field,value", [
    ("overallScore", "not-a-number"),
    ("overallScore", 101),
    ("competitivenessLevel", "随便写的"),
    ("skillAssessment", {}),
    ("strengths", "not-a-list"),
])
def test_validate_rejects(field, value):
    data = dict(VALID_PROFILE)
    data[field] = value
    assert profile._validate(data) is None


def test_validate_accepts_empty_lists():
    data = dict(VALID_PROFILE)
    data["credentialAssessment"] = {"certificates": [], "awards": [], "analysis": "无证书获奖。"}
    assert profile._validate(data) is not None


def test_build_no_key_raises(tmp_db):
    u = db.create_user("alice", "123456")
    with pytest.raises(profile.LLMNotConfigured):
        profile.build_ability_profile(u)


def test_build_llm_failure_returns_none(tmp_db, monkeypatch):
    u = _user_with_key()
    monkeypatch.setattr(profile, "generate_json", lambda *a, **k: None)
    assert profile.build_ability_profile(u) is None


def test_build_invalid_output_returns_none(tmp_db, monkeypatch):
    u = _user_with_key()
    monkeypatch.setattr(profile, "generate_json", lambda *a, **k: {"overallScore": "x"})
    assert profile.build_ability_profile(u) is None


def test_build_success(tmp_db, monkeypatch):
    u = _user_with_key()
    monkeypatch.setattr(profile, "generate_json", lambda *a, **k: VALID_PROFILE)
    out = profile.build_ability_profile(u)
    assert out is not None
    assert out["overallScore"] == 78
    assert out["skillAssessment"]["mastered"] == ["Python"]

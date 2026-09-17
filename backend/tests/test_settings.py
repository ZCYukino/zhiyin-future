"""settings.py 单元测试：账号级 Key 凭据解析（零相交、无 .env 回退）。"""
from __future__ import annotations

import pytest

from app import config, db, settings
from app.config import _env


def test_env_treats_empty_as_unset(monkeypatch):
    """空值/纯空白一律按「未设置」处理，回落默认值。

    回归：.env 里写 `DB_PATH=`（冒号后留空）时 dotenv 会把变量设成空串，
    而 `os.getenv(key, default)` 拿到的是空串不是默认值 —— 照 README 里
    `copy .env.example .env` 做的用户会拿到空 DB_PATH，SQLite 落到私有临时库上，
    账号/简历/报告重启后全没。空的 `JWT_EXPIRE_HOURS=` 更直接：int("") 抛错，后端起不来。
    """
    monkeypatch.setenv("T_EMPTY", "")
    monkeypatch.setenv("T_BLANK", "   ")
    monkeypatch.setenv("T_SET", "deepseek-chat")

    assert _env("T_EMPTY", "DEF") == "DEF"
    assert _env("T_BLANK", "DEF") == "DEF"
    assert _env("T_UNSET_ANYWHERE", "DEF") == "DEF"
    # 有值时不得被默认值覆盖
    assert _env("T_SET", "DEF") == "deepseek-chat"
    # 数值型配置不再因空值崩
    assert int(_env("T_EMPTY", "24")) == 24


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    """把 SQLite 指到临时文件并建表，保证测试互不污染。"""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test-users.db"))
    db.init_db()


def _mk_user(name: str) -> dict:
    u = db.create_user(name, "123456")
    assert u is not None
    return u


def test_llm_credentials_none_user(tmp_db):
    assert settings.llm_credentials(None).configured is False


def test_llm_credentials_unconfigured(tmp_db):
    u = _mk_user("alice")
    cred = settings.llm_credentials(u)
    assert cred.configured is False
    assert cred.model == "deepseek-flash"
    assert cred.base_url == config.LLM_BASE_URL


def test_llm_credentials_configured(tmp_db):
    u = _mk_user("alice")
    db.set_user_api_key(int(u["id"]), "deepseek", "sk-test1234567890abcd")
    cred = settings.llm_credentials(u)
    assert cred.configured is True
    assert cred.api_key == "sk-test1234567890abcd"


def test_zero_crossing(tmp_db):
    a = _mk_user("alice")
    b = _mk_user("bob")
    db.set_user_api_key(int(a["id"]), "deepseek", "sk-aaa")
    assert settings.llm_credentials(b).configured is False
    assert settings.llm_credentials(a).api_key == "sk-aaa"


def test_system_llm_credentials_from_admin(tmp_db):
    db.ensure_admin(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
    admin = db.authenticate(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
    db.set_user_api_key(int(admin["id"]), "deepseek", "sk-admin-key")
    cred = settings.system_llm_credentials()
    assert cred.configured is True
    assert cred.api_key == "sk-admin-key"


def test_embed_credentials_from_admin(tmp_db):
    db.ensure_admin(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
    admin = db.authenticate(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
    db.set_user_api_key(int(admin["id"]), "dashscope", "sk-ws-xxx")
    cred = settings.embed_credentials()
    assert cred.configured is True
    assert cred.model == config.EMBEDDING_MODEL


def test_mask_boundaries():
    assert settings.mask("") == ""
    assert settings.mask("short") == "********"
    assert settings.mask("sk-test1234567890abcd") == "sk-tes****abcd"


# ===== 凭据本身的保密性（field(repr=False) / compare=False）=====

_SECRET = "sk-supersecret-abcdefghijkl"


def _cred(key: str) -> settings.Credentials:
    return settings.Credentials(key, config.LLM_BASE_URL, config.LLM_MODEL, bool(key))


def test_credentials_repr_and_str_never_contain_api_key():
    """repr=False：明文 Key 绝不进 repr / str，也就进不了日志、异常 locals、断言 diff。"""
    cred = _cred(_SECRET)
    assert _SECRET not in repr(cred)
    assert _SECRET not in str(cred)
    assert _SECRET not in f"{cred}"
    # 其余字段仍可见——是「只隐去 Key」，不是整个对象不可读
    assert config.LLM_MODEL in repr(cred)
    assert config.LLM_BASE_URL in repr(cred)


def test_credentials_equality_ignores_key():
    """刻意为之（compare=False）：相等性只看地址与模型名，Key 不参与比较。

    这是有意的权衡：让 Key 远离 == / 容器去重 / 断言 diff 的输出路径（那里最容易外泄）。
    代价是「两个凭据 Key 是否相同」不能靠 == 判断，需要时必须显式比较 .api_key。
    """
    a = _cred("sk-aaa-first-key-0000")
    b = _cred("sk-bbb-second-key-1111")
    assert a == b
    # 相等不代表 Key 相同：显式比较才能看出差异
    assert a.api_key != b.api_key


def test_key_upsert_and_delete(tmp_db):
    u = _mk_user("alice")
    uid = int(u["id"])
    db.set_user_api_key(uid, "deepseek", "sk-first")
    db.set_user_api_key(uid, "deepseek", "sk-second")
    assert db.get_user_api_key(uid, "deepseek") == "sk-second"
    db.delete_user_api_key(uid, "deepseek")
    assert db.get_user_api_key(uid, "deepseek") == ""
    assert db.get_user_api_keys(uid) == {}

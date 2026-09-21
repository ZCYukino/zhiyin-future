"""auth.py 单元测试：JWT 签发 / 校验；以及管理员用户名的注册保留。"""
from __future__ import annotations

import pytest
from fastapi import HTTPException

from app import config, db, server
from app.auth import create_token, decode_token


@pytest.fixture()
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "test-users.db"))
    db.init_db()
    db.ensure_admin(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)


def test_create_and_decode_roundtrip():
    token = create_token(1, "ZCY")
    payload = decode_token(token)
    assert payload is not None
    assert payload["sub"] == "1"
    assert payload["username"] == "ZCY"


def test_decode_invalid_token():
    assert decode_token("not-a-valid-token") is None


def test_reserved_username_rejected_by_create_user(tmp_db):
    """create_user 是最后一道闸：即使绕过 HTTP 层也建不出管理员同名账号。"""
    assert db.create_user(config.ADMIN_USERNAME, "123456") is None


def test_reserved_username_rejected_by_register_endpoint(tmp_db):
    with pytest.raises(HTTPException) as ei:
        server.auth_register(
            server.RegisterRequest(username=config.ADMIN_USERNAME, password="123456")
        )
    assert ei.value.status_code == 400
    assert "保留" in ei.value.detail


def test_reserved_username_rejected_with_surrounding_whitespace(tmp_db):
    """两端空白会被 strip 掉后比对，故 " ZCY " 同样是保留名。"""
    padded = f"  {config.ADMIN_USERNAME}  "
    assert db.is_reserved_username(padded) is True
    assert db.create_user(padded, "123456") is None

    with pytest.raises(HTTPException) as ei:
        server.auth_register(server.RegisterRequest(username=padded, password="123456"))
    assert ei.value.status_code == 400


def test_reservation_is_not_over_broad(tmp_db):
    """保留的只是那一个用户名：其它名字照常注册成功（两个入口都验一遍）。"""
    via_db = db.create_user("normal_user", "123456")
    assert via_db is not None
    assert via_db["username"] == "normal_user"
    assert via_db["role"] == "user"

    resp = server.auth_register(
        server.RegisterRequest(username="another_user", password="123456")
    )
    assert resp["user"]["username"] == "another_user"
    assert resp["token"]

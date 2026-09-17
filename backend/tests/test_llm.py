"""llm.py 单元测试：思考标签剥离 + JSON 容错解析（纯函数，不触发网络）+ 凭据缺失时的「炸出来」。

凭据相关的用例全部在**发起网络请求之前**返回，故不需要打桩 OpenAI 客户端。
"""
from __future__ import annotations

import pytest

from app import config, settings
from app.llm import (
    LLMNotConfigured,
    _extract_json,
    _strip_thinking,
    embed,
    generate,
    generate_json,
)

# 内部调用漏传凭据时的提示语（区别于「该账号没配 Key」）
_INTERNAL_HINT = "显式传入凭据"


def test_strip_thinking_paired():
    text = "<thinking>思考内容</thinking>\n{\"a\": 1}"
    assert "<thinking>" not in _strip_thinking(text)
    assert "思考内容" not in _strip_thinking(text)


def test_strip_thinking_single_sided():
    assert "<|thinking|>" not in _strip_thinking("<|thinking|>hello")
    assert "</thinking>" not in _strip_thinking("hello</thinking>")


def test_extract_json_direct():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_code_block():
    assert _extract_json('```json\n{"b": 2}\n```') == {"b": 2}


def test_extract_json_fence():
    assert _extract_json('说明文字 ```json\n{"c": 3}\n``` 结尾') == {"c": 3}


def test_extract_json_brace_pairing():
    assert _extract_json('前缀 {"d": 4} 后缀') == {"d": 4}


def test_extract_json_invalid_returns_none():
    assert _extract_json("不是 JSON") is None


# ===== 漏传凭据必须「炸出来」，绝不隐式回退到管理员 Key（零相交）=====

def _unconfigured() -> settings.Credentials:
    """显式传入、但 key 为空（configured=False）的凭据。"""
    return settings.Credentials("", config.LLM_BASE_URL, config.LLM_MODEL, False)


def test_generate_without_credentials_raises_internal_guard():
    with pytest.raises(LLMNotConfigured) as ei:
        generate("x")
    assert _INTERNAL_HINT in str(ei.value)


def test_generate_json_without_credentials_raises_internal_guard():
    with pytest.raises(LLMNotConfigured) as ei:
        generate_json("x")
    assert _INTERNAL_HINT in str(ei.value)


def test_embed_without_credentials_raises_internal_guard():
    with pytest.raises(LLMNotConfigured) as ei:
        embed(["x"])
    assert _INTERNAL_HINT in str(ei.value)


def test_generate_with_unconfigured_credentials_reports_account_not_internal_call():
    """显式传了凭据但没配 Key → 是「请先配置…」的账号级提示，不是「调用方漏传」。

    两种失败模式的文案必须可区分：前者是用户可自助修复的配置问题，
    后者是后端代码 bug（谁漏传了 credentials）。
    """
    with pytest.raises(LLMNotConfigured) as ei:
        generate("x", credentials=_unconfigured())
    assert "请先配置" in str(ei.value)
    assert _INTERNAL_HINT not in str(ei.value)


def test_generate_json_with_unconfigured_credentials_reports_account_not_internal_call():
    with pytest.raises(LLMNotConfigured) as ei:
        generate_json("x", credentials=_unconfigured())
    assert "请先配置" in str(ei.value)
    assert _INTERNAL_HINT not in str(ei.value)


def test_embed_with_unconfigured_credentials_reports_account_not_internal_call():
    with pytest.raises(LLMNotConfigured) as ei:
        embed(["x"], credentials=_unconfigured())
    assert "请先配置" in str(ei.value)
    assert _INTERNAL_HINT not in str(ei.value)

"""LLM 客户端：对话走 DeepSeek，向量化走阿里云百炼 DashScope。

Key 来自账号级凭据（app.settings）；未配置抛 LLMNotConfigured，由调用方决定语义。
客户端按 (api_key, base_url) 复用，上限 32 个。
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from collections import OrderedDict
from typing import Any, Iterable

from openai import OpenAI

from . import config, settings

logger = logging.getLogger("llm")

# 重试参数：3 次 + 指数退避，仅对可重试的瞬时故障生效
MAX_RETRIES = 3
RETRY_BASE_DELAY = 1.0

# 思考模型输出的思考内容统一剥离
_THINKING_TAG_RE = re.compile(
    r"<\s*\|?\s*(?:reserved_think|thinking|thought|think)\s*\|?\s*>.*?<\s*\|?\s*/\s*(?:reserved_think|thinking|thought|think)\s*\|?\s*>",
    re.DOTALL | re.IGNORECASE,
)
# 单边遗留的思考起始/结束标记
_THINKING_OPEN_RE = re.compile(r"<\s*\|?\s*(?:reserved_think|thinking|thought|think)\s*\|?\s*>", re.IGNORECASE)
_THINKING_CLOSE_RE = re.compile(r"<\s*\|?\s*/\s*(?:reserved_think|thinking|thought|think)\s*\|?\s*>", re.IGNORECASE)


class LLMNotConfigured(RuntimeError):
    """该账号未配置对应 provider 的 API Key（前端引导配置，不静默降级）。"""


# 客户端缓存：按 (api_key, base_url) 复用，上限 32；后台线程与请求处理并发访问，读写持锁
_client_cache: OrderedDict[tuple[str, str], OpenAI] = OrderedDict()
_client_lock = threading.Lock()


def _client(api_key: str, base_url: str) -> OpenAI:
    key = (api_key, base_url)
    with _client_lock:
        client = _client_cache.get(key)
        if client is None:
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=config.REQUEST_TIMEOUT)
            _client_cache[key] = client
            if len(_client_cache) > 32:
                _client_cache.popitem(last=False)
    return client


def generate(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.3,
    timeout: float | None = None,
    max_retries: int = MAX_RETRIES,
    credentials: settings.Credentials | None = None,
) -> str:
    """调用 DeepSeek 生成文本，带指数退避重试。

    credentials 必须显式传入（用户请求传 llm_credentials，系统级任务传 system_llm_credentials）；
    None 视为漏传凭据并抛 LLMNotConfigured，绝不隐式回退到管理员 Key。
    """
    if credentials is None:
        raise LLMNotConfigured(
            "内部调用必须显式传入凭据（系统任务请传 settings.system_llm_credentials()）"
        )
    cred = credentials
    if not cred.configured:
        raise LLMNotConfigured("请先配置 DeepSeek API Key")
    model = model or cred.model
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    kwargs: dict[str, Any] = {"temperature": temperature}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    # 关闭思考链，避免残留 thinking 标签污染 JSON（仅 DashScope 支持）
    if "dashscope" in (cred.base_url or ""):
        kwargs["extra_body"] = {"enable_thinking": False}
    if timeout is not None:
        kwargs["timeout"] = timeout

    last_exc: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = _client(cred.api_key, cred.base_url).chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001 瞬时故障可重试
            last_exc = e
            # 首次失败是 400（模型拒绝 enable_thinking）时去掉该参数立即重试
            if attempt == 0 and "extra_body" in kwargs and getattr(e, "status_code", None) == 400:
                kwargs.pop("extra_body", None)
                logger.warning("enable_thinking 参数被模型拒绝，去掉后重试：%s", e)
                continue
            if attempt < max_retries - 1:
                delay = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning("LLM 调用失败（第 %d/%d 次），%.1fs 后重试：%s", attempt + 1, max_retries, delay, e)
                time.sleep(delay)
    raise last_exc  # type: ignore[misc]


def _strip_thinking(text: str) -> str:
    """剥离思考模型可能残留的思考标签（成对/单边），防止污染 JSON。"""
    prev = None
    while prev != text:
        prev = text
        text = _THINKING_TAG_RE.sub("", text)
    text = _THINKING_OPEN_RE.sub("", text)
    text = _THINKING_CLOSE_RE.sub("", text)
    return text


def _extract_json(text: str) -> Any:
    """多策略解析 JSON：直接解析 → 代码块 → 花括号配对。"""
    text = _strip_thinking(text).strip()

    def _try(s: str) -> Any:
        try:
            return json.loads(s)
        except json.JSONDecodeError:
            return None

    # 1. 直接解析
    direct = _try(text)
    if direct is not None:
        return direct

    # 2. 剥离 ```json / ``` 代码块
    if text.startswith("```"):
        inner = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        block = _try(inner)
        if block is not None:
            return block
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text, re.IGNORECASE)
    if fence:
        block = _try(fence.group(1).strip())
        if block is not None:
            return block

    # 3. 截取首个 { 到最后一个 }，容忍前后夹杂说明文字
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end > start:
        frag = _try(text[start : end + 1])
        if frag is not None:
            return frag

    return None


def generate_json(
    prompt: str,
    system: str | None = None,
    model: str | None = None,
    temperature: float = 0.2,
    timeout: float | None = None,
    max_retries: int = MAX_RETRIES,
    credentials: settings.Credentials | None = None,
) -> Any:
    """生成并解析 JSON：LLMNotConfigured 向上抛；其他失败返回 None。credentials 须显式传入。"""
    # json_object 模式要求 prompt 显式包含 "JSON"
    if "JSON" not in prompt:
        prompt = prompt + "\n\n请只输出 JSON，不要包含任何解释或 Markdown 代码块。"
    try:
        text = generate(
            prompt, system=system, model=model, json_mode=True,
            temperature=temperature, timeout=timeout, max_retries=max_retries,
            credentials=credentials,
        )
    except LLMNotConfigured:
        raise
    except Exception as e:  # noqa: BLE001 LLM 异常统一返回 None，由调用方决定语义
        logger.warning("LLM 生成失败（已重试 %d 次）：%s", max_retries, e)
        return None
    parsed = _extract_json(text)
    if parsed is None:
        logger.warning("LLM 返回内容无法解析为 JSON：%.200s", text.strip())
    return parsed


def embed(
    texts: Iterable[str],
    model: str | None = None,
    credentials: settings.Credentials | None = None,
) -> list[list[float]]:
    """批量向量化。credentials 必须显式传入，None 视为漏传并抛 LLMNotConfigured。"""
    if credentials is None:
        raise LLMNotConfigured(
            "内部调用必须显式传入凭据（系统任务请传 settings.embed_credentials()）"
        )
    cred = credentials
    if not cred.configured:
        raise LLMNotConfigured("请先配置阿里云百炼 API Key")
    model = model or cred.model
    items = [t for t in texts]
    if not items:
        return []
    resp = _client(cred.api_key, cred.base_url).embeddings.create(
        model=model,
        input=items,
        dimensions=config.EMBEDDING_DIM,
        encoding_format="float",
    )
    # 按 index 排序，保证顺序
    data = sorted(resp.data, key=lambda d: d.index)
    return [d.embedding for d in data]


def verify_api_key(provider: str, api_key: str, timeout: float = 20.0) -> str | None:
    """实测校验：deepseek 发一次最小对话 / dashscope 发一次最短向量化；失败返回中文错误。"""
    base_url = config.LLM_BASE_URL if provider == "deepseek" else config.DASHSCOPE_BASE_URL
    client = _client(api_key, base_url)
    try:
        if provider == "deepseek":
            client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=[{"role": "user", "content": "ping"}],
                max_tokens=1,
                timeout=timeout,
            )
        else:
            client.embeddings.create(
                model=config.EMBEDDING_MODEL,
                input=["ping"],
                dimensions=config.EMBEDDING_DIM,
                encoding_format="float",
                timeout=timeout,
            )
        return None
    except Exception as e:  # noqa: BLE001 校验失败一律转中文提示
        code = getattr(e, "status_code", None)
        if code == 401:
            return "Key 无效或已被删除（认证失败）"
        if code == 402 or code == 429:
            return "Key 无可用额度或余额不足"
        if code == 403:
            return "该 Key 未开通模型服务"
        return "无法连接，请检查网络后重试"

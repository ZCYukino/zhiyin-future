"""爬虫基础设施：低频率合规 HTTP 请求 + 原始 JD 数据结构。"""
from __future__ import annotations

import random
import time
from dataclasses import asdict, dataclass, field
from typing import Any

import requests

# 常见 User-Agent 池（随机轮换）
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
]

# 请求间隔（秒），低频率避免对目标站点造成压力
REQUEST_INTERVAL = (0.8, 2.0)


@dataclass
class RawJob:
    """爬虫产出的原始 JD（未结构化，交给 LLM 抽取）。只保留岗位信息。"""

    title: str
    description: str
    city: str = ""
    salary: str = ""
    salary_min: float | None = None
    salary_max: float | None = None
    source: str = ""
    url: str = ""
    published_at: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def fetch(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: int = 15,
    encoding: str | None = None,
    retries: int = 2,
) -> requests.Response:
    """带重试、随机延迟、UA 轮换的 GET 请求。"""
    hdrs = {"User-Agent": random.choice(USER_AGENTS)}
    if headers:
        hdrs.update(headers)

    last_err: Exception | None = None
    for _ in range(retries + 1):
        try:
            time.sleep(random.uniform(*REQUEST_INTERVAL))
            resp = requests.get(url, params=params, headers=hdrs, timeout=timeout)
            if encoding:
                resp.encoding = encoding
            elif resp.encoding is None or resp.encoding.lower() in ("iso-8859-1", "ascii"):
                # 中文站点常未正确声明编码，回退到 apparent_encoding
                resp.encoding = resp.apparent_encoding or "utf-8"
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:  # noqa: PERF203
            last_err = e
    raise last_err  # type: ignore[misc]


def post_json(
    url: str,
    payload: dict,
    headers: dict | None = None,
    timeout: int = 15,
    retries: int = 2,
) -> Any:
    """带重试、随机延迟、UA 轮换的 POST JSON 请求，返回解析后的 JSON。"""
    hdrs = {"User-Agent": random.choice(USER_AGENTS)}
    if headers:
        hdrs.update(headers)

    last_err: Exception | None = None
    for _ in range(retries + 1):
        try:
            time.sleep(random.uniform(*REQUEST_INTERVAL))
            resp = requests.post(url, json=payload, headers=hdrs, timeout=timeout)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:  # noqa: PERF203
            last_err = e
    raise last_err  # type: ignore[misc]

"""seed.py 单元测试：种子数据完整性。"""
from __future__ import annotations

from app.seed import SEED_KEYWORDS, SEED_RAW_JOBS


def test_seed_jobs_valid():
    assert len(SEED_RAW_JOBS) >= 8
    for j in SEED_RAW_JOBS:
        assert j.title
        assert j.description
        assert j.source == "seed"


def test_seed_keywords_nonempty():
    assert len(SEED_KEYWORDS) >= 10
    assert all(kw for kw in SEED_KEYWORDS)

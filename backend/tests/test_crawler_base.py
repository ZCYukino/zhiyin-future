"""crawler/base.py 单元测试：RawJob 数据结构。"""
from __future__ import annotations

from app.crawler.base import RawJob


def test_rawjob_defaults():
    j = RawJob(title="t", description="d")
    assert j.city == ""
    assert j.salary_min is None
    assert j.extra == {}


def test_rawjob_to_dict():
    j = RawJob(title="t", description="d", city="北京", source="mohrss")
    d = j.to_dict()
    assert d["title"] == "t"
    assert d["city"] == "北京"
    assert d["source"] == "mohrss"

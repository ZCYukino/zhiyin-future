"""clean.py 单元测试：去噪 / 城市归一 / 去重 / 交叉验证 / 清洗流水线。"""
from __future__ import annotations

from app.clean import (
    _similarity,
    clean_pipeline,
    cross_validate_skills,
    deduplicate,
    denoise,
    normalize_city,
)
from app.crawler.base import RawJob


def _job(desc: str, city: str = "") -> RawJob:
    return RawJob(title="测试岗位", description=desc, city=city)


# ===== denoise =====
def test_denoise_removes_noise_lines():
    text = "岗位职责：负责后端开发。\n五险一金、带薪年假、节日福利\n联系人：张三 13800138000\n领导交办的其他事项\n熟悉 Python 与 MySQL。"
    out = denoise(text)
    assert "岗位职责" in out
    assert "熟悉 Python" in out
    assert "五险一金" not in out
    assert "联系人" not in out
    assert "领导交办" not in out


def test_denoise_keeps_clean_lines():
    text = "岗位职责：负责算法研发。\n任职要求：精通 Python。"
    assert denoise(text) == text


# ===== normalize_city =====
def test_normalize_city_province_dropped():
    assert normalize_city("广东省") == ""
    assert normalize_city("内蒙古自治区") == ""


def test_normalize_city_municipality():
    assert normalize_city("北京") == "北京"
    assert normalize_city("上海市") == "上海"


def test_normalize_city_strip_suffix():
    assert normalize_city("杭州市") == "杭州"


def test_normalize_city_district():
    assert normalize_city("朝阳区") == "北京"
    assert normalize_city("天河区") == "广州"
    assert normalize_city("不存在的区") == ""


def test_normalize_city_passthrough_and_empty():
    assert normalize_city("杭州") == "杭州"
    assert normalize_city("") == ""


# ===== _similarity / deduplicate =====
def test_similarity():
    assert _similarity("", "x") == 0.0
    assert _similarity("abc", "abc") == 1.0


def test_deduplicate_removes_near_duplicates():
    jobs = [_job("负责 Java 后端服务开发与维护"), _job("负责 Java 后端服务开发与维护")]
    assert len(deduplicate(jobs)) == 1


def test_deduplicate_keeps_distinct():
    jobs = [_job("负责 Java 后端开发"), _job("负责前端 Vue 页面开发")]
    assert len(deduplicate(jobs)) == 2


# ===== cross_validate_skills =====
def test_cross_validate_support():
    lists = [["Python", "Java"], ["Python", "Go"], ["Java", "C++"]]
    assert sorted(cross_validate_skills(lists, min_support=2)) == ["Java", "Python"]


def test_cross_validate_min_support_one():
    lists = [["Python"], ["Java"]]
    assert sorted(cross_validate_skills(lists, min_support=1)) == ["Java", "Python"]


# ===== clean_pipeline =====
def test_clean_pipeline_drops_short_and_normalizes():
    jobs = [
        _job("岗位职责：负责后端服务端架构设计与核心业务开发，熟悉高并发与数据库优化，具备良好工程能力。", "北京市"),
        _job("太短", "朝阳区"),
    ]
    out = clean_pipeline(jobs)
    assert len(out) == 1
    assert out[0].city == "北京"

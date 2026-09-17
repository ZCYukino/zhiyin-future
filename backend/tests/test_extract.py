"""extract.py 单元测试：技术栈推断 + 九类分类定义。"""
from __future__ import annotations

from app.extract import (
    CATEGORIES,
    CATEGORY_DESC,
    CATEGORY_IDS,
    CATEGORY_NAMES,
    _infer_stack,
)


def test_infer_stack_ai():
    assert _infer_stack("PyTorch") == "ai"
    assert _infer_stack("大模型") == "ai"
    assert _infer_stack("自然语言处理") == "ai"


def test_infer_stack_backend():
    assert _infer_stack("Java") == "backend"
    assert _infer_stack("MySQL") == "backend"
    assert _infer_stack("微服务") == "backend"


def test_infer_stack_frontend():
    assert _infer_stack("Vue") == "frontend"
    assert _infer_stack("React") == "frontend"


def test_infer_stack_data():
    assert _infer_stack("Spark") == "data"
    assert _infer_stack("SQL") == "data"
    assert _infer_stack("数据挖掘") == "data"


def test_infer_stack_cloud():
    assert _infer_stack("Kubernetes") == "cloud"
    assert _infer_stack("Docker") == "cloud"
    assert _infer_stack("Linux") == "cloud"


def test_infer_stack_security():
    assert _infer_stack("WAF") == "security"
    assert _infer_stack("渗透测试") == "security"


def test_infer_stack_embedded():
    assert _infer_stack("RTOS") == "embedded"
    assert _infer_stack("C++") == "embedded"
    assert _infer_stack("ARM") == "embedded"


def test_infer_stack_product():
    assert _infer_stack("产品规划") == "product"
    assert _infer_stack("PRD") == "product"


def test_infer_stack_qa():
    assert _infer_stack("Selenium") == "qa"
    assert _infer_stack("测试") == "qa"


def test_infer_stack_default_tool():
    assert _infer_stack("Git") == "tool"


def test_categories_consistency():
    assert len(CATEGORIES) == 9
    assert len(CATEGORY_IDS) == 9
    assert set(CATEGORY_IDS) == set(CATEGORY_NAMES.keys())
    assert all(cid in CATEGORY_DESC for cid in CATEGORY_IDS)


def test_extract_job(monkeypatch):
    import app.extract as extract
    from app.crawler.base import RawJob
    fake = {"name": "X", "categoryId": "ai", "mustSkills": ["Python"], "bonusSkills": []}
    monkeypatch.setattr(extract, "generate_json", lambda *a, **k: fake)
    raw = RawJob(title="算法工程师", description="岗位描述", city="北京", salary="20-30K")
    assert extract.extract_job(raw) == fake


def test_generate_job_definition(monkeypatch):
    import app.extract as extract
    fake = {"name": "X", "categoryId": "ai"}
    monkeypatch.setattr(extract, "build_context", lambda *a, **k: "上下文")
    monkeypatch.setattr(extract, "generate_json", lambda *a, **k: fake)
    assert extract.generate_job_definition("X") == fake


def test_generate_job_definition_no_context(monkeypatch):
    import app.extract as extract
    monkeypatch.setattr(extract, "build_context", lambda *a, **k: "")
    assert extract.generate_job_definition("X") is None


def test_generate_capability_change(monkeypatch):
    import app.extract as extract
    fake = {"changes": [{"period": "2026上半年", "addedSkills": ["a"]}]}
    monkeypatch.setattr(extract, "generate_json", lambda *a, **k: fake)
    out = extract.generate_capability_change("X", ["a"], ["b"], ["c"], "p1", "p2")
    assert out == [{"period": "2026上半年", "addedSkills": ["a"],
                    "removedSkills": [], "importanceUp": [], "importanceDown": []}]


def test_generate_capability_change_invalid(monkeypatch):
    import app.extract as extract
    monkeypatch.setattr(extract, "generate_json", lambda *a, **k: {"changes": "not-a-list"})
    assert extract.generate_capability_change("X", [], [], [], "p1", "p2") is None

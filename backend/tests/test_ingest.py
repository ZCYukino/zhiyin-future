"""ingest.py 单元测试：分类推断 / 聚合 / 技能矩阵 / 图谱 / 存档 / 抽取与演化 / 零产出保护。"""
from __future__ import annotations

import json
from datetime import datetime

import pytest

import app.ingest as ingest
from app.ingest import (
    _aggregate,
    _infer_category,
    _skill_levels,
    archive_jds,
    build_graph,
    build_job_relations,
    normalize_education,
    recent_periods,
)
from app.crawler.base import RawJob


# ===== _infer_category =====
def test_infer_category():
    assert _infer_category("产品经理", "") == "product"
    assert _infer_category("嵌入式工程师", "") == "embedded"
    assert _infer_category("渗透测试工程师", "") == "security"
    assert _infer_category("测试开发工程师", "") == "qa"
    assert _infer_category("数据分析师", "") == "data"
    assert _infer_category("前端开发", "") == "frontend"
    assert _infer_category("后端开发", "") == "backend"
    assert _infer_category("云计算运维", "") == "cloud"
    assert _infer_category("算法工程师", "") == "ai"


# ===== _skill_levels =====
def test_skill_levels_with_bonus():
    out = _skill_levels(["a", "b", "c", "d", "e", "f", "g"], ["x", "y"])
    assert out["junior"] == [{"name": "a", "stack": "tool"}, {"name": "b", "stack": "tool"}, {"name": "c", "stack": "tool"}]
    assert out["mid"][0]["name"] == "d"
    assert [s["name"] for s in out["senior"]] == ["x", "y"]


def test_skill_levels_no_bonus_promotes_mid():
    out = _skill_levels(["a", "b", "c", "d", "e"], [])
    assert [s["name"] for s in out["junior"]] == ["a", "b", "c"]
    assert [s["name"] for s in out["mid"]] == ["d"]
    assert [s["name"] for s in out["senior"]] == ["e"]


# ===== normalize_education =====
def test_normalize_education():
    assert normalize_education("不限") == "不限"
    assert normalize_education("博士") == "博士及以上"
    assert normalize_education("硕士及以上学历") == "硕士及以上"
    assert normalize_education("本科") == "本科及以上"
    assert normalize_education("大专") == "大专及以上"


# ===== _aggregate =====
def test_aggregate_groups_and_cross_validates():
    items = [
        {"name": "后端工程师", "categoryId": "backend", "duties": ["d1"],
         "mustSkills": ["Java", "Spring Boot"], "bonusSkills": ["Kafka"],
         "education": "本科及以上", "experience": "1-3年",
         "salaryMin": 20, "salaryMax": 40, "_city": "北京"},
        {"name": "后端工程师", "categoryId": "backend", "duties": ["d2"],
         "mustSkills": ["Java", "MySQL"], "bonusSkills": ["Kafka"],
         "education": "本科及以上", "experience": "3-5年",
         "salaryMin": 25, "salaryMax": 50, "_city": "上海"},
        {"name": "后端工程师", "categoryId": "backend", "duties": ["d3"],
         "mustSkills": ["Java", "Go"], "bonusSkills": [],
         "education": "本科及以上", "experience": "3-5年",
         "salaryMin": 30, "salaryMax": 60, "_city": "北京"},
    ]
    out = _aggregate(items)
    assert len(out) == 1
    j = out[0]
    assert "Java" in j["mustSkills"]  # 支持度 3
    assert j["categoryId"] == "backend"
    assert j["experience"] == "3-5年"  # 众数
    assert j["cityDistribution"][0]["city"] == "北京"


def test_aggregate_single_sample_keeps_all():
    items = [{"name": "算法工程师", "categoryId": "ai", "duties": ["d"],
              "mustSkills": ["Python", "PyTorch"], "bonusSkills": [],
              "education": "硕士及以上", "experience": "3-5年",
              "salaryMin": 30, "salaryMax": 60, "_city": ""}]
    out = _aggregate(items)
    assert sorted(out[0]["mustSkills"]) == ["PyTorch", "Python"]
    assert out[0]["cityDistribution"] == []


# ===== recent_periods =====
def test_recent_periods():
    assert recent_periods(datetime(2026, 8, 1)) == ("2026上半年", "2026下半年")
    assert recent_periods(datetime(2026, 3, 1)) == ("2025下半年", "2026上半年")


# ===== build_job_relations =====
def test_build_job_relations_advanced_and_transfer():
    jobs = [
        {"id": "1", "name": "软件工程师", "categoryId": "backend", "skills": ["Java", "Python", "SQL"]},
        {"id": "2", "name": "AI模型算法工程师", "categoryId": "ai", "skills": ["Python", "PyTorch"]},
        {"id": "3", "name": "数据分析师", "categoryId": "data", "skills": ["SQL", "Python", "Java"]},
    ]
    edges = build_job_relations(jobs)
    rels = {(e["source"], e["target"]): e["relation"] for e in edges}
    # 垂直晋升阶梯 软件工程师 -> AI模型算法工程师
    assert ("job-1", "job-2") in rels or ("job-2", "job-1") in rels
    assert "advanced" in rels.values()
    # 横向换岗：AI模型算法工程师 与 数据分析师 共享 Python
    assert any(e["relation"] == "transfer" for e in edges)


# ===== build_graph =====
def test_build_graph():
    jobs = [{"id": "1", "name": "后端工程师", "categoryId": "backend", "isNew": False,
             "skills": ["Java", "Kafka"]}]
    must_bonus = {"1": (["Java"], ["Kafka"])}
    graph = build_graph(jobs, must_bonus)
    assert len(graph["nodes"]) == 3  # 1 job + 2 skills
    assert any(n["type"] == "job" for n in graph["nodes"])
    assert any(e["relation"] == "core" for e in graph["edges"])
    assert any(e["relation"] == "optional" for e in graph["edges"])


# ===== archive_jds =====
def test_archive_jds_dedup(monkeypatch, tmp_path):
    archive_path = tmp_path / "jd_archive.json"
    monkeypatch.setattr(ingest, "JD_ARCHIVE_PATH", archive_path)
    raw = [
        RawJob(title="岗位A", description="职责描述内容足够长", url="http://x/1", source="mohrss"),
        RawJob(title="岗位A", description="职责描述内容足够长", url="http://x/1", source="mohrss"),
        RawJob(title="岗位B", description="另一条岗位职责描述", url="http://x/2", source="mohrss"),
    ]
    total = archive_jds(raw)
    assert total == 2
    data = json.loads(archive_path.read_text(encoding="utf-8"))
    assert len(data["items"]) == 2


# ===== _extract_one（LLM 成功 / 失败返回 None） =====
def test_extract_one_llm(monkeypatch):
    monkeypatch.setattr(ingest, "extract_job", lambda raw: {
        "name": "后端工程师", "mustSkills": ["Java"], "bonusSkills": [], "categoryId": "backend"})
    raw = RawJob(title="t", description="d", city="北京")
    d = ingest._extract_one(raw)
    assert d["name"] == "后端工程师"
    assert d["_city"] == "北京"


def test_extract_one_none_when_llm_fails(monkeypatch):
    monkeypatch.setattr(ingest, "extract_job", lambda raw: None)
    raw = RawJob(title="后端开发工程师", description="熟悉 Java、Spring Boot、MySQL", city="上海")
    assert ingest._extract_one(raw) is None


# ===== _discover_one =====
def test_discover_one(monkeypatch):
    fake = {"name": "AI智能体开发工程师", "categoryId": "ai", "confidence": 0.8,
            "summary": "s", "duties": ["d"], "mustSkills": ["Python"],
            "bonusSkills": [], "scenarios": []}
    monkeypatch.setattr(ingest, "generate_job_definition", lambda *a, **k: fake)
    d = ingest._discover_one({"name": "x", "seed": "s"})
    assert d["name"] == "AI智能体开发工程师"
    assert d["_isNew"] is True
    assert d["categoryId"] == "ai"


def test_discover_one_low_confidence(monkeypatch):
    monkeypatch.setattr(ingest, "generate_job_definition", lambda *a, **k: {"name": "X", "confidence": 0.2})
    assert ingest._discover_one({"name": "x", "seed": "s"}) is None


# ===== _capability_change_one =====
def test_capability_change_one(monkeypatch):
    fake = [{"period": "2026上半年", "addedSkills": ["a"], "removedSkills": [],
             "importanceUp": [], "importanceDown": []}]
    monkeypatch.setattr(ingest, "generate_capability_change", lambda *a, **k: fake)
    j = {"id": "1", "name": "X"}
    mb = {"1": (["Python", "PyTorch", "Java"], [])}
    out = ingest._capability_change_one(j, mb)
    assert out[0]["jobId"] == "1"
    assert out[0]["addedSkills"] == ["a"]


def test_capability_change_one_failed_returns_empty(monkeypatch):
    monkeypatch.setattr(ingest, "generate_capability_change", lambda *a, **k: None)
    j = {"id": "1", "name": "X"}
    mb = {"1": (["Python"], [])}
    assert ingest._capability_change_one(j, mb) == []


# ===== build_knowledge =====
def test_build_knowledge(monkeypatch):
    monkeypatch.setattr(ingest, "discover_new_job_defs", lambda *a, **k: [])
    monkeypatch.setattr(ingest, "generate_capability_changes", lambda *a, **k: [])
    extracted = [{"name": "后端工程师", "categoryId": "backend", "duties": ["d"],
                  "mustSkills": ["Java"], "bonusSkills": ["Kafka"],
                  "education": "本科及以上", "experience": "1-3年",
                  "salaryMin": 20, "salaryMax": 40, "_city": "北京"}]
    k = ingest.build_knowledge(extracted)
    assert len(k["jobs"]) == 1
    assert k["jobs"][0]["id"] == "1"
    assert k["jobs"][0]["name"] == "后端工程师"
    assert "jobSkillProgression" in k
    assert "graph" in k
    assert "capabilityChanges" in k


# ============================================================================
# 数据丢失防护：空数据 / 失败路径不得清空既有向量库、不得写空快照
# ============================================================================

def test_index_vectors_empty_jobs_keeps_existing_collection(monkeypatch):
    """jobs 为空 → 直接返回，绝不清空集合。

    一次「本轮没抓到岗位」若调用 reset_collection，就会把在线 RAG 的语料抹成空库，
    而本轮并没有任何新向量可写回。
    """
    calls: list[str] = []
    monkeypatch.setattr(ingest.store, "reset_collection", lambda: calls.append("reset_collection"))
    monkeypatch.setattr(ingest.store, "upsert_fragments", lambda *a, **k: calls.append("upsert_fragments"))

    def _no_embed(*a, **k):
        raise AssertionError("jobs 为空时不应触发 embedding")

    monkeypatch.setattr(ingest, "embed", _no_embed)

    ingest.index_vectors({"jobs": []})

    assert calls == []


def test_index_vectors_embed_failure_keeps_existing_collection(monkeypatch):
    """embedding 失败 → 异常向上抛，且**尚未** reset（旧集合原样保留）。

    逐批 embed 全部成功后才允许 reset + 重建；否则限流/断网/欠费任何一次失败都会
    把向量库清空且无人重建。
    """
    calls: list[str] = []
    monkeypatch.setattr(ingest.store, "reset_collection", lambda: calls.append("reset_collection"))
    monkeypatch.setattr(ingest.store, "upsert_fragments", lambda *a, **k: calls.append("upsert_fragments"))

    embed_calls: list[int] = []

    def _boom(texts, **k):
        embed_calls.append(len(texts))
        raise RuntimeError("embed 失败：Key 无可用额度")

    monkeypatch.setattr(ingest, "embed", _boom)

    knowledge = {"jobs": [{"id": "1", "name": "后端工程师", "skills": ["Java"]}]}
    with pytest.raises(RuntimeError, match="embed 失败"):
        ingest.index_vectors(knowledge)

    assert embed_calls == [1]  # 确实走到了 embedding 阶段（断言非空转）
    assert calls == []


def test_main_aborts_without_side_effects_when_nothing_extracted(monkeypatch):
    """零产出保护：本轮一个岗位都没抽到时必须抛错，且不向量化、不落快照。

    Key 失效时 generate_json 会把每个非配置类错误都吞成 None，extract_all 于是返回
    ([], 全部失败)。若继续往下走，就会清空向量库并把 {"jobs": []} 写成最新快照，
    而 load_latest_snapshot 永远取最新文件 → 全站 0 岗位。
    """
    raw = [RawJob(title="岗位A", description="职责描述足够长", url="http://x/1", source="mohrss")]
    monkeypatch.setattr(ingest, "collect_raw", lambda **k: list(raw))
    monkeypatch.setattr(ingest, "clean_pipeline", lambda jobs: list(jobs))
    monkeypatch.setattr(ingest, "archive_jds", lambda cleaned: len(cleaned))
    monkeypatch.setattr(ingest, "extract_all", lambda jobs, progress=None, workers=8: ([], ["岗位A"]))
    monkeypatch.setattr(ingest, "discover_new_job_defs", lambda *a, **k: [])

    side_effects: list[str] = []
    monkeypatch.setattr(ingest, "index_vectors", lambda k: side_effects.append("index_vectors"))
    monkeypatch.setattr(ingest.store, "save_snapshot", lambda k: side_effects.append("save_snapshot"))

    with pytest.raises(RuntimeError, match="未抽取到任何岗位"):
        ingest.main(use_crawler=False)

    assert side_effects == []


# ============================================================================
# 诚实留空：没有数据源的字段一律 None / []，绝不臆造兜底值
# ============================================================================

def test_aggregate_invents_nothing_when_samples_lack_data():
    """样本没给薪资/公司数/城市 → 输出留空，不编造区间或默认城市。"""
    items = [
        {"name": "合成数据工程师", "categoryId": "ai", "duties": ["d1"],
         "mustSkills": ["Python"], "bonusSkills": [], "education": "", "experience": "", "_city": ""},
        {"name": "合成数据工程师", "categoryId": "ai", "duties": ["d2"],
         "mustSkills": ["Python"], "bonusSkills": [], "education": "", "experience": "", "_city": ""},
    ]
    out = _aggregate(items)
    assert len(out) == 1
    j = out[0]
    assert j["salaryMin"] is None
    assert j["salaryMax"] is None
    assert j["companyCount"] is None
    assert j["cityDistribution"] == []
    assert j["experience"] == ""  # 未给年限就留空，不套用默认年限


def _discovered_def(monkeypatch, cand: dict | None = None) -> dict:
    """走真实的 _discover_one 生成一条新岗位定义（只打桩 LLM 调用本身）。"""
    cand = cand or {"name": "AI智能体开发工程师", "seed": "多智能体协作与工具调用"}
    monkeypatch.setattr(ingest, "generate_job_definition", lambda *a, **k: {
        "name": cand["name"], "categoryId": "ai", "confidence": 0.9,
        "summary": "摘要", "duties": ["职责"], "mustSkills": ["Python"],
        "bonusSkills": [], "scenarios": [],
    })
    d = ingest._discover_one(cand)
    assert d is not None
    return d


def test_discovered_job_leaves_unknown_fields_empty(monkeypatch):
    """新岗位没有 JD 样本：学历/经验/城市/公司数一律留空。"""
    d = _discovered_def(monkeypatch)
    assert d["education"] is None
    assert d["experience"] is None
    assert d["cityDistribution"] == []
    assert d["companyCount"] is None
    # 候选未给参考区间时也不编造薪资
    assert d["salaryMin"] is None
    assert d["salaryMax"] is None


def test_build_knowledge_new_job_has_no_fabricated_hot_or_trend(monkeypatch):
    """组装后的新岗位：hotScore / trend 无数据源 → None（前端显示「—」），不编造涨跌。"""
    discovered = _discovered_def(monkeypatch)
    monkeypatch.setattr(ingest, "discover_new_job_defs", lambda *a, **k: [dict(discovered)])
    monkeypatch.setattr(ingest, "generate_capability_changes", lambda *a, **k: [])
    extracted = [{"name": "后端工程师", "categoryId": "backend", "duties": ["d"],
                  "mustSkills": ["Java"], "bonusSkills": ["Kafka"],
                  "education": "本科及以上", "experience": "1-3年",
                  "salaryMin": 20, "salaryMax": 40, "_city": "北京"}]

    k = ingest.build_knowledge(extracted)

    old = next(j for j in k["jobs"] if not j["isNew"])
    new = next(j for j in k["jobs"] if j["isNew"])
    assert new["name"] == "AI智能体开发工程师"
    assert new["hotScore"] is None  # 无样本依据，不编造热度
    assert new["trend"] is None  # 无趋势数据源，不编造涨跌
    assert new["companyCount"] is None
    assert new["cityDistribution"] == []
    assert k["jobRequirements"][new["id"]]["education"] is None
    assert k["jobRequirements"][new["id"]]["experience"] is None
    # 老岗位热度由真实样本数派生（sampleCount=1 → 68），趋势同样无数据源
    assert old["hotScore"] == 68
    assert old["trend"] is None


def test_normalize_salary_never_returns_degenerate_range():
    """薪资区间必须始终满足 min < max，且缺失端点不臆造。

    回归：两端都超过 80K 上限的样本曾被钳制成 (80, 80)，前端会显示「80-80K」。
    """
    from app.ingest import _normalize_salary as norm

    # 钳制后仍须 min < max
    for raw in [(100, 120), (80, 100), (80, 80), (200, 300), (6, 6), (3, 3), (5, 200)]:
        lo, hi = norm(*raw)
        assert lo is not None and hi is not None, raw
        assert lo < hi, f"{raw} 退化为 ({lo}, {hi})"

    # 端点缺失/非正 → 不臆造区间
    for raw in [(None, None), (0, 40), (20, None), (None, 30), (-5, 20)]:
        assert norm(*raw) == (None, None), raw

    # 正常区间原样保留（只做取整）
    assert norm(20, 40) == (20, 40)
    assert norm(16.666, 9.167) == (17, 22)

"""离线采集管道：爬虫 → 清洗 → LLM 抽取 → 组装知识库 → 向量化 → 快照落盘。"""
from __future__ import annotations

import json
import logging
import re
import copy
import hashlib
import math
import uuid
import os
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Callable

from . import config, settings, store
from .clean import clean_pipeline, cross_validate_skills, job_identity
from .crawler.base import RawJob
from .crawler.sources import CRAWLERS
from .extract import CATEGORY_DESC, CATEGORY_IDS, CATEGORY_NAMES, _infer_stack, extract_job, generate_capability_change, generate_job_definition
from .llm import LLMNotConfigured, embed
from .seed import SEED_KEYWORDS, SEED_RAW_JOBS

logger = logging.getLogger("ingest")

# 清洗后 JD 的累积存档（跨轮去重）
JD_ARCHIVE_PATH = config.DATA_DIR / "raw_jds" / "jd_archive.json"
EXTRACTION_CACHE_PATH = config.DATA_DIR / "raw_jds" / "extractions.json"


def _write_json(path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    finally:
        tmp.unlink(missing_ok=True)


def _read_archive() -> list[dict[str, Any]]:
    if not JD_ARCHIVE_PATH.exists():
        return []
    data = json.loads(JD_ARCHIVE_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise RuntimeError("JD 累计存档格式错误，已停止刷新以保护既有数据")
    return data["items"]


def _raw_from_archive(item: dict[str, Any]) -> RawJob:
    return RawJob(title=item["title"], description=item["description"], city=item.get("city") or "",
        salary=item.get("salary") or "", salary_min=item.get("salaryMin"), salary_max=item.get("salaryMax"),
        source=item.get("source") or "", url=item.get("url") or "", published_at=item.get("publishedAt"),
        extra=item.get("extra") or {"company": item.get("company") or ""})


def load_archived_jobs() -> list[RawJob]:
    # 演示种子不计入真实招聘证据
    return [_raw_from_archive(item) for item in _read_archive() if item.get("source") not in ("", "seed")]


def archive_jds(cleaned: list[RawJob], stats: dict[str, Any] | None = None) -> int:
    """把本轮清洗后的 JD 追加进累积存档（按 URL / 标题+正文指纹去重），返回存档总条数。"""
    items = _read_archive()
    indexed = {job_identity(_raw_from_archive(item)): item for item in items}
    added = updated = 0
    now = datetime.now().isoformat(timespec="seconds")
    for j in cleaned:
        key = job_identity(j)
        previous = indexed.get(key)
        value = {
            "_key": key,
            "id": (previous or {}).get("id") or f"jd-{uuid.uuid4().hex}",
            "title": j.title,
            "description": j.description,
            "city": j.city,
            "salary": j.salary,
            "salaryMin": j.salary_min,
            "salaryMax": j.salary_max,
            "source": j.source,
            "url": j.url,
            "company": (j.extra or {}).get("company", ""),
            "publishedAt": j.published_at,
            "extra": copy.deepcopy(j.extra),
            "collectedAt": (previous or {}).get("collectedAt") or now,
            "lastSeenAt": now,
        }
        if previous is None:
            added += 1
        elif any(previous.get(field) != value[field] for field in ("title", "description", "city", "salary", "salaryMin", "salaryMax", "publishedAt", "extra")):
            updated += 1
        indexed[key] = value
    items = list(indexed.values())
    _write_json(JD_ARCHIVE_PATH, {"version": 2, "updatedAt": now, "items": items})
    if stats is not None:
        stats.update(newCount=added, updatedCount=updated, archiveCount=len([x for x in items if x.get("source") not in ("", "seed")]))
    return len(items)

# 垂直晋升阶梯（lower→upper），名字须与快照 jobs[].name 一致
JOB_LADDERS: list[tuple[str, str]] = [
    ("运维工程师", "运维主管"),
    ("软件工程师", "AI模型算法工程师"),
    ("AI模型算法工程师", "大模型算法工程师"),
    ("数字算法工程师", "AI模型算法工程师"),
    ("电子工程师", "嵌入式电控开发工程师"),
    ("嵌入式电控开发工程师", "嵌入式软件工程师"),
    ("嵌入式软件工程师", "嵌入式研发工程师"),
    ("前端开发工程师", "前端可视化开发工程师"),
    ("前端开发工程师", "GIS前端开发工程师"),
    ("大数据工程师", "大数据运维工程师"),
    ("Java开发工程师", "全栈工程师"),
    ("云平台驻场工程师", "运维主管"),
    ("AI智能体开发工程师", "AI智能体研发工程师"),
]


def collect_raw(use_crawler: bool = True, limit_per_kw: int = 50, stats: dict[str, Any] | None = None) -> list[RawJob]:
    """单次有界采样；真实来源无结果时报错，种子仅能显式用于离线演示。"""
    raw: list[RawJob] = []
    stats = stats if stats is not None else {}
    max_pages = max(1, min(100, int(os.getenv("CRAWL_MAX_PAGES", "5"))))
    limit_per_kw = max(1, min(1000, int(os.getenv("CRAWL_LIMIT_PER_KEYWORD", str(limit_per_kw)))))
    stats.update(sourceCounts={}, failedSources=[], sampled=True, maxPages=max_pages, limitPerKeyword=limit_per_kw)
    if use_crawler:
        for name, cls in CRAWLERS.items():
            crawler = cls()
            source_raw: list[RawJob] = []
            keywords = getattr(crawler, "KEYWORDS", None) or SEED_KEYWORDS
            for kw in keywords:
                try:
                    before = len(raw)
                    rows = crawler.crawl(kw, limit=limit_per_kw, pages=max_pages)
                    source_raw.extend(rows)
                    raw.extend(rows)
                    for error in getattr(crawler, "errors", []):
                        message = f"{name}: {error}"
                        if message not in stats["failedSources"]:
                            stats["failedSources"].append(message)
                    if getattr(crawler, "errors", []) and not rows:
                        break
                    logger.info("爬虫 %s 关键词 %s 获取 %d 条", name, kw, len(raw) - before)
                except Exception as e:  # noqa: BLE001
                    logger.warning("爬虫 %s 关键词 %s 失败：%s", name, kw, e)
                    message = f"{name}: {type(e).__name__}"
                    if message not in stats["failedSources"]:
                        stats["failedSources"].append(message)
                    break  # 来源不可用时不为每个关键词重复打满重试
            stats["sourceCounts"][name] = len(source_raw)
            if not source_raw and not any(x.startswith(f"{name}:") for x in stats["failedSources"]):
                stats["failedSources"].append(f"{name}: 未获取到匹配岗位")
    else:
        raw = copy.deepcopy(SEED_RAW_JOBS)
        stats["sourceCounts"] = {"seed": len(raw)}
    stats["rawCount"] = len(raw)
    if use_crawler and not raw:
        raise RuntimeError("真实招聘数据采集失败，已保留上一版数据；" + "；".join(stats["failedSources"]))
    return raw


def _infer_category(title: str, text: str) -> str:
    """从岗位名 + 描述推断分类（规则降级用）。顺序即优先级，避免误命中。"""
    t = (title + " " + text).lower()
    if any(k in t for k in ("产品经理", "产品规划", "需求分析", "用户研究")):
        return "product"
    if any(k in t for k in ("嵌入式", "物联网", "iot", "rtos", "arm", "芯片", "驱动开发")):
        return "embedded"
    # 安全先于测试：用专有词，不用「风控」这类宽泛词
    if any(k in t for k in ("渗透", "攻防", "漏洞挖掘", "漏洞复现", "安全审计", "安全体系", "网络安全", "安全工程师", "waf", "siem", "反欺诈", "风控工程师", "风险控制", "应急响应")):
        return "security"
    # 用「测试开发/自动化测试」，避免「渗透测试」误命中
    if any(k in t for k in ("测试开发", "自动化测试", "测试框架", "接口测试", "性能测试", "质量保障")):
        return "qa"
    if any(k in t for k in ("数据分析", "数据仓库", "大数据", "etl", "商业智能", "数据挖掘")):
        return "data"
    if any(k in t for k in ("前端", "用户界面", "web 前端", "vue", "react", "小程序", "h5")):
        return "frontend"
    if any(k in t for k in ("后端", "服务端", "java", "spring", "微服务", "golang")):
        return "backend"
    if any(k in t for k in ("云计算", "运维", "devops", "kubernetes", "k8s", "sre", "容器")):
        return "cloud"
    return "ai"


def _extract_one(raw: RawJob) -> dict[str, Any] | None:
    """LLM 结构化抽取；失败/不完整返回 None（跳过该岗位，不降级规则）。"""
    try:
        d = extract_job(raw)
    except LLMNotConfigured:
        raise  # 配置问题向上抛，让刷新任务整体失败
    except Exception as e:  # noqa: BLE001
        logger.warning("LLM 抽取失败（跳过该岗位）%s：%s", raw.title, e)
        return None
    if not isinstance(d, dict) or not isinstance(d.get("name"), str) or not d["name"].strip():
        return None
    d = copy.deepcopy(d)
    for field in ("mustSkills", "bonusSkills", "duties"):
        value = d.get(field, [])
        if not isinstance(value, list) or any(not isinstance(s, str) or not s.strip() for s in value):
            return None
        d[field] = list(dict.fromkeys(s.strip() for s in value))
    if d.get("categoryId") not in CATEGORY_IDS:
        return None
    for field in ("education", "experience"):
        if d.get(field) is not None and not isinstance(d[field], str):
            return None
    for field in ("salaryMin", "salaryMax"):
        value = d.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)):
            return None
    if not (d.get("mustSkills") or d.get("bonusSkills")):
        logger.warning("LLM 抽取不完整（跳过该岗位）：%s", raw.title)
        return None
    # 薪资以来源的明确数值为准，面议/缺失时不能采用模型猜测的区间。
    d["salaryMin"], d["salaryMax"] = _normalize_salary(raw.salary_min, raw.salary_max)
    d["name"] = d["name"].strip()
    d.update(_city=raw.city, _source=raw.source, _url=raw.url, _publishedAt=raw.published_at,
             _extra=copy.deepcopy(raw.extra), _rawDescription=raw.description)
    return d


def _extraction_key(raw: RawJob) -> str:
    from .prompts import EXTRACT_PROMPT
    # 正文与配置/提示词变更才重新付费；首次/末次采集时间不参与哈希。
    data = {"job": raw.to_dict(), "prompt": EXTRACT_PROMPT, "model": config.LLM_MODEL,
            "baseUrl": config.LLM_BASE_URL, "categories": CATEGORY_DESC, "schema": 3}
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def _pipeline_fingerprint(raw_jobs: list[RawJob]) -> str:
    """比较已发布版本的完整证据与模型输入，不能用本轮存档增量代表发布状态。"""
    from .prompts import JOB_PROFILE_PROMPT
    data = {
        "extractions": sorted(_extraction_key(raw) for raw in raw_jobs),
        "profilePrompt": JOB_PROFILE_PROMPT,
        "embedding": {"model": config.EMBEDDING_MODEL, "baseUrl": config.DASHSCOPE_BASE_URL,
                      "dimensions": config.EMBEDDING_DIM},
        "schema": 1,
    }
    return hashlib.sha256(json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def extract_all(
    raw_jobs: list[RawJob],
    progress: Callable[[int, int], None] | None = None,
    workers: int = 8,
    stats: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """LLM 结构化抽取（并发）；失败岗位跳过并记录。返回 (结果, 失败岗位名列表)。"""
    n = len(raw_jobs)
    if n == 0:
        return [], []
    out: list[dict[str, Any] | None] = [None] * n
    failed: list[str] = []
    done = 0
    cache: dict[str, Any] = {}
    if EXTRACTION_CACHE_PATH.exists():
        try:
            loaded = json.loads(EXTRACTION_CACHE_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                cache = loaded
        except (ValueError, OSError):
            logger.warning("结构化抽取缓存不可读，本轮重新抽取")
    keys = [_extraction_key(raw) for raw in raw_jobs]
    pending = []
    for i, key in enumerate(keys):
        if isinstance(cache.get(key), dict):
            # 命中旧正文也要刷新其使用顺序
            cached = cache.pop(key)
            cache[key] = cached
            out[i] = copy.deepcopy(cached)
            done += 1
        else:
            pending.append(i)
    if stats is not None:
        stats["reusedCount"] = done
        stats["retainedExtractionCount"] = 0
    last_success = {(entry.get("_source"), entry.get("_url")): entry for entry in cache.values()
                    if isinstance(entry, dict) and entry.get("_url")}
    with ThreadPoolExecutor(max_workers=min(workers, n)) as ex:
        futs = {ex.submit(_extract_one, raw_jobs[i]): i for i in pending}
        for fut in as_completed(futs):
            i = futs[fut]
            res = fut.result()  # LLMNotConfigured 在此向上抛
            if res is None:
                failed.append(raw_jobs[i].title)
                raw = raw_jobs[i]
                previous_result = last_success.get((raw.source, raw.url)) if raw.url else None
                if previous_result:
                    # 只复用旧正文对应的旧抽取，不能把旧技能伪装为新正文的提取结果。
                    res = copy.deepcopy(previous_result)
                    if stats is not None:
                        stats["retainedExtractionCount"] += 1
            else:
                cache[keys[i]] = copy.deepcopy(res)
            out[i] = res
            done += 1
            if progress:
                progress(done, n)
    # 只缓存成功输出；失败样本下一次重试，不把失败固定下来。
    _write_json(EXTRACTION_CACHE_PATH, cache)
    return [d for d in out if d is not None], failed


def _skill_levels(must: list[str], bonus: list[str]) -> dict[str, list[dict[str, str]]]:
    """把 must/bonus 技能分配到 junior/mid/senior，使每个等级尽量都有 3 项。"""
    must = must or []
    bonus = bonus or []
    junior = must[:3]
    mid = must[3:6]
    senior = bonus[:3] or must[6:9]
    # 高级为空时把中级尾部技能上提
    if not senior and len(mid) >= 2:
        senior = [mid[-1]]
        mid = mid[:-1]
    return {
        "junior": [{"name": s, "stack": _infer_stack(s)} for s in junior],
        "mid": [{"name": s, "stack": _infer_stack(s)} for s in mid],
        "senior": [{"name": s, "stack": _infer_stack(s)} for s in senior],
    }


def normalize_education(edu: str) -> str:
    """统一学历表述：把「本科及以上学历」「本科以上」等归一到「本科及以上」等枚举值。"""
    e = (edu or "").strip()
    if not e or "不限" in e:
        return "不限"
    # 去掉「学历/学位/毕业」后缀，再按学位关键字归一
    e = re.sub(r"(学历|学位|毕业)$", "", e).strip()
    for key, canon in (("博士", "博士及以上"), ("硕士", "硕士及以上"), ("本科", "本科及以上"), ("大专", "大专及以上")):
        if key in e:
            return canon
    # 未识别的表述原样返回
    return e


def _normalize_salary(lo: float | None, hi: float | None) -> tuple[float | None, float | None]:
    """保留来源中的真实金额；缺失、非有限、非正或倒挂的区间留空。"""
    if any(isinstance(value, bool) or not isinstance(value, (int, float))
           or not math.isfinite(value) or value <= 0 for value in (lo, hi)):
        return None, None
    return (lo, hi) if lo <= hi else (None, None)


def _aggregate(extracted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按岗位名聚合多个 JD 样本：技能交叉验证、字段取众数，输出去重后的岗位定义。"""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for d in extracted:
        groups[d["name"]].append(d)

    out: list[dict[str, Any]] = []
    for name, items in groups.items():
        n = len(items)
        # 样本 ≥3 时支持度 ≥2，否则全保留
        min_support = 2 if n >= 3 else 1
        must = cross_validate_skills([d.get("mustSkills", []) or [] for d in items], min_support=min_support)
        bonus = cross_validate_skills([d.get("bonusSkills", []) or [] for d in items], min_support=min_support)
        # 交叉验证全部过滤时退化为并集
        if not must and not bonus:
            must = list(dict.fromkeys(s for d in items for s in (d.get("mustSkills") or [])))
            bonus = list(dict.fromkeys(s for d in items for s in (d.get("bonusSkills") or [])))
        duties = next((d.get("duties") or [] for d in items if d.get("duties")), [])
        education = normalize_education(Counter(d.get("education") or "" for d in items).most_common(1)[0][0])
        # 经验取众数，未给出时留空串
        experience = Counter(d.get("experience") or "" for d in items).most_common(1)[0][0]
        category_id = Counter(d.get("categoryId") or "" for d in items).most_common(1)[0][0] or "ai"
        # 薪资取中位数，再清洗尾数/退化区间
        sals = [(d.get("salaryMin") or 0, d.get("salaryMax") or 0) for d in items]
        sals = [s for s in sals if s[1] > 0]
        if sals:
            salary_min = sorted(s[0] for s in sals)[len(sals) // 2]
            salary_max = sorted(s[1] for s in sals)[len(sals) // 2]
        else:
            salary_min, salary_max = None, None  # 无样本给出薪资，不臆造
        salary_min, salary_max = _normalize_salary(salary_min, salary_max)
        # 城市分布：剔除空城市；全空则留空
        city_counter: Counter[str] = Counter(
            c for d in items if (c := (d.get("_city") or "").strip())
        )
        city_dist = [{"city": c, "count": cnt} for c, cnt in city_counter.most_common(3)]
        companies = {str((d.get("_extra") or {}).get("company") or "").strip() for d in items}
        companies.discard("")
        out.append(
            {
                "name": name,
                "categoryId": category_id,
                "duties": duties,
                "mustSkills": must,
                "bonusSkills": bonus,
                "education": education,
                "experience": experience,
                "salaryMin": salary_min,
                "salaryMax": salary_max,
                "cityDistribution": city_dist,
                "companyCount": len(companies) if companies else None,
                "sampleCount": n,
                "_source": "、".join(sorted({d.get("_source") for d in items if d.get("_source")})),
                "evidence": [{"source": d.get("_source"), "url": d.get("_url"),
                              "publishedAt": d.get("_publishedAt"), "company": (d.get("_extra") or {}).get("company", "")}
                             for d in items if d.get("_source") not in (None, "", "seed")],
                "rawDescriptions": [d.get("_rawDescription") or "" for d in items],
            }
        )
    return out


# 新兴岗位候选：人工提供萌芽方向种子，LLM 生成规范定义；薪资为现实月薪区间（K/月）
NEW_JOB_CANDIDATES: list[dict[str, Any]] = [
    {"name": "AI智能体开发工程师", "salaryMin": 20, "salaryMax": 45, "seed": "负责基于大语言模型的智能体（Agent）系统设计与开发，涵盖多智能体协作、工具调用、任务规划、记忆管理与评测，融合 RAG、LangChain 等技术栈。"},
    {"name": "大模型安全评测工程师", "salaryMin": 20, "salaryMax": 40, "seed": "负责大语言模型的安全评测与对齐，包括红队测试、内容安全、越狱防护、价值观对齐、偏见检测与对抗样本评估，保障模型安全合规。"},
    {"name": "合成数据工程师", "salaryMin": 18, "salaryMax": 35, "seed": "负责面向大模型训练的合成数据生成、质量评估与数据飞轮建设，涵盖数据生成管线、去噪去重、难例挖掘与配比优化。"},
    {"name": "AI数据标注质量专家", "salaryMin": 10, "salaryMax": 20, "seed": "负责大模型训练数据的标注规范制定、质检体系搭建与质量度量，保障多源数据标注一致性与可用性，支撑 RLHF 与 SFT 数据生产。"},
    {"name": "多模态系统工程师", "salaryMin": 20, "salaryMax": 45, "seed": "负责多模态大模型（文本、图像、语音、视频）的系统集成、推理优化与工程落地，涵盖多模态对齐、跨模态检索与端侧部署。"},
]


def _discover_one(cand: dict[str, Any]) -> dict[str, Any] | None:
    """为单个新兴岗位候选生成规范定义，低置信度/失败返回 None。"""
    try:
        d = generate_job_definition(cand["name"], cand["seed"])
    except LLMNotConfigured:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("新岗位定义生成失败 %s：%s", cand["name"], e)
        d = None
    if not d or not d.get("name"):
        return None
    try:
        confidence = float(d.get("confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    if confidence < 0.5:
        return None
    summary = d.get("summary") or ""
    # 分类优先采用 LLM 判断，未返回合法分类时回退规则推断
    cat = d.get("categoryId")
    if cat not in CATEGORY_IDS:
        cat = _infer_category(d["name"], summary)
    return {
        "name": d["name"],
        "categoryId": cat,
        "duties": d.get("duties") or [],
        "mustSkills": d.get("mustSkills") or [],
        "bonusSkills": d.get("bonusSkills") or [],
        # 新岗位无 JD 样本，学历/经验留空
        "education": None,
        "experience": None,
        # 薪资取人工给定的参考区间，未给定则留空
        "salaryMin": cand.get("salaryMin"),
        "salaryMax": cand.get("salaryMax"),
        "cityDistribution": [],
        "companyCount": None,
        "sampleCount": 1,
        "_isNew": True,
        "_confidence": round(confidence, 2),
        "_summary": summary,
        "_scenarios": d.get("scenarios") or [],
        "_source": "多源数据挖掘",
    }


def discover_new_job_defs(workers: int = 5) -> list[dict[str, Any]]:
    """固定人工候选不能证明存在真实招聘，默认不再自动生成或发布。"""
    return []


def recent_periods(now: datetime | None = None) -> tuple[str, str]:
    """按当前日期计算「最近两个半年」的周期标签 (较早期, 较近期)。"""
    now = now or datetime.now()
    year = now.year
    if now.month <= 6:
        return (f"{year - 1}下半年", f"{year}上半年")
    return (f"{year}上半年", f"{year}下半年")


def _capability_change_one(
    j: dict[str, Any],
    must_bonus: dict[str, tuple[list[str], list[str]]],
) -> list[dict[str, Any]]:
    """为单个岗位生成能力演化记录（真实 LLM）；失败返回 []（该岗位无演化记录，不降级规则）。"""
    mb = must_bonus.get(j["id"], ([], []))
    prog = _skill_levels(mb[0], mb[1])
    junior = [s["name"] for s in prog["junior"]]
    mid = [s["name"] for s in prog["mid"]]
    senior = [s["name"] for s in prog["senior"]]
    period1, period2 = recent_periods()
    try:
        per_job = generate_capability_change(j["name"], junior, mid, senior, period1, period2)
    except LLMNotConfigured:
        raise
    except Exception as e:  # noqa: BLE001
        logger.warning("能力演化 LLM 生成失败 %s：%s", j["name"], e)
        return []
    if not per_job:
        return []
    return [
        {
            "period": c["period"],
            "jobId": j["id"],
            "addedSkills": c["addedSkills"],
            "removedSkills": c["removedSkills"],
            "importanceUp": c["importanceUp"],
            "importanceDown": c["importanceDown"],
        }
        for c in per_job
    ]


def generate_capability_changes(
    jobs: list[dict[str, Any]],
    must_bonus: dict[str, tuple[list[str], list[str]]],
    progress: Callable[[int, int], None] | None = None,
    workers: int = 8,
) -> list[dict[str, Any]]:
    """为每个岗位生成能力演化记录（并发；真实 LLM，失败跳过）。progress(done, total) 供进度回调。"""
    n = len(jobs)
    if n == 0:
        return []
    changes: list[dict[str, Any]] = []
    done = 0
    with ThreadPoolExecutor(max_workers=min(workers, n)) as ex:
        futs = {ex.submit(_capability_change_one, j, must_bonus): i for i, j in enumerate(jobs)}
        for fut in as_completed(futs):
            changes.extend(fut.result())
            done += 1
            if progress:
                progress(done, n)
    return changes


def build_knowledge(
    extracted: list[dict[str, Any]],
    progress: Callable[[int, int], None] | None = None,
    previous: dict[str, Any] | None = None,
    infer_changes: bool = True,
) -> dict[str, Any]:
    """把抽取结果组装成对齐前端结构的知识库 JSON。progress(done, total) 在能力演化阶段回调。"""
    aggregated = _aggregate(extracted)
    # LLM 生成新兴岗位定义，追加到聚合结果统一组装
    n_old = len(aggregated)
    existing_names = {d["name"] for d in aggregated}
    aggregated.extend(d for d in discover_new_job_defs() if d["name"] not in existing_names)
    old_ids = {j["name"]: str(j["id"]) for j in (previous or {}).get("jobs", [])}
    old_jobs = {j["name"]: j for j in (previous or {}).get("jobs", [])}

    jobs: list[dict[str, Any]] = []
    must_bonus: dict[str, tuple[list[str], list[str]]] = {}
    discovery_log: list[dict[str, Any]] = []
    today = datetime.now().strftime("%Y-%m-%d")

    for idx, d in enumerate(aggregated, start=1):
        jid = old_ids.get(d["name"]) or "j-" + hashlib.sha256(d["name"].encode("utf-8")).hexdigest()[:20]
        skills = (d["mustSkills"] or []) + (d["bonusSkills"] or [])
        must_bonus[jid] = (d["mustSkills"], d["bonusSkills"])
        duties = d["duties"] or []
        prior_job = old_jobs.get(d["name"]) or {}
        is_new = bool(prior_job.get("isNew")) or idx > n_old or (bool(previous) and d["name"] not in old_ids and bool(d.get("evidence")))
        discovery_date = prior_job.get("discoveredDate") or today
        jobs.append(
            {
                "id": jid,
                "name": d["name"],
                "categoryId": d["categoryId"],
                "salaryMin": d["salaryMin"],
                "salaryMax": d["salaryMax"],
                "salaryUnit": "K/月",
                "description": d.get("_summary") or ("；".join(duties[:3]) if duties else d["name"]),
                "tags": skills[:3],
                # 热度：老岗位由样本数派生，新岗位无样本依据留 None
                "hotScore": None if is_new else min(60 + d["sampleCount"] * 8, 99),
                "isNew": is_new,
                "source": d.get("_source") or None,
                "confidence": d.get("_confidence") if is_new else None,
                "discoveredDate": discovery_date if is_new else None,
                "companyCount": d.get("companyCount"),
                "trend": None,  # 无趋势数据源，不编造
                "skills": skills,
                "observedSkills": list(dict.fromkeys(skills)) if d.get("evidence") else None,
                "cityDistribution": d["cityDistribution"],
                "sampleCount": d["sampleCount"],
                "evidence": d.get("evidence") or [],
            }
        )
        if is_new:
            discovery_log.append(
                {
                    "date": discovery_date,
                    "jobName": d["name"],
                    "jobId": jid,
                    "source": d.get("_source") or "多源数据挖掘",
                    "confidence": d.get("_confidence"),
                    "description": d.get("_summary") or (duties[0] if duties else ""),
                }
            )

    # 能力演化记录：LLM 生成，失败的岗位无轨迹
    capability_changes = generate_capability_changes(jobs, must_bonus, progress=progress) if infer_changes else []

    return {
        "version": datetime.now().isoformat(timespec="seconds"),
        "meta": {"jobCount": len(jobs), "source": "crawler+llm"},
        "jobs": jobs,
        "categories": [
            {"id": cid, "name": cn, "icon": ""}
            for cid, cn in CATEGORY_NAMES.items()
            if cid in CATEGORY_IDS
        ],
        "jobDetailNotes": {j["id"]: j["description"] for j in jobs},
        "jobRequirements": {
            jid: {"education": d["education"], "experience": d["experience"]}
            for jid, d in zip((j["id"] for j in jobs), aggregated)
        },
        "jobIntro": {
            jid: {"duties": d["duties"], "scenarios": d.get("_scenarios") or []}
            for jid, d in zip((j["id"] for j in jobs), aggregated)
        },
        "jobEvidence": {
            job["id"]: [{**evidence, "text": text} for evidence, text in zip(d.get("evidence") or [], d.get("rawDescriptions") or [])]
            for job, d in zip(jobs, aggregated)
        },
        "jobSkillProgression": {
            jid: _skill_levels(must_bonus[jid][0], must_bonus[jid][1]) for jid in must_bonus
        },
        "graph": build_graph(jobs, must_bonus),
        "capabilityChanges": capability_changes,
        "discoveryLog": discovery_log,
    }


def build_job_relations(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """生成 job→job 关系边：advanced（垂直晋升阶梯）+ transfer（横向换岗，技能重叠≥2）。"""
    edges: list[dict[str, Any]] = []
    by_name = {j["name"]: j for j in jobs}

    for lower, upper in JOB_LADDERS:
        a, b = by_name.get(lower), by_name.get(upper)
        if a and b:
            edges.append(
                {
                    "source": f"job-{a['id']}",
                    "target": f"job-{b['id']}",
                    "label": "晋升",
                    "weight": 2,
                    "relation": "advanced",
                }
            )

    # 横向换岗：不同分类 + 技能重叠 ≥2
    skill_by_id = {j["id"]: set(j.get("skills") or []) for j in jobs}
    cat_by_id = {j["id"]: j["categoryId"] for j in jobs}
    candidates: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for i, a in enumerate(jobs):
        for b in jobs[i + 1:]:
            if cat_by_id[a["id"]] == cat_by_id[b["id"]]:
                continue
            shared = len(skill_by_id[a["id"]] & skill_by_id[b["id"]])
            if shared >= 2:
                candidates[a["id"]].append((shared, b["id"]))
                candidates[b["id"]].append((shared, a["id"]))

    seen: set[tuple[str, str]] = set()
    for jid, cands in candidates.items():
        cands.sort(key=lambda x: (-x[0], x[1]))
        for shared, other in cands[:2]:
            key = tuple(sorted((f"job-{jid}", f"job-{other}")))
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                {
                    "source": key[0],
                    "target": key[1],
                    "label": "换岗",
                    "weight": 1,
                    "relation": "transfer",
                }
            )
    return edges


def build_graph(
    jobs: list[dict[str, Any]],
    must_bonus: dict[str, tuple[list[str], list[str]]],
) -> dict[str, Any]:
    """从 jobs 派生图谱节点与边（job 节点 + skill 节点 + core/optional 边 + job→job 关系边）。"""
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    skill_ids: dict[str, str] = {}

    def skill_node(s: str) -> str:
        if s not in skill_ids:
            sid = f"skill-{len(skill_ids) + 1}"
            skill_ids[s] = sid
            nodes.append(
                {
                    "id": sid,
                    "label": s,
                    "type": "skill",
                    "techStack": _infer_stack(s),
                    "size": 20,
                }
            )
        return skill_ids[s]

    for j in jobs:
        nodes.append(
            {
                "id": f"job-{j['id']}",
                "jobId": j["id"],
                "label": j["name"],
                "type": "job",
                "category": j["categoryId"],
                "techStack": j["categoryId"],
                "size": 28,
                "isNew": j.get("isNew", False),
            }
        )
        must, bonus = must_bonus.get(j["id"], ([], []))
        for s in must:
            edges.append(
                {
                    "source": f"job-{j['id']}",
                    "target": skill_node(s),
                    "label": "核心",
                    "weight": 2,
                    "relation": "core",
                    "evidenceKind": (j.get("skillEvidence") or {}).get(s, "unverified"),
                }
            )
        for s in bonus:
            edges.append(
                {
                    "source": f"job-{j['id']}",
                    "target": skill_node(s),
                    "label": "加分",
                    "weight": 1,
                    "relation": "optional",
                    "evidenceKind": (j.get("skillEvidence") or {}).get(s, "unverified"),
                }
            )
    # 垂直晋升 + 横向换岗的 job→job 边
    edges.extend(build_job_relations(jobs))
    return {"nodes": nodes, "edges": edges}


def index_vectors(knowledge: dict[str, Any]) -> str | None:
    """把岗位知识片段 embedding 写入 ChromaDB（供 RAG 检索）；jobs 为空时不重建集合。"""
    jobs = knowledge.get("jobs", []) or []
    if not jobs:
        logger.warning("无岗位可向量化，保留既有向量集合不动")
        return
    job_intro = knowledge.get("jobIntro") or {}
    job_req = knowledge.get("jobRequirements") or {}
    job_prog = knowledge.get("jobSkillProgression") or {}
    ids, texts, metas = [], [], []
    for j in jobs:
        jid = j["id"]
        intro = job_intro.get(jid) or {}
        req = job_req.get(jid) or {}
        prog = job_prog.get(jid) or {}
        duties = "；".join(intro.get("duties") or [])
        scen = "；".join(s.get("name", "") for s in (intro.get("scenarios") or []) if isinstance(s, dict))
        skill_names: list[str] = []
        for lv in ("junior", "mid", "senior"):
            skill_names += [s["name"] if isinstance(s, dict) else str(s) for s in (prog.get(lv) or [])]
        parts = [
            j["name"],
            f"职责：{duties}" if duties else "",
            f"场景：{scen}" if scen else "",
            f"任职要求：学历 {req.get('education', '')}，经验 {req.get('experience', '')}",
            f"技能：{'、'.join(skill_names) or ', '.join(j.get('skills', []) or [])}",
        ]
        text = " ".join(p for p in parts if p)
        ids.append(jid)
        texts.append(text)
        metas.append({"source": f"job-{jid}", "name": j["name"]})
        for number, evidence in enumerate((knowledge.get("jobEvidence") or {}).get(jid) or []):
            raw_text = evidence.get("text") or ""
            if not raw_text:
                continue
            for offset in range(0, len(raw_text), 1800):
                ids.append(f"{jid}-jd-{number}-{offset}")
                texts.append(raw_text[offset:offset + 1800])
                metas.append({"source": evidence.get("source") or "", "url": evidence.get("url") or "",
                              "publishedAt": evidence.get("publishedAt") or "", "jobId": jid, "kind": "recruitment", "name": j["name"]})
    embs: list[list[float]] = []
    for start in range(0, len(texts), 10):
        embs.extend(embed(texts[start:start + 10], credentials=settings.embed_credentials()))
    if len(embs) != len(ids) or any(not row or any(not isinstance(v, (int, float)) or not math.isfinite(v) for v in row) for row in embs):
        raise RuntimeError("向量模型返回数量或格式不完整，未发布本轮数据")
    collection_name = "jd_fragments_v_" + uuid.uuid4().hex
    try:
        store.create_vector_collection(collection_name)
        store.upsert_fragments(ids, texts, metas, embs, collection_name=collection_name)
    except Exception:
        try:
            store.delete_vector_collection(collection_name)
        except Exception:
            logger.warning("未发布向量集合清理失败：%s", collection_name)
        raise
    logger.info("已向量化 %d 条岗位片段", len(ids))
    return collection_name


def publish_knowledge(knowledge: dict[str, Any]) -> None:
    """准备不可变向量集合，再原子提交包含集合名的完整快照。"""
    collection_name = index_vectors(knowledge)
    if not collection_name:
        raise RuntimeError("没有可发布的向量数据，已保留旧版本")
    knowledge.setdefault("meta", {})["vectorCollection"] = collection_name
    try:
        store.save_snapshot(knowledge)
    except Exception:
        try:
            store.delete_vector_collection(collection_name)
        except Exception:
            logger.warning("未发布集合清理失败：%s", collection_name)
        raise


def main(
    use_crawler: bool = True,
    progress: Callable[[str, int], None] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    from .enrich import enrich_knowledge

    def report(stage: str, pct: int) -> None:
        if progress:
            progress(stage, pct)

    previous = store.load_latest_snapshot() or {}
    stats: dict[str, Any] = {}
    report("采集原始 JD", 3)
    raw = collect_raw(use_crawler=use_crawler, stats=stats)
    stats["rawCount"] = len(raw)
    stats["duplicateCount"] = len(raw) - len({job_identity(job) for job in raw})
    report("清洗数据", 18)
    cleaned = clean_pipeline(raw)
    stats["cleanedCount"] = len(cleaned)
    if not cleaned:
        raise RuntimeError("本轮真实招聘数据清洗后无有效 JD，已保留上一版数据")
    # 存档保留原始证据，供下次重试
    archive_jds(cleaned, stats=stats)
    cumulative = load_archived_jobs() if use_crawler else cleaned
    pipeline_fingerprint = _pipeline_fingerprint(cumulative)
    previous_meta = previous.get("meta") or {}
    if (use_crawler and previous_meta.get("mode") == "real" and previous_meta.get("vectorCollection")
            and previous_meta.get("skillEvidenceVersion") == 1
            and not previous_meta.get("failedJobs") and not previous_meta.get("failedProfiles")
            and previous_meta.get("pipelineFingerprint") == pipeline_fingerprint):
        knowledge = copy.deepcopy(previous)
        stats.update(unchanged=True, reusedCount=stats["archiveCount"])
        knowledge["meta"]["crawlStats"] = stats
        report("刷新完成", 100)
        return knowledge, []
    report("LLM 结构化抽取", 25)
    extracted, failed_jobs = extract_all(cumulative, stats=stats,
        progress=lambda done, total: report("LLM 结构化抽取", 25 + int(done / total * 30)))
    if not extracted:
        raise RuntimeError(f"本轮未抽取到任何岗位（{len(cumulative)} 条 JD），已保留原有数据")
    report("组装知识库", 58)
    knowledge = build_knowledge(extracted, previous=previous, infer_changes=False)
    if not knowledge.get("jobs"):
        raise RuntimeError("本轮未形成任何岗位，已保留原有数据")
    knowledge["meta"].update(source="crawler+llm" if use_crawler else "seed+llm",
        mode="real" if use_crawler else "demo", crawlStats=stats,
        pipelineFingerprint=pipeline_fingerprint,
        capabilityChangesKind="unavailable", failedJobs=failed_jobs, failedProfiles=[])
    # 演化不能由当前技能反推成历史事实；真实历史样本不足时明确无记录。
    report("岗位画像富化", 62)
    knowledge, failed_profiles = enrich_knowledge(knowledge, previous=previous,
        progress=lambda stage, pct: report(stage, 62 + int(pct * 0.24)))
    knowledge["meta"]["failedProfiles"] = failed_profiles
    if not knowledge.get("jobs"):
        raise RuntimeError("没有完成有效岗位画像，已保留上一版数据；失败岗位：" + "、".join(failed_profiles[:10]))
    report("向量化索引", 88)
    publish_knowledge(knowledge)
    report("刷新完成", 100)
    return knowledge, failed_jobs


if __name__ == "__main__":
    main()

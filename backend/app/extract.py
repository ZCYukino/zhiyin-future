"""LLM 结构化抽取与生成：JD 抽取、新岗位定义、岗位能力演化轨迹。

- 结构化抽取用 DeepSeek（deepseek-flash）
- RAG 检索增强用于岗位定义，防控"幻觉"，并输出可溯源引用
"""
from __future__ import annotations

import logging
from typing import Any

from . import config, settings
from .crawler.base import RawJob
from .llm import generate_json
from .prompts import CAPABILITY_CHANGE_PROMPT, EXTRACT_PROMPT, JOB_DEF_PROMPT
from .rag import build_context

logger = logging.getLogger("extract")

# 9 类岗位分类（全站唯一事实来源；对齐前端 jobCategories / techStacksForGraph）
CATEGORIES: list[dict[str, str]] = [
    {"id": "ai", "name": "人工智能", "icon": "cpu", "description": "大模型、NLP、深度学习、计算机视觉等算法研发方向"},
    {"id": "backend", "name": "后端开发", "icon": "monitor", "description": "服务端架构、微服务、数据库、API 与分布式系统"},
    {"id": "frontend", "name": "前端开发", "icon": "picture", "description": "Web、移动端与跨端应用开发，用户体验与工程化"},
    {"id": "data", "name": "数据科学", "icon": "odometer", "description": "数据仓库、ETL、大数据平台、数据分析与可视化"},
    {"id": "cloud", "name": "云计算与运维", "icon": "set-up", "description": "容器编排、DevOps、CI/CD 与云基础设施"},
    {"id": "security", "name": "信息安全", "icon": "lock", "description": "网络安全、渗透测试、安全合规与红蓝对抗"},
    {"id": "embedded", "name": "嵌入式与物联网", "icon": "cpu", "description": "嵌入式软件、物联网、芯片与软硬件协同"},
    {"id": "product", "name": "产品与项目", "icon": "guide", "description": "产品规划、需求管理、项目推进与运营"},
    {"id": "qa", "name": "测试与质量", "icon": "finished", "description": "自动化测试、性能测试、质量保障与工程效能"},
]
CATEGORY_IDS = [c["id"] for c in CATEGORIES]
CATEGORY_NAMES = {c["id"]: c["name"] for c in CATEGORIES}

# 分类定义描述（供 LLM 分类 prompt 使用）：给出每类的名称与边界，避免只给 id 导致 LLM 瞎猜误分类
CATEGORY_DESC = "；".join(f"{c['id']}={c['name']}（{c['description']}）" for c in CATEGORIES)


def _infer_stack(name: str) -> str:
    """技能名 → 技术栈（与 matching/前端 inferStackFromName 对齐的唯一实现）。"""
    s = name.lower()
    if any(k in s for k in ("python", "pytorch", "tensorflow", "transformer", "transformers", "bert", "diffusion", "cuda", "rag", "agent", "langchain", "langgraph", "autogen", "crewai", "llm", "nlp", "自然语言处理", "计算机视觉", "语音识别", "机器学习", "深度学习", "大模型", "多智能体", "推理", "端侧")):
        return "ai"
    if any(k in s for k in ("java", "spring", "go", "golang", "mysql", "redis", "kafka", "微服务", "后端")):
        return "backend"
    if any(k in s for k in ("vue", "react", "typescript", "css", "webpack", "node", "前端")):
        return "frontend"
    if any(k in s for k in ("sql", "etl", "elt", "tableau", "excel", "spark", "flink", "hadoop", "数据", "挖掘", "标注", "质检", "dama", "cvat", "label studio", "scale ai", "iaa")):
        return "data"
    if any(k in s for k in ("kubernetes", "k8s", "docker", "jenkins", "terraform", "linux", "devops", "云原生")):
        return "cloud"
    if any(k in s for k in ("waf", "siem", "cissp", "等保", "安全", "渗透")):
        return "security"
    if any(k in s for k in ("rtos", "arm", "嵌入式", "c++", "驱动")):
        return "embedded"
    if any(k in s for k in ("产品", "用户研究", "项目", "prd", "需求", "用户故事", "竞品", "可行性", "协作", "优先级", "敏捷", "pmp")):
        return "product"
    if any(k in s for k in ("selenium", "jmeter", "测试")):
        return "qa"
    return "tool"

# ===== 1. JD 结构化抽取 =====


def extract_job(raw: RawJob) -> dict[str, Any] | None:
    """从单条原始 JD 抽取结构化岗位信息。"""
    prompt = EXTRACT_PROMPT.format(
        title=raw.title,
        city=raw.city,
        salary=raw.salary,
        description=raw.description[:3000],
        categories=CATEGORY_DESC,
    )
    return generate_json(
        prompt,
        system="你是严谨的岗位数据分析助手。",
        model=config.LLM_MODEL,
        temperature=0.0,
        credentials=settings.system_llm_credentials(),
    )


# ===== 2. 新岗位定义生成（RAG 增强）=====


def generate_job_definition(name: str, seed_text: str = "") -> dict[str, Any] | None:
    """生成新岗位定义（含岗位名称/职责/必备/加分/应用场景）。"""
    context = build_context(name, top_k=6)
    if not context:
        # RAG 无命中 → 回退到内置岗位种子描述（人工撰写的真实 JD 文本，仍由 LLM 生成定义，
        # 非编造输出）。此处必须留痕：否则「向量库为空」会被误读为「新岗位无需检索」。
        logger.warning("RAG 未返回任何 JD 片段，回退到内置种子描述：%s", name)
        context = seed_text
    if not context:
        return None
    prompt = JOB_DEF_PROMPT.format(name=name, context=context[:4000], categories=CATEGORY_DESC)
    return generate_json(
        prompt,
        system="你是严谨的岗位研究助手。",
        model=config.LLM_MODEL,
        credentials=settings.system_llm_credentials(),
    )


# ===== 3. 岗位能力演化轨迹生成（赛题②：近两年技能新增/淘汰/重要性变化）=====


def generate_capability_change(
    job_name: str,
    junior: list[str],
    mid: list[str],
    senior: list[str],
    period1: str,
    period2: str,
) -> list[dict[str, Any]] | None:
    """为单个岗位生成最近一年能力演化轨迹（2 期，周期由调用方按当前日期动态传入），失败返回 None。"""
    prompt = CAPABILITY_CHANGE_PROMPT.format(
        job_name=job_name,
        junior="、".join(junior) or "无",
        mid="、".join(mid) or "无",
        senior="、".join(senior) or "无",
        period1=period1,
        period2=period2,
    )
    data = generate_json(
        prompt,
        system="你是严谨的岗位演化分析助手。",
        model=config.LLM_MODEL,
        credentials=settings.system_llm_credentials(),
    )
    changes = data.get("changes") if isinstance(data, dict) else None
    if not isinstance(changes, list):
        return None
    out: list[dict[str, Any]] = []
    for c in changes:
        if not isinstance(c, dict):
            continue
        period = str(c.get("period") or "").strip()
        if not period:
            continue
        out.append(
            {
                "period": period,
                "addedSkills": [s for s in (c.get("addedSkills") or []) if isinstance(s, str)],
                "removedSkills": [s for s in (c.get("removedSkills") or []) if isinstance(s, str)],
                "importanceUp": [s for s in (c.get("importanceUp") or []) if isinstance(s, str)],
                "importanceDown": [s for s in (c.get("importanceDown") or []) if isinstance(s, str)],
            }
        )
    return out or None

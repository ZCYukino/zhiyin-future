"""人岗匹配报告：规则算分 + LLM 生成学习路径与总结，对齐前端 MatchReport 结构。"""
from __future__ import annotations

import logging
import re
from functools import lru_cache
from typing import Any

from . import settings, store
from .extract import _infer_stack
from .llm import LLMNotConfigured, generate_json
from .prompts import MATCH_PROMPT

logger = logging.getLogger("matching")

PRIORITY_ORDER = {"must": 0, "important": 1, "bonus": 2}
LEVEL_ORDER = {"junior": 0, "mid": 1, "senior": 2}
VERDICT_LABEL = {"strong": "强匹配", "fair": "较强匹配", "partial": "部分匹配", "weak": "弱匹配"}
VALID_STACKS = {"ai", "backend", "frontend", "data", "cloud", "security", "embedded", "product", "qa", "tool"}

# 技能优先级权重：必备技能决定匹配度主体，加分技能只做小幅加分
PRIORITY_WEIGHT = {"must": 1.0, "important": 0.7, "bonus": 0.4}

# 部分掌握按 60% 计分，避免措辞相近被过度拉低
PARTIAL_FACTOR = 0.6

# 覆盖率取幂后映射到 0~100：抬升低分段，保留两端点
SCORE_CURVE_EXP = 0.65

# ASCII 技能名按 token 精确匹配，避免 Java⊂JavaScript 这类子串误判
_ASCII_TOKEN_RE = re.compile(r"[a-z0-9+#.]+")
# 中文字段，只在中文之间做子串比较
_CJK_RUN_RE = re.compile("[一-鿿]+")
_SKILL_ALIASES = {
    "golang": "go",
    "csharp": "c#",
    "cxx": "c++",
    "cpp": "c++",
    "cplusplus": "c++",
    "k8s": "kubernetes",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "nodejs": "node",
    # node.js 必须单独归一，否则与 nodejs 对不上
    "node.js": "node",
    "vuejs": "vue",
    "vue.js": "vue",
    "postgres": "postgresql",
}
# 去掉点/连字符后相等视为同词；只对长度≥3 的 token 生效
_TOKEN_SEP_RE = re.compile(r"[.\-]")


def _fold_token(t: str) -> str:
    return _TOKEN_SEP_RE.sub("", t)

# LLM 生成单次超时（秒），失败不降级
MATCH_LLM_TIMEOUT = 30.0


def _as_text(v: Any) -> str:
    """把请求体里的任意值收敛成字符串，宁可当成空值也不让接口崩。"""
    if isinstance(v, str):
        return v
    if v is None or isinstance(v, (dict, list, bool)):
        return ""
    return str(v)


def normalize_skill_name(s: str) -> str:
    # 去括号注释并转小写；保留空格供 ASCII 分词使用
    return re.sub(r"[（(][^)）]*[)）]", "", s).replace("\t", " ").strip().lower()


def _ascii_tokens(s: str) -> set[str]:
    return {_SKILL_ALIASES.get(t, t) for t in _ASCII_TOKEN_RE.findall(s.lower())}


_COMPACT_RE = re.compile(r"[^a-z0-9+#]")


def _compact(s: str) -> str:
    """只留下 ASCII 字母数字（+# 保留），丢掉空格与分隔符：'Vue 3' → 'vue3'。"""
    return _COMPACT_RE.sub("", s.lower())


# 泛用 ASCII 缩写不构成技能身份，避免「AI」一词误判整项技能
_GENERIC_ASCII = frozenset({
    "ai", "ml", "dl", "llm", "api", "sdk", "ui", "ux", "os", "db",
    "it", "id", "web", "app", "dev", "ops", "demo", "proj", "sys", "code",
})


def _strong_tokens(s: str) -> set[str]:
    """可用于判定「同一项技能」的 ASCII 词：先归一化，再剔除泛用缩写。"""
    return {t for t in _ascii_tokens(s) if t not in _GENERIC_ASCII}


def _ascii_overlap(a: str, b: str) -> bool:
    """两串的 ASCII 词能否算同一个词：归一化精确相等，或去分隔符相等（node.js≡nodejs），
    或拆写相等（'vue 3'≡'vue3'）。后两条只对长度≥3 的词生效，短词按原样比对。"""
    ta, tb = _strong_tokens(a), _strong_tokens(b)
    if ta & tb:
        return True
    for x in ta:
        if len(x) < 3:
            continue
        fx = _fold_token(x)
        if len(fx) < 3:
            continue
        if any(len(y) >= 3 and fx == _fold_token(y) for y in tb):
            return True
    if len(ta) >= 2 or len(tb) >= 2:
        ca, cb = _compact(a), _compact(b)
        if len(ca) >= 3 and ca == cb:
            return True
    return False


def _cjk_only(s: str) -> str:
    """只保留中文字段，避免 ASCII 碎片污染中文比较。"""
    return "".join(_CJK_RUN_RE.findall(s))


def _longest_common_run(a: str, b: str) -> str:
    """最长公共连续子串。"""
    if not a or not b:
        return ""
    prev = [0] * (len(b) + 1)
    best, end = 0, 0
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                cur[j] = prev[j - 1] + 1
                if cur[j] > best:
                    best, end = cur[j], i
        prev = cur
    return a[end - best: end]


# 只共用一个高频构词成分不算措辞相近；比对必须是整段公共子串
_GENERIC_RUNS = frozenset({
    "数据", "设计", "开发", "控制", "分析", "系统", "功能", "计算", "管理", "部署",
    "模拟", "计算机", "网络", "技术", "平台", "应用", "能力", "经验", "流程",
    "工具", "信息", "模型", "服务", "优化", "项目", "辅助", "流程设计",
})
# 不收「测试」「结构」：同族词判 partial 是合理的

# 最长公共子串的中文字段长度上限，超长输入直接判不相关
_MAX_DP_CHARS = 120

# 看着像但不是一回事的 ASCII 前缀对
_ASCII_FALSE_PREFIX = frozenset({("java", "javascript")})


def _cjk_usable(s: str) -> bool:
    """该侧中文字段是否够格当技能证据：≥3 字，或整串纯中文。
    否则「Prompt设计」只剩 2 字后缀「设计」，会被长技能点整串包含。
    这里用 _ascii_tokens 而不是 _strong_tokens：问的是含不含 ASCII。"""
    c = _cjk_only(s)
    return bool(c) and (len(c) >= 3 or not _ascii_tokens(s))


def contains_match(a: str, b: str) -> bool:
    na, nb = a.strip().lower(), b.strip().lower()
    if not na or not nb:
        return False
    # 完全同名即同一项技能，必须前置（泛用缩写的 token 集为空）
    if na == nb:
        return True
    # ASCII 按规范化 token 精确匹配，不能因含中文就改走中文分支
    if _ascii_overlap(na, nb):
        return True
    # 中文双向子串包含，只比中文字段；被包含方须够格
    ca, cb = _cjk_only(na), _cjk_only(nb)
    if not ca or not cb:
        return False
    if ca == cb:
        # 中文字段相同还不够：岗位词带 ASCII 限定语而简历词没有时（LoRA微调←微调），
        # 简历只证明了笼统的说法，不能算掌握
        if _strong_tokens(na) and not _strong_tokens(nb):
            return False
        return True
    # ① 岗位词⊂简历词 → 更具体，算掌握
    # ② 简历词⊂岗位词 → 更笼统，只有前缀成立（复合词中心语在后）
    if len(ca) < len(cb) and ca in cb:
        return _cjk_usable(na)
    if len(cb) < len(ca) and cb in ca:
        return _cjk_usable(nb) and ca.startswith(cb)
    return False


def shared_substring(a: str, b: str) -> bool:
    na, nb = a.strip().lower(), b.strip().lower()
    if len(na) < 2 or len(nb) < 2:
        return False
    # 共享长度≥3 的前缀才判相关
    for x in _strong_tokens(na):
        for y in _strong_tokens(nb):
            if x == y:
                continue
            short, long = sorted((x, y), key=len)
            if len(short) >= 3 and long.startswith(short):
                if (short, long) in _ASCII_FALSE_PREFIX:
                    continue
                return True
    # 公共片段须占两侧总长≥20% 才算措辞相近
    ca, cb = _cjk_only(na), _cjk_only(nb)
    if not ca or not cb or not (_cjk_usable(na) and _cjk_usable(nb)):
        return False
    # 超长输入直接判不相关，挡掉 O(n·m) DP
    if len(ca) > _MAX_DP_CHARS or len(cb) > _MAX_DP_CHARS:
        return False
    run = _longest_common_run(ca, cb)
    if len(run) < 2 or len(run) * 5 < len(ca) + len(cb):
        return False
    # 排除只共用一个高频构词成分的情况
    return run not in _GENERIC_RUNS


_PAREN_RE = re.compile(r"[（(]([^)）]*)[)）]")
_INNER_SEP_RE = re.compile(r"[、,，;；/]")
# 中文并列连接词：把「A与B」这类复合技能点拆成组成项
# 用先行断言跳过词内字（如「参与」的「与」）
_CONNECTOR_RE = re.compile(
    r"(?<![参赠])与"        # 参与 / 赠与
    r"|(?<![以涉普波遍顾提及])及"  # 以及 / 涉及 / 普及 / 及时 / 提及
    r"|(?<![饱总柔温调谐平和])和"  # 饱和 / 总和 / 温和 / 调和 / 和谐 / 和平
)


def skill_parts(name: str) -> tuple[list[str], list[str]]:
    """把技能点拆成 (合取项, 举例项)。

    合取项（A与B）：两个都要，只写其一算部分。
    举例项（括号内「、」「/」枚举）：覆盖过半算完全掌握。
    括号里写「IAA与置信度建模」是合取，归合取项。
    """
    base = normalize_skill_name(name)
    conj: list[str] = []
    alts: list[str] = []

    def split_conj(text: str) -> list[str] | None:
        """全部≥2 字的组成部分才当合取拆，否则整串当原子。"""
        parts = [normalize_skill_name(p) for p in _CONNECTOR_RE.split(text) if p.strip()]
        if len(parts) > 1 and all(len(p) >= 2 for p in parts):
            return parts
        return None

    base_parts = split_conj(base)
    if base_parts:
        conj.extend(base_parts)
    for inner in _PAREN_RE.findall(name):
        for part in _INNER_SEP_RE.split(inner):
            segs = split_conj(part)
            if segs:
                conj.extend(segs)
                continue
            cand = normalize_skill_name(part)
            if len(cand) >= 2 and cand not in alts:
                alts.append(cand)
    return conj, alts


_TEXT_SEG_RE = re.compile(r"[\n\r。；;!！?？]+")
_ASCII_RUN_RE = re.compile(r"[a-z0-9+#.]+")


def text_segments(text: str) -> list[str]:
    """把简历正文切成句段：括号外主体一段、每个括号内容单独成段。

    括号会把技能点里的真正证据词隔断，不拆就扫不到；只在句段内比较，
    避免跨行拼出假词（上一行「机器」+ 下一行「学习」）。
    """
    out: list[str] = []
    for raw in _TEXT_SEG_RE.split(text or ""):
        s = raw.strip()
        if not s:
            continue
        outer = normalize_skill_name(s)
        if outer:
            out.append(outer)
        for inner in _PAREN_RE.findall(s):
            cand = normalize_skill_name(inner)
            if cand:
                out.append(cand)
    return out


@lru_cache(maxsize=1024)
def _term_span_re(term: str) -> re.Pattern[str] | None:
    """技能词编译成正文正则：ASCII 片段加词边界，中文按字面。"""
    t = normalize_skill_name(term)
    if not t:
        return None
    # 逐段拼：ASCII 段加词边界；ASCII 与中文交界处允许空白
    pos, pieces, prev_ascii = 0, [], False
    for m in _ASCII_RUN_RE.finditer(t):
        gap = t[pos:m.start()]
        if gap:
            pieces.append((r"\s*" if prev_ascii else "") + re.escape(gap))
            prev_ascii = False
        pieces.append(r"(?<![a-z0-9])" + re.escape(m.group()) + r"(?![a-z0-9])")
        pos = m.end()
        prev_ascii = True
    tail = t[pos:]
    if tail:
        pieces.append((r"\s*" if prev_ascii else "") + re.escape(tail))
    return re.compile("".join(pieces), re.IGNORECASE)


def _fragment_usable(term: str) -> bool:
    """合取/举例片段是否够格当正文直扫证据。

    2 字片段在散文里到处都是（「安全」命中「网络安全测试」），
    要求至少 3 个中文字，或带一个有辨识度的 ASCII 词。
    """
    return len(_cjk_only(term)) >= 3 or bool(_strong_tokens(term))


def _term_in_text(term: str, segments: list[str]) -> bool:
    """岗位技能词是否逐字出现在简历正文里。

    拿岗位自己的词去简历里找，不依赖前端词典覆盖面；只认逐字出现，不引入误判。
    """
    if not segments:
        return False
    rx = _term_span_re(term)
    if rx is None:
        return False
    return any(rx.search(seg) for seg in segments)


def classify_skill(req_name: str, user_skills: list[str], segments: list[str] | None = None) -> str:
    """三分类：mastered / partial / missing。

    1. 有合取项：逐字写全 → 掌握；全部覆盖 → 掌握；部分 → partial。
    2. 无合取项且本体命中 → 掌握。
    3. 举例项覆盖过半 → 掌握，命中部分 → partial。
    4. 措辞相近 → partial，否则 missing。
    """
    base = normalize_skill_name(req_name)
    conj, alts = skill_parts(req_name)
    segs = segments or []

    def hit(term: str, *, fragment: bool = False) -> bool:
        # 证据来源：前端词典技能表 + 正文逐字扫描（fragment 走直扫另有门槛）
        if any(contains_match(term, u) for u in user_skills):
            return True
        if fragment and not _fragment_usable(term):
            return False
        return _term_in_text(term, segs)

    def fuzzy() -> bool:
        return any(shared_substring(t, u) for t in [base, *conj, *alts] for u in user_skills)

    if conj:
        # 只认逐字写全，contains_match 会因前缀包含而放行
        if _term_in_text(base, segs) or any(normalize_skill_name(u) == base for u in user_skills):
            return "mastered"
        n = sum(1 for c in conj if hit(c, fragment=True))
        if n == len(conj):
            return "mastered"
        return "partial" if (n or any(hit(a, fragment=True) for a in alts) or fuzzy()) else "missing"

    if hit(base):
        return "mastered"

    if alts:
        n = sum(1 for a in alts if hit(a, fragment=True))
        # 覆盖过半即算掌握
        need = (len(alts) + 1) // 2
        if n >= need:
            return "mastered"
        if n or fuzzy():
            return "partial"
        return "missing"

    return "partial" if fuzzy() else "missing"


def priority_from_level(level: str) -> str:
    return "must" if level == "junior" else "important" if level == "mid" else "bonus"


def edu_level_of(s: str) -> int:
    if "博士" in s:
        return 4
    if "硕士" in s:
        return 3
    if "本科" in s:
        return 2
    if "大专" in s:
        return 1
    return 0


_YEAR_RANGE_RE = re.compile(r"(\d+)\s*[-~—－–至到]\s*(\d+)\s*年")
_YEAR_RE = re.compile(r"(\d+)\s*年")


def parse_years(s: str) -> int:
    """从年限描述取入职门槛：区间取下界（1-3年 → 1），其余取唯一值，未写为 0。"""
    t = s or ""
    m = _YEAR_RANGE_RE.search(t)
    if m:
        return int(m.group(1))
    m = _YEAR_RE.search(t)
    return int(m.group(1)) if m else 0


def _resolve_stack(name: str, stack: str | None) -> str:
    """归一技术栈：软技能常被误标为 tool，用 _infer_stack 重判一次。"""
    if stack in VALID_STACKS and stack != "tool":
        return stack
    inferred = _infer_stack(name)
    return inferred if inferred != "tool" else "tool"


def _llm_plan(
    job_name: str,
    mastered: list[str],
    partial: list[str],
    missing: list[str],
    credentials: settings.Credentials,
) -> dict[str, Any] | None:
    prompt = MATCH_PROMPT.format(
        job_name=job_name,
        mastered="、".join(mastered) or "（无）",
        partial="、".join(partial) or "（无）",
        missing="、".join(missing) or "（无）",
    )
    # 单次尝试 + 短超时，失败返回 None
    data = generate_json(
        prompt, system="你是严谨的职业规划师。",
        timeout=MATCH_LLM_TIMEOUT, max_retries=2, credentials=credentials,
    )
    if not data:
        return None
    return data


def build_match_report(
    job_id: str,
    user: dict[str, Any],
    credentials: settings.Credentials | None = None,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """生成匹配报告；snapshot 显式传入时用它，否则读最新快照。"""
    # 只读路径走缓存版，避免每次请求都读盘解析快照
    k = snapshot if snapshot is not None else store.load_cached_snapshot()
    jobs = k.get("jobs", []) or []
    job = next((j for j in jobs if j.get("id") == job_id), None)
    if not job:
        return None

    progression = (k.get("jobSkillProgression", {}) or {}).get(job_id)
    req = (k.get("jobRequirements", {}) or {}).get(job_id) or {}

    raw_skills = user.get("userSkills")
    if not isinstance(raw_skills, list):
        raw_skills = []
    # 元素必须是字符串，否则过滤掉
    user_skills = [u for u in raw_skills if isinstance(u, str)]
    # 简历正文：独立于词典的第二证据来源
    segments = text_segments(_as_text(user.get("resumeText")))

    specs: list[dict[str, Any]] = []
    if progression:
        for level in ("junior", "mid", "senior"):
            for s in progression.get(level, []) or []:
                name = s["name"] if isinstance(s, dict) else str(s)
                stack = _resolve_stack(name, s.get("stack") if isinstance(s, dict) else None)
                specs.append({"name": name, "stack": stack, "level": level})
    else:
        for s in job.get("skills", []) or []:
            specs.append({"name": s, "stack": _infer_stack(s), "level": "junior"})

    mastered: list[dict[str, Any]] = []
    partial: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    for spec in specs:
        status = classify_skill(spec["name"], user_skills, segments)
        item = {
            "name": spec["name"],
            "level": spec["level"],
            "stack": spec["stack"],
            "status": status,
            "priority": priority_from_level(spec["level"]),
        }
        if status == "mastered":
            mastered.append(item)
        elif status == "partial":
            partial.append(item)
        else:
            missing.append(item)

    missing.sort(key=lambda s: (PRIORITY_ORDER[s["priority"]], LEVEL_ORDER[s["level"]]))

    total_weight = sum(PRIORITY_WEIGHT[priority_from_level(s["level"])] for s in specs)
    achieved = (
        sum(PRIORITY_WEIGHT[s["priority"]] for s in mastered)
        + sum(PRIORITY_WEIGHT[s["priority"]] * PARTIAL_FACTOR for s in partial)
    )
    coverage = achieved / total_weight if total_weight else 0
    score = round(100 * coverage ** SCORE_CURVE_EXP)
    verdict = "strong" if score >= 75 else "fair" if score >= 50 else "partial" if score >= 30 else "weak"
    verdict_label = VERDICT_LABEL[verdict]

    requirements: list[dict[str, Any]] = []
    user_edu = _as_text(user.get("education"))
    user_major = _as_text(user.get("major")) or "专业未填"
    if req.get("education"):
        requirements.append(
            {
                "label": "学历",
                "user": f"{user_edu}（{user_major}）",
                "required": req["education"],
                "passed": edu_level_of(user_edu) >= edu_level_of(req["education"]),
            }
        )
    # 岗位没给要求就不合成门槛，缺就是缺
    user_exp = _as_text(user.get("resumeYears")) or _as_text(user.get("experience"))
    if req.get("experience"):
        required_years = parse_years(req["experience"])
        user_years = parse_years(user_exp)
        requirements.append(
            {"label": "经验", "user": user_exp or f"{user_years}年", "required": req["experience"], "passed": user_years >= required_years}
        )

    # 硬门槛不达标时结论最多下调一级，不封顶
    if any(not r["passed"] for r in requirements):
        _order = ["weak", "partial", "fair", "strong"]
        _idx = _order.index(verdict)
        if _idx > 0:
            verdict = _order[_idx - 1]
            verdict_label = VERDICT_LABEL[verdict]

    # 缺口 = 完全缺失 + 半掌握
    gap_skills = missing + partial
    priority_gaps = {
        "must": sum(1 for s in gap_skills if s["priority"] == "must"),
        "important": sum(1 for s in gap_skills if s["priority"] == "important"),
        "bonus": sum(1 for s in gap_skills if s["priority"] == "bonus"),
    }

    one_line_summary: str | None = None
    learning_path: list[dict[str, Any]] = []
    llm_status = "ok"
    # 凭据只接受显式传入，绝不从 body.user 解析（id 可伪造）
    cred = credentials if credentials is not None else settings.llm_credentials(None)
    if not cred.configured:
        llm_status = "no_api_key"
    else:
        try:
            llm = _llm_plan(
                job.get("name", ""),
                [s["name"] for s in mastered],
                [s["name"] for s in partial],
                [s["name"] for s in missing],
                cred,
            )
            if llm:
                if isinstance(llm.get("oneLineSummary"), str) and llm["oneLineSummary"].strip():
                    one_line_summary = llm["oneLineSummary"].strip()
                lp = llm.get("learningPath")
                if isinstance(lp, list) and lp:
                    cleaned: list[dict[str, Any]] = []
                    for st in lp:
                        steps = []
                        for step in (st.get("steps") or [])[:5]:
                            if not isinstance(step, dict) or not step.get("skill"):
                                continue
                            stack = _resolve_stack(step["skill"], step.get("stack"))
                            steps.append(
                                {
                                    "skill": step["skill"],
                                    "stack": stack,
                                    # 未给 resource/milestone 就留空
                                    "resource": step.get("resource") or "",
                                    "milestone": step.get("milestone") or "",
                                }
                            )
                        if steps:
                            cleaned.append(
                                {
                                    "stage": st.get("stage") or f"阶段 · {len(cleaned) + 1}",
                                    "period": st.get("period") or "",
                                    "focus": st.get("focus") or "",
                                    "steps": steps,
                                }
                            )
                    if cleaned:
                        learning_path = cleaned
                # 有缺口但没产出学习路径，不得谎报无缺口
                if not learning_path and (missing or partial):
                    llm_status = "failed"
            else:
                llm_status = "failed"
        except LLMNotConfigured:
            llm_status = "no_api_key"
        except Exception as e:  # noqa: BLE001
            logger.warning("LLM 学习路径生成失败：%s", e)
            llm_status = "failed"

    return {
        "score": score,
        "verdict": verdict,
        "verdictLabel": verdict_label,
        "oneLineSummary": one_line_summary,
        "skillCoverage": {"total": len(specs), "mastered": mastered, "partial": partial, "missing": missing},
        "requirements": requirements,
        "priorityGaps": priority_gaps,
        "learningPath": learning_path,
        "llmStatus": llm_status,
    }

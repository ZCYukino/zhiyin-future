"""人岗匹配报告：Python 规则算分（稳定可复现）+ LLM 生成学习路径与总结（真实 AI，无规则降级）。

对齐前端 MatchReport 结构（score / verdict / verdictLabel / oneLineSummary /
skillCoverage / requirements / priorityGaps / learningPath / llmStatus）。
"""
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

# ===== 常量 =====

PRIORITY_ORDER = {"must": 0, "important": 1, "bonus": 2}
LEVEL_ORDER = {"junior": 0, "mid": 1, "senior": 2}
VERDICT_LABEL = {"strong": "强匹配", "fair": "较强匹配", "partial": "部分匹配", "weak": "弱匹配"}
VALID_STACKS = {"ai", "backend", "frontend", "data", "cloud", "security", "embedded", "product", "qa", "tool"}

# 技能优先级权重：必备技能决定匹配度主体，加分技能只做小幅加分
PRIORITY_WEIGHT = {"must": 1.0, "important": 0.7, "bonus": 0.4}

# 部分掌握计分系数：部分掌握（shared_substring 命中）按 60% 计分，而非对半，
# 避免「语义相近但措辞不同」的技能被过度拉低。
PARTIAL_FACTOR = 0.6

# 分数曲线指数：对「加权覆盖率」取 0.65 次方后再映射到 0~100。
# 作用：抬升低分段，消除大量个位/十几分的「过度严苛」极低分；
# 同时保留 0 与 100 两个端点，中高分段依旧拉开区分度。
SCORE_CURVE_EXP = 0.65

# ASCII 技能名按 token 精确匹配，避免「Java⊂JavaScript」「Go⊂MongoDB」「C⊂C++」等子串误判
_ASCII_TOKEN_RE = re.compile(r"[a-z0-9+#.]+")
# 中文字段（连续汉字），用于「只在中文之间做子串/2-gram 比较」
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
    # 'node.js' 因为 _ASCII_TOKEN_RE 含 `.` 会整体成一个 token，必须单独归一，
    # 否则 'Node.js' → {node.js} 而 'NodeJS' → {node}，同一个东西两个词面对不上。
    "node.js": "node",
    "vuejs": "vue",
    "vue.js": "vue",
    "postgres": "postgresql",
}
# 去掉点/连字符后仍相等的 token 视为同一个词（node.js ≡ nodejs、react.js ≡ reactjs）。
# 只对**长度 ≥3** 的 token 生效：「c.」这类单字符缩写不在其中。
_TOKEN_SEP_RE = re.compile(r"[.\-]")


def _fold_token(t: str) -> str:
    return _TOKEN_SEP_RE.sub("", t)

# 匹配报告 LLM 生成的单次超时（秒）：报告主体由规则秒级算分，LLM 只负责总结与学习路径；
# 超时/失败 → llmStatus="failed"，不降级。学习路径需输出多阶段 JSON，保留宽裕但仍有硬上限。
MATCH_LLM_TIMEOUT = 30.0


# ===== 技能匹配 =====
# 前端 resumeParser.ts 负责「从简历文本里抽出技能词」，本模块负责「把岗位技能点和
# 候选人证据比对」。**两者不是同一套实现，不要试图对齐**：前端是词典驱动的召回
# （别名归一 k8s≡Kubernetes、模糊表达短语），后端还有合取/举例语义、包含方向、
# 正文逐字直扫这些判定。前端产出 userSkills，后端把它当证据来源之一。

def _as_text(v: Any) -> str:
    """把请求体里的任意值收敛成字符串。

    `/matching/analyze` 的 body.user 是任意 dict（未登录也能调用），
    `{"education": 12345}` / `{"resumeText": 12345}` 这类输入以前会直接抛
    TypeError → 500。宁可当成空值，也不要让接口崩。
    """
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


# 泛用 ASCII 缩写：**不构成技能身份**。只共用「AI」「LLM」这种词不算同一项技能。
# 真实事故：岗位技能点「Scale AI平台配置」被简历里的「ai应用」以 token 'ai' 判成已掌握；
# 「LLM生成数据可信度评估」「LLM辅助数据合成」被简历里一句「LLM」判成已掌握——
# 简历只是提了 LLM，并没做过「LLM 生成数据的可信度评估」。
# 代价是「LLM基本原理」这类点也需要简历写出更多内容才算数（宁可少认，不可乱认）。
_GENERIC_ASCII = frozenset({
    "ai", "ml", "dl", "llm", "api", "sdk", "ui", "ux", "os", "db",
    "it", "id", "web", "app", "dev", "ops", "demo", "proj", "sys", "code",
})


def _strong_tokens(s: str) -> set[str]:
    """可用于判定「同一项技能」的 ASCII 词：先归一化，再剔除泛用缩写。"""
    return {t for t in _ascii_tokens(s) if t not in _GENERIC_ASCII}


def _ascii_overlap(a: str, b: str) -> bool:
    """两串里的 ASCII 词能否算「同一个词」。

    1) 归一化后的精确相等（主要判据）。
    2) 分隔符写法不同：node.js ≡ nodejs。
    3) 分开写 vs 连写：'vue 3' ≡ 'vue3'（简历写「Vue 3+TypeScript」、
       岗位技能点写「Vue3」是极常见的差异）。只在**至少一侧拆成了多个词**
       时才走这条，且要求 ≥3 字符，避免把无关缩写连起来。
    第 2、3 条只对长度 ≥3 的词生效，避免单字符缩写互认（c ⊂ c#、go ⊂ golang）；
    第 1 条按原样比对，短词（Go / C）完全相同才算同一个。
    """
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
    """只保留中文字段。中文的子串 / 2-gram 比较必须只在中文之间做：
    中英混排串若整串参与比较，ASCII 碎片会污染结果（'cvat等' 命中 'C'、
    'prd撰写' 命中 'Prompt设计'）。"""
    return "".join(_CJK_RUN_RE.findall(s))


def _longest_common_run(a: str, b: str) -> str:
    """最长公共**连续**子串（两侧都是短串，O(n·m) DP 足够）。"""
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


# 高频构词成分：**只**共用一个这样的词，不算「措辞相近」。
# 真实噪声（拿本仓库真实简历跑出来的「部分掌握」一列）：原理图设计~原型设计、
# 高性能计算~计算机视觉、配置管理工具~项目管理、系统性能优化~操作系统……
# 比对的必须是**整段公共子串**——「机器学习/深度学习」共的是「学习」，
# 「前端开发/后端开发」共的是「端开发」，都保留。
_GENERIC_RUNS = frozenset({
    "数据", "设计", "开发", "控制", "分析", "系统", "功能", "计算", "管理", "部署",
    "模拟", "计算机", "网络", "技术", "平台", "应用", "能力", "经验", "流程",
    "工具", "信息", "模型", "服务", "优化", "项目", "辅助", "流程设计",
})
# 刻意不收「测试」「结构」：功能测试/性能测试、数据结构/结构设计 这类确实同族，
# 判 partial 是合理的（只是不同侧重），不该一刀切成 missing。

# 参与最长公共子串 DP 的中文字段长度上限。真实技能名最长十几个字，
# 给到 120 足够宽松；超长输入只可能是构造出来的，直接判不相关。
_MAX_DP_CHARS = 120

# ASCII「看着像但不是一回事」的前缀对：Java ⊂ JavaScript 但两者无关。
# 只列真正会误导的；正常的「同族前缀」（Spring ⊂ Spring Boot）不受影响。
_ASCII_FALSE_PREFIX = frozenset({("java", "javascript")})


def _cjk_usable(s: str) -> bool:
    """该侧的中文字段是否够格当「技能证据」。

    要求中文字段 ≥3 字，**或**整串本身就是纯中文（没有 ASCII）。
    否则「Prompt设计」的中文字段只剩 '设计' 这个 2 字后缀，会被
    「标注质检流程设计」这类长岗位技能点整串包含 → 两个无关技能判成一项。
    纯中文的 2 字技能名（'微调' / '算法'）不受影响，仍是合法证据。

    这里用 _ascii_tokens 而**不是** _strong_tokens：问的是「这串里含不含 ASCII」，
    'ai应用' 里的 'ai' 虽然是泛用缩写，也足以说明它的中文字段只剩 2 字、不够格。
    换成 _strong_tokens 会让 'ai应用' 变成合法证据。
    """
    c = _cjk_only(s)
    return bool(c) and (len(c) >= 3 or not _ascii_tokens(s))


def contains_match(a: str, b: str) -> bool:
    na, nb = a.strip().lower(), b.strip().lower()
    if not na or not nb:
        return False
    # 完全同名 → 同一项技能。必须前置：泛用缩写（AI / LLM / Web）被 _GENERIC_ASCII
    # 过滤后 token 集为空，会连「自己等于自己」都判不出来。
    if na == nb:
        return True
    # ASCII 按规范化 token 精确匹配（Go 不再误配 MongoDB，Java 不再误配 JavaScript）。
    # 只要有 ASCII token 就走这条，**不能因为整串还含中文就改走中文子串分支**：
    # 「cvat等」含中文，旧实现整串子串比较 → userSkill「C」（C 语言）单字符命中，
    # 把「标注质检流程设计（Label Studio/CVAT等）」误判成已掌握。
    if _ascii_overlap(na, nb):
        return True
    # 中文无天然词边界，双向子串包含；只比中文字段，避免 ASCII 碎片混入。
    # 被包含的一方还须「够格」（见 _cjk_usable），否则 2 字后缀会到处命中。
    ca, cb = _cjk_only(na), _cjk_only(nb)
    if not ca or not cb:
        return False
    if ca == cb:
        # 中文字段相同还不够：`_cjk_only` 把 ASCII 丢掉了，
        # 「LoRA微调」与「微调」会退化成同一个中文串。岗位词带着 ASCII 限定语
        # 而简历词没有时（LoRA微调 ← 微调、Python编程 ← 编程），简历只证明了
        # 那个笼统的说法，不能算掌握；反方向（微调 ← LoRA微调）是简历更具体，成立。
        if _strong_tokens(na) and not _strong_tokens(nb):
            return False
        return True
    # 包含关系要分方向看，不能一律算「同一项」：
    #
    #   a 是岗位技能点、b 是简历里的词（classify_skill 的调用方向）
    #
    # ① 岗位词 ⊂ 简历词 → 简历说得比岗位**更具体**。具体蕴含一般，
    #    「算法」这个岗位技能点在简历写「算法工程师」时可以直接算掌握。
    # ② 简历词 ⊂ 岗位词 → 简历说得比岗位**更笼统**，只有「简历词是岗位词的前缀」
    #    才成立。中文复合词中心语在后：前缀补进来的是角色/抽象名词
    #    （机器学习 ⊂ 机器学习工程师、项目管理 ⊂ 项目管理经验），后缀/中间补进来的是
    #    限定性修饰语（算法 ⊂ 量子算法、工作流 ⊂ 标注工作流设计）——后者是缩小了范围，
    #    笼统的说法不能证明它。
    if len(ca) < len(cb) and ca in cb:
        return _cjk_usable(na)
    if len(cb) < len(ca) and cb in ca:
        return _cjk_usable(nb) and ca.startswith(cb)
    return False


def shared_substring(a: str, b: str) -> bool:
    na, nb = a.strip().lower(), b.strip().lower()
    if len(na) < 2 or len(nb) < 2:
        return False
    # ASCII：共享「长度 ≥3 的前缀」才判相关，避免 go⊂mongodb 之类误判
    for x in _strong_tokens(na):
        for y in _strong_tokens(nb):
            if x == y:
                continue
            short, long = sorted((x, y), key=len)
            if len(short) >= 3 and long.startswith(short):
                if (short, long) in _ASCII_FALSE_PREFIX:
                    continue
                return True
    # 中文：只比中文字段（否则「prd撰写」的 2-gram 'pr' 会命中「Prompt设计」），
    # 且公共片段必须**占两侧总长的 ≥20%**才算「措辞相近」。
    # 旧实现只要共享任意一个 2-gram 就算 partial，于是「数据」「设计」这类
    # 高频词让大量无关技能两两配对——真实事故里「部分掌握」一列全是噪声。
    ca, cb = _cjk_only(na), _cjk_only(nb)
    if not ca or not cb or not (_cjk_usable(na) and _cjk_usable(nb)):
        return False
    # 技能名不可能长过 _MAX_DP_CHARS；超过就判不相关，顺带把 O(n·m) 的 DP 挡在门外
    # （接口未鉴权，塞一个 10 万字的 userSkill 就能把单次请求拖到秒级）
    if len(ca) > _MAX_DP_CHARS or len(cb) > _MAX_DP_CHARS:
        return False
    run = _longest_common_run(ca, cb)
    # len(run)*5 >= la+lb  等价于  len(run) >= 0.2*(la+lb)
    # 机器学习/深度学习：共享「学习」(2) ≥ 0.2*8 ✓
    # 多模态数据一致性校验/向量数据库：共享「数据」(2) < 0.2*15 ✗
    if len(run) < 2 or len(run) * 5 < len(ca) + len(cb):
        return False
    # 再排掉「只共用一个高频构词成分」：原理图设计/原型设计 只共「设计」，不是一回事
    return run not in _GENERIC_RUNS


_PAREN_RE = re.compile(r"[（(]([^)）]*)[)）]")
_INNER_SEP_RE = re.compile(r"[、,，;；/]")
# 中文并列连接词：把「服务端部署与维护」这类复合技能点拆成组成项。
#
# ⚠️ 不能简单地按字拆：中文没有词边界，逐字切会把词从中间劈开。
# 实测事故：技能点「SRC参与经验」被切成 ['src参', '经验']——「参与」的「与」被当成连接词，
# 碎片『经验』随后在正文里命中「经验回放」，把这条技能点误判成掌握。
# 用先行断言跳过「连接词其实是词内字」的情况。
_CONNECTOR_RE = re.compile(
    r"(?<![参赠])与"        # 参与 / 赠与
    r"|(?<![以涉普波遍顾提及])及"  # 以及 / 涉及 / 普及 / 及时 / 提及
    r"|(?<![饱总柔温调谐平和])和"  # 饱和 / 总和 / 温和 / 调和 / 和谐 / 和平
)


def skill_parts(name: str) -> tuple[list[str], list[str]]:
    """把技能点拆成 (合取项, 举例项)。classify_skill 的唯一拆分入口。

    岗位技能点常把**真正可检的技能名塞进括号**，括号外只剩话题标签，例如
    「AI基础概念（机器学习、深度学习、大模型、RAG）」。旧实现只取
    normalize_skill_name()（= 删掉括号后的本体 'ai基础概念'），于是简历里
    写了 RAG / 大模型 / 机器学习也恒定判「未掌握」——括号把唯一能匹配的
    证据全删了。复合技能点同理：「服务端部署与维护」整体既不是「服务端部署」
    也不是「部署」的超串，简历只写了其中一项时双向子串都够不着。

    - **合取项**（「A与B」「A和B」「A及B」）：中文里这是「两个都要」。
      简历只写了其中一项时不能算掌握，只能算部分。
    - **举例项**（括号里用「、」「/」并列的枚举）：括号是对该概念的举例说明，
      覆盖过半才算完全掌握。

    括号里如果写的是「IAA与置信度建模」，那是合取，归合取项。
    """
    base = normalize_skill_name(name)
    conj: list[str] = []
    alts: list[str] = []

    def split_conj(text: str) -> list[str] | None:
        """全是 ≥2 字的组成部分才当合取拆；否则返回 None（整串当原子）。
        返回前统一归一化，与别的候选词保持同一形态。"""
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
    """把简历正文切成句段。每个句段产出两部分，都归一化：

    - **括号外的主体**（去掉括号注释）。岗位技能点「容器化技术（Docker）与编排工具
      （Kubernetes）的基础应用」拆出的合取项「编排工具的基础应用」在原文里被括号隔断，
      不去括号就永远扫不到。
    - **每个括号里的内容单独成段**。技能点也常把真正可检的名字写在括号里
      （「数据标注质量评估（IAA与置信度建模）」的合取项只存在于括号里），
      简历里那部分往往也写成括号或独立出现，不单独取出就丢证据。
      单独成段而不是拼回主体，避免「系统（Python）开发」拼出「系统Python开发」这种假相邻。

    只在句段内比较，绝不把全文拼成一条长串——拼起来会让上一行结尾的「…机器」
    和下一行开头的「学习…」连成「机器学习」。
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
    """把技能词编译成「在正文里出现」的正则。

    ASCII 片段加词边界（`C` 不该命中 `CET-4`、`Certificate`），中文片段按字面。
    """
    t = normalize_skill_name(term)
    if not t:
        return None
    # 逐段拼：ASCII 段加词边界，其余原样。ASCII 与中文交界处允许空白——
    # 岗位词写「QUBO建模」而简历写「QUBO 建模」是常见差异。
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
    # 忽略大小写：正文里写的是 AI / Docker / SRC，归一化后是小写
    return re.compile("".join(pieces), re.IGNORECASE)


def _fragment_usable(term: str) -> bool:
    """合取/举例片段够不够格当「正文直扫」的证据。

    片段是从技能点里拆出来的**词**，比整条技能点弱得多。整条技能点逐字出现是强证据
    （「容器化技术（Docker）与编排工具（Kubernetes）的基础应用」写全了就是会），
    但 2 个字的片段在散文里到处都是：
      「安全与合规（DevSecOps）」拆出的『安全』『合规』会命中
      「负责网络安全测试与数据合规审查」——那句话与 DevSecOps 毫无关系。
    所以要求片段至少 3 个中文字，或带一个**有辨识度**的 ASCII 词（iaa / cvat / pcb）。
    只有正文直扫受这条约束；词典路径不受影响——词典是人工维护的，收进去的词本身就是证据。
    """
    return len(_cjk_only(term)) >= 3 or bool(_strong_tokens(term))


def _term_in_text(term: str, segments: list[str]) -> bool:
    """岗位技能词是否**逐字**出现在简历正文里。

    这是绕开前端词典的关键：前端那份技能词典是人工维护的固定表，岗位技能点里
    只要出现没收录的词（家电控制器开发经验 / 量子算法 / 环境适应性测试…），
    简历原文写了也认不出来 —— 实测 30 个岗位里有 17 个，即使候选人把岗位要求的
    技能一条不差地写进简历，系统依然判未掌握。新采集的岗位只会更严重。
    这里改成**拿岗位自己的词去简历里找**，与词典覆盖面无关，岗位怎么变都成立。

    只认逐字出现（不做任何模糊），所以不会引入新的误判。
    """
    if not segments:
        return False
    rx = _term_span_re(term)
    if rx is None:
        return False
    return any(rx.search(seg) for seg in segments)


def classify_skill(req_name: str, user_skills: list[str], segments: list[str] | None = None) -> str:
    """三分类：mastered / partial / missing。

    判定顺序（每步都对应一种技能点的真实写法）：

    1. **有合取项**（「A与B」）时：
       a. 简历逐字写全了这个技能点名称 → 掌握。**只认逐字**，不能用 contains_match——
          本体必然以第一个合取项为前缀，用包含判定会让「简历只写『模型量化』」
          直接掌握「模型量化与剪枝」，绕过下面的合取检查。
       b. 合取项**全部**覆盖 → 掌握；覆盖一部分 → 部分掌握；一个都没覆盖 →
          看举例项与措辞相近度决定 partial/missing。
    2. 无合取项且本体命中 → 掌握。括号是对本体的举例说明，本体命中就不必再数例子。
    3. 举例项覆盖**过半** → 掌握（4 项里中 1 项不足以称掌握这个概念）；
       命中一部分 → 部分掌握。
    4. 都不命中但措辞相近 → 部分掌握；否则未掌握。
    """
    base = normalize_skill_name(req_name)
    conj, alts = skill_parts(req_name)
    segs = segments or []

    def hit(term: str, *, fragment: bool = False) -> bool:
        # 两条证据来源：① 前端词典抽出的技能表（含别名归一，能认 k8s≡Kubernetes）
        # ② 简历正文逐字扫描（不依赖词典，新岗位/新领域照样成立）
        # fragment=True 表示 term 是从技能点里拆出来的片段，走正文直扫时另有门槛
        if any(contains_match(term, u) for u in user_skills):
            return True
        if fragment and not _fragment_usable(term):
            return False
        return _term_in_text(term, segs)

    def fuzzy() -> bool:
        return any(shared_substring(t, u) for t in [base, *conj, *alts] for u in user_skills)

    if conj:
        # 简历把技能点名称整个写全了 → 掌握。
        # 必须**只认逐字**：contains_match 会因为「本体以第一个合取项为前缀」
        # 而放行（简历只写「模型量化」就命中「模型量化与剪枝」），绕过合取判定。
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
        # 覆盖过半即算掌握：⌈n/2⌉（1 项→1、2 项→1、3 项→2、4 项→2）
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
    """从年限描述里取**入职门槛**。

    区间写法取下界：「1-3年」表示 1 年即可投递，拿 3 当门槛会把 1-2 年经验的人
    全判成不达标（旧实现 re.search 取到的是区间里最后一个数字）。
    其余取唯一值：「5年以上」→5、「3年及以上」→3、「经验不限」→0。
    """
    t = s or ""
    m = _YEAR_RANGE_RE.search(t)
    if m:
        return int(m.group(1))
    m = _YEAR_RE.search(t)
    return int(m.group(1)) if m else 0


def _resolve_stack(name: str, stack: str | None) -> str:
    """归一技术栈：快照/LLM 给出的 stack 常把「产品/协作/需求」等软技能误标为兜底
    tool；用权威的 _infer_stack 重判一次（能判出更具体栈就采纳），保证资源推荐不跑偏。"""
    if stack in VALID_STACKS and stack != "tool":
        return stack
    inferred = _infer_stack(name)
    return inferred if inferred != "tool" else "tool"


# ===== LLM 生成学习路径 + 总结 =====


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
    # 单次尝试 + 短超时：报告正文由规则算分（秒级），LLM 仅生成总结与学习路径；
    # 失败返回 None（不再降级规则版），由 build_match_report 标记 llmStatus。
    data = generate_json(
        prompt, system="你是严谨的职业规划师。",
        timeout=MATCH_LLM_TIMEOUT, max_retries=2, credentials=credentials,
    )
    if not data:
        return None
    return data


# ===== 主入口 =====

def build_match_report(
    job_id: str,
    user: dict[str, Any],
    credentials: settings.Credentials | None = None,
    snapshot: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """生成匹配报告。

    snapshot 显式传入时就用它，否则读最新快照。把数据源做成参数而不是直接
    读全局 store，是为了让调用方（含测试）不必去 monkeypatch 全局状态。
    """
    # 只读路径：走缓存版，避免每次请求都把 450KB 快照读盘 + 解析一遍
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
    # 元素也必须是字符串：未鉴权接口上的 {"userSkills": [{"x":1}]} 以前会 500
    user_skills = [u for u in raw_skills if isinstance(u, str)]
    # 简历正文（用户上传时落库）：作为独立于词典的第二证据来源，见 _term_in_text
    segments = text_segments(_as_text(user.get("resumeText")))

    # 1. 展开技能矩阵
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

    # 2. 逐技能分类
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

    # 加权计分：必备技能权重最高，加分技能仅小幅加分；部分掌握按 PARTIAL_FACTOR 计分
    total_weight = sum(PRIORITY_WEIGHT[priority_from_level(s["level"])] for s in specs)
    achieved = (
        sum(PRIORITY_WEIGHT[s["priority"]] for s in mastered)
        + sum(PRIORITY_WEIGHT[s["priority"]] * PARTIAL_FACTOR for s in partial)
    )
    coverage = achieved / total_weight if total_weight else 0
    # 曲线映射：coverage^0.7 抬升低分段，消除过度严苛的极低分，同时保留满分与中高分段区分度
    score = round(100 * coverage ** SCORE_CURVE_EXP)
    verdict = "strong" if score >= 75 else "fair" if score >= 50 else "partial" if score >= 30 else "weak"
    verdict_label = VERDICT_LABEL[verdict]

    # 3. 硬门槛核查
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
    # 岗位没有给出学历/经验要求时**不合成门槛**：按薪资猜一个「3年以上」再拿它卡人，
    # 是凭空造出一条岗位从未提出的要求。缺就是缺，报告里不出现该行。
    user_exp = _as_text(user.get("resumeYears")) or _as_text(user.get("experience"))
    if req.get("experience"):
        required_years = parse_years(req["experience"])
        user_years = parse_years(user_exp)
        requirements.append(
            {"label": "经验", "user": user_exp or f"{user_years}年", "required": req["experience"], "passed": user_years >= required_years}
        )

    # 硬门槛轻度影响：任一硬门槛（学历/经验）不达标，结论最多下调一级（strong→fair、fair→partial），
    # 不再一刀切封顶为「部分匹配」，避免单点短板（如工作经验不足）过度拉低整体结论。
    if any(not r["passed"] for r in requirements):
        _order = ["weak", "partial", "fair", "strong"]
        _idx = _order.index(verdict)
        if _idx > 0:
            verdict = _order[_idx - 1]
            verdict_label = VERDICT_LABEL[verdict]

    # 4. 差距优先级统计
    # 缺口 = 完全缺失 + 半掌握（两者均属「未达标」，需补足）
    gap_skills = missing + partial
    priority_gaps = {
        "must": sum(1 for s in gap_skills if s["priority"] == "must"),
        "important": sum(1 for s in gap_skills if s["priority"] == "important"),
        "bonus": sum(1 for s in gap_skills if s["priority"] == "bonus"),
    }

    # 5. LLM 生成学习路径 + 总结（无规则降级；未配置/失败通过 llmStatus 明示）
    one_line_summary: str | None = None
    learning_path: list[dict[str, Any]] = []
    llm_status = "ok"
    # 凭据只接受显式传入（由路由按鉴权 token 解析）；默认视为未配置，
    # 绝不从 body.user 解析（其 id 可伪造，会形成跨账号 Key 冒用）。
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
                                    # LLM 未给 resource/milestone 就留空，不用模板补
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
                # LLM 返回了内容但没产出学习路径、而实际存在缺口 → 不得谎报「无缺口」
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

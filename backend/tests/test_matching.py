"""matching.py 单元测试：技能匹配 / 三分类 / 计分 / 匹配报告（llmStatus）。"""
from __future__ import annotations

import app.matching as matching
from app import config, settings
from app.matching import (
    _resolve_stack,
    _term_in_text,
    build_match_report,
    classify_skill,
    contains_match,
    edu_level_of,
    normalize_skill_name,
    parse_years,
    priority_from_level,
    shared_substring,
    skill_parts,
    text_segments,
)


def test_normalize_skill_name():
    assert normalize_skill_name("Python（高级）") == "python"
    assert normalize_skill_name("  Java\t") == "java"


def test_contains_match_ascii_exact():
    assert contains_match("Python", "python") is True
    assert contains_match("Java", "JavaScript") is False
    assert contains_match("Go", "MongoDB") is False


def test_contains_match_alias():
    assert contains_match("k8s", "Kubernetes") is True
    assert contains_match("Golang", "go") is True


def test_contains_match_chinese_substring():
    assert contains_match("机器学习", "机器学习工程师") is True
    assert contains_match("自然语言处理", "NLP") is False


def test_contains_match_empty():
    assert contains_match("", "x") is False


def test_shared_substring_chinese():
    assert shared_substring("机器学习", "深度学习") is True
    assert shared_substring("Go", "MongoDB") is False
    assert shared_substring("a", "ab") is False  # 长度 <2


def test_shared_substring_rejects_lookalike_language_prefix():
    """Java ⊄ JavaScript：ASCII 前缀规则不能把「看着像」当「同一族」。"""
    assert shared_substring("Java", "JavaScript") is False
    assert shared_substring("JavaScript", "Java") is False
    # 反向不得误伤：真正的同族前缀（Elastic ⊂ Elasticsearch）照旧判 partial
    assert shared_substring("Elastic", "Elasticsearch") is True
    # 「一边完全包含另一边」由 contains_match 负责，shared_substring 不重复判
    assert contains_match("Spring Boot", "Spring") is True


def test_shared_substring_rejects_single_generic_morpheme():
    """只共用一个高频构词成分，不算「措辞相近」。"""
    assert shared_substring("原理图设计", "原型设计") is False
    assert shared_substring("高性能计算", "计算机视觉") is False
    assert shared_substring("配置管理工具", "项目管理") is False
    assert shared_substring("系统性能优化", "操作系统") is False
    assert shared_substring("IoT项目开发", "ai辅助开发") is False
    assert shared_substring("自动控制", "版本控制") is False
    # 反向不得误伤：公共子串是**具体**词而非泛词时照旧判 partial
    assert shared_substring("机器学习", "增量学习") is True   # 共「学习」
    assert shared_substring("前端开发", "后端开发") is True   # 共「端开发」，非「开发」
    assert shared_substring("数据标注", "标注质检") is True   # 共「标注」


def test_skill_parts_expands_parenthetical():
    conj, alts = skill_parts("AI基础概念（机器学习、深度学习、大模型、RAG）")
    assert conj == []  # 没有「与/和/及」，不是合取
    assert alts == ["机器学习", "深度学习", "大模型", "rag"]


def test_skill_parts_splits_compound_by_connector():
    """复合技能点按连接词拆成组成项（合取）。"""
    assert skill_parts("服务端部署与维护") == (["服务端部署", "维护"], [])
    assert skill_parts("模型剪枝与知识蒸馏") == (["模型剪枝", "知识蒸馏"], [])
    assert skill_parts("监控与日志分析工具（如Prometheus、Grafana、ELK）")[0] == ["监控", "日志分析工具"]
    # 括号里写「A与B」也是合取
    assert skill_parts("数据标注质量评估（IAA与置信度建模）") == (["iaa", "置信度建模"], [])
    # 不含连接词、不含括号的技能点拆不出任何组成项
    assert skill_parts("数据标注流程认知") == ([], [])


def test_contains_match_separated_vs_joined_ascii():
    """分开写 vs 连写是同一个词：简历写「Vue 3+TypeScript」、岗位技能点写「Vue3」。"""
    assert contains_match("Vue3", "Vue 3") is True
    assert contains_match("Vue3", "vue3") is True
    assert contains_match("Node.js", "NodeJS") is True
    assert contains_match("Node.js", "node js") is True
    # 反向不得误伤：长度 <3 的缩写不参与连写合并
    assert contains_match("JavaScript", "Java") is False
    assert contains_match("CiCd", "C I D") is False


def test_term_in_text_matches_verbatim():
    """岗位技能词逐字出现在简历里就算数，与词典收没收这个词无关。"""
    segs = text_segments("技能清单：家电控制器开发经验、量子算法、环境适应性测试")
    assert _term_in_text("家电控制器开发经验", segs) is True
    assert _term_in_text("量子算法", segs) is True
    assert _term_in_text("环境适应性测试", segs) is True
    assert _term_in_text("多传感器融合", segs) is False


def test_term_in_text_respects_ascii_word_boundaries():
    """ASCII 片段按词边界：`C` 不该命中 `CET-4`／`Certificate`。"""
    segs = text_segments("通过 CET-4，熟悉 Certificate 体系，编程语言 C、C++")
    assert _term_in_text("C", segs) is True
    assert _term_in_text("C语言", segs) is False
    assert _term_in_text("ET", segs) is False


def test_term_in_text_does_not_cross_segments():
    """绝不跨句段拼接：上一行结尾的「机器」+ 下一行开头的「学习」不是「机器学习」。"""
    segs = text_segments("负责数据机器\n学习平台建设")
    assert _term_in_text("机器学习", segs) is False
    assert _term_in_text("数据机器", segs) is True


def test_parenthetical_content_is_scannable():
    """括号内容也要能扫到，每个句段额外产出「括号内容」作为独立句段。"""
    segs = text_segments("技能清单：数据标注质量评估（IAA与置信度建模）")
    assert _term_in_text("IAA", segs) is True
    assert _term_in_text("置信度建模", segs) is True
    # 括号里的内容单独成段，不会和主体拼成假相邻
    segs2 = text_segments("负责系统（Python）开发")
    assert _term_in_text("系统开发", segs2) is True
    assert _term_in_text("系统Python", segs2) is False


def test_connector_split_does_not_cut_inside_words():
    """连接词拆词不能把词从中间劈开（如「参与」的「与」不是连接词）。"""
    assert skill_parts("SRC参与经验") == ([], [])
    # 「以及 / 涉及」这类词里的及不是连接词，整串保持原子
    assert skill_parts("以及安全合规") == ([], [])
    assert skill_parts("涉及面较广的经验") == ([], [])
    # 同一串里，词内的「与」要跳过，真正的连接词照拆
    assert skill_parts("参与需求分析与评审") == (["参与需求分析", "评审"], [])
    # 真连接词照旧拆
    assert skill_parts("Linux操作系统及命令行操作") == (["linux操作系统", "命令行操作"], [])
    assert skill_parts("模型量化与剪枝") == (["模型量化", "剪枝"], [])
    assert skill_parts("服务端部署与维护") == (["服务端部署", "维护"], [])


def test_short_fragment_in_prose_is_not_evidence():
    """2 字片段在散文里到处都有，不构成「正文直扫」的证据。"""
    segs = text_segments("负责网络安全测试与数据合规审查，熟悉等保要求")
    assert classify_skill("安全与合规（DevSecOps）", [], segs) == "missing"
    # 够长的片段照旧算数
    assert classify_skill("服务端部署与维护", [], text_segments("负责服务端部署，保障线上稳定")) == "partial"
    # 带辨识度 ASCII 词的片段也算数
    assert classify_skill("标注质检流程设计（Label Studio/CVAT等）", [], text_segments("使用 CVAT 做标注质检流程设计")) == "mastered"


def test_build_match_report_survives_malformed_user_payload(monkeypatch):
    """未鉴权接口上的畸形 body 不能 500。"""
    snap = {"jobs": [{"id": "1", "name": "x", "skills": ["Java"]}],
            "jobSkillProgression": {}, "jobRequirements": {}}
    monkeypatch.setattr(matching, "_llm_plan", lambda *a, **k: None)
    for bad in [
        {"userSkills": [{"x": 1}]},
        {"userSkills": [5, None, "Java"]},
        {"resumeText": 12345},
        {"education": 12345, "major": [], "resumeYears": 123},
    ]:
        report = build_match_report("1", dict(bad), snapshot=snap)
        assert report is not None, bad
        assert 0 <= report["score"] <= 100, bad


def test_shared_substring_ignores_absurdly_long_input():
    """超长输入直接判不相关：O(n·m) 的 DP 不能被未鉴权请求拖垮。"""
    assert shared_substring("安" * 100000, "全" * 99999 + "安") is False
    assert shared_substring("机器学习", "深度学习") is True  # 正常长度不受影响


def test_verbatim_full_skill_point_is_mastered_without_dictionary():
    """简历逐字写全了技能点名称 → 掌握，即使合取项都没单独出现。"""
    for name in [
        "数据标注质量评估（IAA与置信度建模）",
        "容器化技术（Docker）与编排工具（Kubernetes）的基础应用",
        "模型量化与剪枝",
        "监控与日志分析工具（如Prometheus、Grafana、ELK）",
    ]:
        segs = text_segments(f"技能清单：{name}")
        assert classify_skill(name, [], segs) == "mastered", name


def test_verbatim_does_not_bypass_conjunction():
    """「逐字」必须真的逐字：简历只写「模型量化」不能因此掌握「模型量化与剪枝」。"""
    segs = text_segments("技能清单：模型量化、模型压缩")
    assert classify_skill("模型量化与剪枝", [], segs) == "partial"
    segs2 = text_segments("技能清单：数据标注质量评估")
    # 括号外的名称写全了，但合取项（IAA / 置信度建模）一个都没出现 —— 括号是注解，
    # 候选人用了岗位自己的名称，算掌握
    assert classify_skill("数据标注质量评估（IAA与置信度建模）", [], segs2) == "mastered"
    # 而合取项在括号外时（A与B），只写 A 不算掌握
    assert classify_skill("数据标注质量评估与置信度建模", [], segs2) == "partial"


def test_term_in_text_strips_parentheses():
    """岗位词跨括号时也要能扫到，两边都去括号才连得上。"""
    segs = text_segments("容器化技术（Docker）与编排工具（Kubernetes）的基础应用")
    assert _term_in_text("编排工具的基础应用", segs) is True


def test_classify_skill_uses_resume_text_as_second_evidence():
    """classify_skill 的第二证据来源：userSkills 认不出时，正文直扫仍可判掌握。"""
    segs = text_segments("熟悉量子算法与 QUBO 建模")
    assert classify_skill("量子算法", [], segs) == "mastered"
    assert classify_skill("QUBO建模", [], segs) == "mastered"
    assert classify_skill("量子算法", []) == "missing"  # 不给正文就只有词典一条路


def test_build_match_report_recognizes_unknown_vocabulary(monkeypatch):
    """整条岗位词表都不在词典里，只要简历写了就得给满分。"""
    snap = {
        "jobs": [{"id": "9", "name": "空调电控工程师", "categoryId": "embedded",
                  "skills": ["家电控制器开发经验", "空调控制器开发经验", "PMSM/BLDC控制调试经验"]}],
        "jobSkillProgression": {
            "9": {"junior": [{"name": "家电控制器开发经验", "stack": "embedded"},
                             {"name": "空调控制器开发经验", "stack": "embedded"},
                             {"name": "PMSM/BLDC控制调试经验", "stack": "embedded"}],
                  "mid": [], "senior": []},
        },
        "jobRequirements": {"9": {"education": "本科及以上", "experience": "1-3年"}},
    }
    monkeypatch.setattr(matching, "_llm_plan", lambda *a, **k: None)
    resume = "技能清单：家电控制器开发经验、空调控制器开发经验、PMSM/BLDC控制调试经验"
    user = {"userSkills": [], "resumeText": resume, "education": "本科", "resumeYears": "2年"}
    report = build_match_report("9", user, snapshot=snap)
    assert report["score"] == 100
    assert len(report["skillCoverage"]["mastered"]) == 3
    assert report["verdict"] == "strong"


def test_containment_direction_decides_mastery():
    """包含关系要分方向：简历比岗位笼统时，只有「简历词是岗位词的前缀」才算掌握。"""
    # 岗位词 ⊃ 简历词，且简历词是前缀 → 掌握（补进来的是角色/抽象名词）
    assert contains_match("机器学习工程师", "机器学习") is True
    assert contains_match("项目管理经验", "项目管理") is True
    assert contains_match("数据标注流程认知", "数据标注") is True
    assert contains_match("容器化部署", "容器化") is True
    # 岗位词 ⊃ 简历词，但简历词是后缀/中间 → 不掌握（补进来的是限定语）
    assert contains_match("量子算法", "算法") is False
    assert contains_match("数值优化算法", "算法") is False
    assert contains_match("标注工作流设计", "工作流") is False
    assert contains_match("多模态大模型端侧部署", "大模型") is False
    assert contains_match("回归测试", "测试") is False
    # 反方向：简历比岗位更具体 → 具体蕴含一般，掌握
    assert contains_match("算法", "算法工程师") is True
    assert contains_match("测试", "回归测试") is True


def test_classify_skill_conjunction_requires_all_parts():
    """「A与B」是合取：只掌握其中一项只能算部分掌握。"""
    assert classify_skill("模型量化与剪枝", ["模型量化"]) == "partial"
    assert classify_skill("模型量化与剪枝", ["模型量化", "剪枝"]) == "mastered"
    assert classify_skill("模型剪枝与知识蒸馏", ["知识蒸馏"]) == "partial"
    assert classify_skill("产品规划与需求分析", ["产品规划", "需求分析"]) == "mastered"
    assert classify_skill("产品规划与需求分析", ["产品规划"]) == "partial"
    assert classify_skill("服务端部署与维护", ["Java", "SQL"]) == "missing"
    # 合取判定不能被「本体以第一个合取项为前缀」绕过
    assert classify_skill("版本控制与元数据治理", ["版本控制"]) == "partial"


def test_parse_years_takes_lower_bound_of_range():
    """年限区间取下界：岗位写「1-3年」表示 1 年即可投递。"""
    assert parse_years("1-3年") == 1
    assert parse_years("3-5年") == 3
    assert parse_years("5年以上") == 5
    assert parse_years("3年及以上") == 3
    assert parse_years("经验不限") == 0
    assert parse_years("无经验") == 0


def test_build_match_report_does_not_invent_thresholds(monkeypatch):
    """岗位没给学历/经验要求时，不得按薪资编一个门槛出来卡人。"""
    snap = {
        "jobs": [{"id": "7", "name": "无要求岗", "categoryId": "backend",
                  "salaryMin": 40, "salaryMax": 60, "skills": ["Java"]}],
        "jobSkillProgression": {}, "jobRequirements": {},
    }
    monkeypatch.setattr(matching, "_llm_plan", lambda *a, **k: None)
    report = build_match_report("7", {"userSkills": ["Java"], "education": "大专", "resumeYears": "0年"}, snapshot=snap)
    assert report["requirements"] == []
    assert report["verdict"] == "strong"  # 没有被合成出来的门槛拉低


def test_skill_parts_splits_ascii_and_slash():
    assert skill_parts("标注质检流程设计（Label Studio/CVAT等）") == ([], ["label studio", "cvat等"])


def test_classify_skill_matches_parenthetical_content():
    """岗位技能点常把真正可检的技能名塞进括号，旧实现删括号后匹配不到。"""
    ai = "AI基础概念（机器学习、深度学习、大模型、RAG）"
    # 括号是 4 项举例，覆盖过半才算「掌握这个概念」
    assert classify_skill(ai, ["机器学习", "深度学习"]) == "mastered"
    assert classify_skill(ai, ["大模型", "RAG"]) == "mastered"
    assert classify_skill(ai, ["RAG"]) == "partial"  # 4 项里只中 1 项，不足以称掌握
    assert classify_skill("标注质检流程设计（Label Studio/CVAT等）", ["Label Studio"]) == "mastered"
    # 括号里写「A与B」是合取：只中一个只能算部分
    assert classify_skill("数据标注质量评估（IAA与置信度建模）", ["IAA", "置信度建模"]) == "mastered"
    assert classify_skill("数据标注质量评估（IAA与置信度建模）", ["IAA"]) == "partial"


def test_classify_skill_parenthetical_does_not_overclaim():
    """修括号不等于放水：括号内的词也不命中时，仍然必须判 missing。"""
    assert classify_skill("AI基础概念（机器学习、深度学习、大模型、RAG）", ["Java", "SQL"]) == "missing"
    assert classify_skill("标注质检流程设计（Label Studio/CVAT等）", ["Python"]) == "missing"


def test_ascii_token_not_swallowed_by_mixed_cjk_string():
    """'cvat等' 含中文时 ASCII 部分不得走中文子串分支。"""
    assert contains_match("cvat等", "C") is False
    assert contains_match("C", "cvat等") is False
    assert shared_substring("cvat等", "Java") is False
    assert shared_substring("prd撰写", "Prompt设计") is False  # 旧实现 'pr' ⊂ 'prompt'


def test_shared_substring_rejects_generic_bigram_only():
    """2-gram 重叠不能把「只共用一个常用词」当成「语义相近」。"""
    assert shared_substring("多模态数据一致性校验", "向量数据库") is False
    assert shared_substring("数据标注质量评估", "数据结构") is False
    assert shared_substring("数据分析能力", "向量数据库") is False
    assert shared_substring("标注质检流程设计", "原型设计") is False
    # 反向不得误伤：真正措辞相近的仍须判 partial
    assert shared_substring("机器学习", "深度学习") is True   # 共享「学习」，占比 2/8
    assert shared_substring("前端开发", "后端开发") is True   # 共享「端开发」
    assert shared_substring("数据标注", "标注质检") is True


def test_short_cjk_suffix_in_mixed_name_is_not_evidence():
    """混排串里的 2 字中文后缀不构成技能证据。"""
    assert contains_match("标注质检流程设计", "Prompt设计") is False
    assert shared_substring("标注质检流程设计", "Prompt设计") is False
    # 反向不得误伤：纯中文技能名的包含关系照旧
    assert contains_match("机器学习", "机器学习工程师") is True
    assert contains_match("算法", "算法工程师") is True
    # 但「岗位词带 ASCII 限定语、简历词没有」不算掌握：
    # _cjk_only 会把两者退化成同一个中文串，得靠 ASCII 把它们区分开
    assert contains_match("LoRA微调", "微调") is False
    assert contains_match("Python编程", "编程") is False
    # 反方向（简历更具体）成立
    assert contains_match("微调", "LoRA微调") is True


def test_generic_ascii_abbreviation_is_not_an_identity():
    """泛用 ASCII 缩写不构成技能身份，简历提过 AI/LLM 不等于做过对应技能点。"""
    assert contains_match("Scale AI平台配置", "ai应用") is False
    assert contains_match("Scale AI平台配置", "AI辅助开发") is False
    assert contains_match("LLM生成数据可信度评估", "llm") is False
    assert contains_match("LLM辅助数据合成", "llm") is False
    assert shared_substring("LLM辅助数据合成", "AI辅助开发") is False
    # 反向不得误伤：真正的技术名词照旧命中
    assert contains_match("Scale AI平台配置", "Scale AI") is True
    assert contains_match("MCP协议", "MCP") is True
    assert contains_match("BLDC", "bldc") is True
    assert contains_match("IoT项目开发", "IoT") is True
    # 但「完全同名」永远是同一项技能——泛用缩写被过滤后 token 集为空，
    # 不能连自己等于自己都判不出来
    assert contains_match("AI", "AI") is True
    assert classify_skill("LLM", ["LLM"]) == "mastered"
    assert classify_skill("Web", ["web"]) == "mastered"


def test_ascii_part_still_matches_across_mixed_strings():
    """反向：混排里真正相同的 ASCII 词仍须命中（修 bug 不能把这块一起关掉）。"""
    assert contains_match("cvat等", "cvat") is True
    assert contains_match("Label Studio/CVAT等", "Label Studio") is True
    assert contains_match("AI基础概念（机器学习、深度学习、大模型、RAG）", "RAG") is True


def test_classify_skill_is_reflexive_for_typical_skill_points():
    """不变量：岗位技能点对「自己」必须判已掌握。"""
    for name in [
        "C", "C++", "C/C++", "C语言", "Go", "Java", "JavaScript", "Node.js", "SQL",
        "CI/CD工具（如Jenkins）的使用与配置", "Docker/Kubernetes", "HTML/CSS", "Git/SVN",
        "AI基础概念（机器学习、深度学习、大模型、RAG）",
        "标注质检流程设计（Label Studio/CVAT等）",
        "数据标注质量评估（IAA与置信度建模）",
        "数据标注流程认知", "跨部门协作", "需求优先级管理", "用户故事",
        "MATLAB/Simulink", "AutoGen/CrewAI", "LangChain/LlamaIndex",
        "自动化质检流水线设计", "多传感器融合与3D感知",
        "服务端部署与维护", "持续集成/持续交付流程",
        # 复合技能点（连接词拆分不得让本体失配）
        "监控与日志分析工具（如Prometheus、Grafana、ELK）",
        "容器化技术（Docker）与编排工具（Kubernetes）的基础应用",
        "安全与合规（DevSecOps）", "版本控制与元数据治理",
        "Scale AI平台配置", "LLM基本原理", "Vue3", "TCP/IP", "BLDC", "FOC",
    ]:
        assert classify_skill(name, [name]) == "mastered", name


def test_classify_skill():
    assert classify_skill("Python", ["Python", "SQL"]) == "mastered"
    assert classify_skill("机器学习", ["深度学习"]) == "partial"
    assert classify_skill("Java", ["Python"]) == "missing"


def test_priority_from_level():
    assert priority_from_level("junior") == "must"
    assert priority_from_level("mid") == "important"
    assert priority_from_level("senior") == "bonus"


def test_edu_level_of():
    assert edu_level_of("博士") == 4
    assert edu_level_of("硕士及以上") == 3
    assert edu_level_of("本科") == 2
    assert edu_level_of("大专") == 1
    assert edu_level_of("不限") == 0


def test_parse_years():
    assert parse_years("5年以上") == 5
    assert parse_years("无经验") == 0


def test_resolve_stack():
    assert _resolve_stack("Python", "ai") == "ai"
    assert _resolve_stack("Python", "tool") == "ai"  # tool 重判
    assert _resolve_stack("产品规划", "product") == "product"


_SNAPSHOT = {
    "jobs": [
        {"id": "1", "name": "Java后端工程师", "categoryId": "backend",
         "salaryMin": 20, "salaryMax": 40, "skills": ["Java", "Spring Boot", "MySQL"]},
    ],
    "jobSkillProgression": {
        "1": {
            "junior": [{"name": "Java", "stack": "backend"},
                        {"name": "Spring Boot", "stack": "backend"},
                        {"name": "MySQL", "stack": "backend"}],
            "mid": [], "senior": [],
        }
    },
    "jobRequirements": {"1": {"education": "本科及以上", "experience": "1-3年"}},
}


def test_build_match_report_not_found(monkeypatch):
    assert build_match_report("999", {"userSkills": []}, snapshot=_SNAPSHOT) is None


def test_build_match_report_full_mastery(monkeypatch):
    monkeypatch.setattr(matching, "_llm_plan", lambda *a, **k: None)
    user = {"userSkills": ["Java", "Spring Boot", "MySQL"], "education": "本科", "resumeYears": "3年"}
    report = build_match_report("1", user, snapshot=_SNAPSHOT)
    assert report is not None
    assert report["score"] == 100
    assert report["verdict"] == "strong"
    assert report["skillCoverage"]["total"] == 3
    assert len(report["skillCoverage"]["mastered"]) == 3
    assert report["learningPath"] == []  # 无缺口
    assert report["llmStatus"] == "no_api_key"
    assert report["oneLineSummary"] is None


def test_build_match_report_zero_mastery_and_gate(monkeypatch):
    monkeypatch.setattr(matching, "_llm_plan", lambda *a, **k: None)
    user = {"userSkills": ["Python"], "education": "大专", "resumeYears": "0年"}
    report = build_match_report("1", user, snapshot=_SNAPSHOT)
    assert report is not None
    assert report["score"] == 0
    assert report["verdict"] == "weak"
    assert len(report["skillCoverage"]["missing"]) == 3
    assert any(not r["passed"] for r in report["requirements"])
    assert report["llmStatus"] == "no_api_key"
    assert report["oneLineSummary"] is None


def test_build_match_report_partial(monkeypatch):
    monkeypatch.setattr(matching, "_llm_plan", lambda *a, **k: None)
    user = {"userSkills": ["Java"], "education": "本科", "resumeYears": "3年"}
    report = build_match_report("1", user, snapshot=_SNAPSHOT)
    assert report["score"] == 49  # 1/3 覆盖率，经 0.65 次方曲线映射
    assert report["verdict"] == "partial"
    assert report["llmStatus"] == "no_api_key"
    assert report["oneLineSummary"] is None


def test_build_match_report_hard_gate_demotes_one_level(monkeypatch):
    monkeypatch.setattr(matching, "_llm_plan", lambda *a, **k: None)
    # 技能全掌握但门槛不达标：分数不受影响，结论只下调一级
    user = {"userSkills": ["Java", "Spring Boot", "MySQL"], "education": "大专", "resumeYears": "0年"}
    report = build_match_report("1", user, snapshot=_SNAPSHOT)
    assert report["score"] == 100
    assert report["verdict"] == "fair"
    assert report["llmStatus"] == "no_api_key"
    assert report["oneLineSummary"] is None


def test_build_match_report_llm_ok(monkeypatch):
    cred = settings.Credentials("sk-test", config.LLM_BASE_URL, config.LLM_MODEL, True)
    monkeypatch.setattr(matching, "_llm_plan", lambda *a, **k: {
        "oneLineSummary": "总体匹配良好。",
        "learningPath": [
            {
                "stage": "阶段一", "period": "1-3 个月", "focus": "补 Python",
                "steps": [{"skill": "Python", "stack": "ai"}],
            }
        ],
    })
    user = {"userSkills": ["Java"], "education": "本科", "resumeYears": "3年"}
    report = build_match_report("1", user, credentials=cred, snapshot=_SNAPSHOT)
    assert report["llmStatus"] == "ok"
    assert report["oneLineSummary"] == "总体匹配良好。"
    assert report["learningPath"][0]["steps"][0]["skill"] == "Python"
    # 未给 resource/milestone 就留空
    assert report["learningPath"][0]["steps"][0]["resource"] == ""
    assert report["learningPath"][0]["steps"][0]["milestone"] == ""


def test_build_match_report_llm_failed(monkeypatch):
    cred = settings.Credentials("sk-test", config.LLM_BASE_URL, config.LLM_MODEL, True)
    monkeypatch.setattr(matching, "_llm_plan", lambda *a, **k: None)
    user = {"userSkills": ["Java"], "education": "本科", "resumeYears": "3年"}
    report = build_match_report("1", user, credentials=cred, snapshot=_SNAPSHOT)
    assert report["llmStatus"] == "failed"
    assert report["score"] == 49  # 规则算分不受影响
    assert report["learningPath"] == []


def test_build_match_report_pathless_payload_with_gaps(monkeypatch):
    cred = settings.Credentials("sk-test", config.LLM_BASE_URL, config.LLM_MODEL, True)
    monkeypatch.setattr(matching, "_llm_plan", lambda *a, **k: {"oneLineSummary": "有总结但没路径"})
    user = {"userSkills": ["Java"], "education": "本科", "resumeYears": "3年"}
    report = build_match_report("1", user, credentials=cred, snapshot=_SNAPSHOT)
    assert report["llmStatus"] == "failed"
    assert report["oneLineSummary"] == "有总结但没路径"

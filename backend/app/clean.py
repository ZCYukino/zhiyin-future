"""多源异构数据清洗与交叉验证：去重、去噪（模板句）、时滞处理。"""
from __future__ import annotations

import re
from collections import Counter
from difflib import SequenceMatcher

from .crawler.base import RawJob

# JD 常见噪声模板（福利 / 公司介绍 / 联系方式 / 套话），去噪时剔除
NOISE_PATTERNS = [
    r"五险一金|六险一金|带薪年假|弹性工作|定期体检|节日福利|年终奖|股票期权|餐补|房补|交通补贴",
    r"公司简介|公司介绍|关于我们|成立于?\d{4}年|注册资本|员工人数|融资|上市|独角兽|福利待遇",
    r"[\w.+-]+@[\w-]+\.[\w.]+|1[3-9]\d{9}|联系人|微信号|简历投递|欢迎投递|投递方式|HR",
    r"领导交办|完成上级|交代的|临时.*任务|其他.*事项",
    r"抗压能力|团队合作精神|责任心强|学习能力强|沟通能力|执行力强|积极主动",
]

# 区 → 所属市
DISTRICT_TO_CITY = {
    "东城区": "北京", "西城区": "北京", "朝阳区": "北京", "海淀区": "北京", "丰台区": "北京",
    "石景山区": "北京", "通州区": "北京", "大兴区": "北京", "昌平区": "北京", "顺义区": "北京",
    "黄浦区": "上海", "徐汇区": "上海", "静安区": "上海", "长宁区": "上海", "杨浦区": "上海",
    "虹口区": "上海", "浦东新区": "上海", "闵行区": "上海", "嘉定区": "上海", "普陀区": "上海",
    "越秀区": "广州", "海珠区": "广州", "荔湾区": "广州", "天河区": "广州", "白云区": "广州",
    "黄埔区": "广州", "番禺区": "广州", "南沙区": "广州", "花都区": "广州",
    "罗湖区": "深圳", "福田区": "深圳", "南山区": "深圳", "宝安区": "深圳", "龙岗区": "深圳",
    "龙华区": "深圳", "坪山区": "深圳", "光明区": "深圳", "盐田区": "深圳",
    "上城区": "杭州", "拱墅区": "杭州", "西湖区": "杭州", "滨江区": "杭州", "余杭区": "杭州",
    "萧山区": "杭州", "临平区": "杭州", "钱塘区": "杭州",
    "锦江区": "成都", "青羊区": "成都", "金牛区": "成都", "武侯区": "成都", "成华区": "成都",
    "高新区": "成都",
    "玄武区": "南京", "鼓楼区": "南京", "秦淮区": "南京", "建邺区": "南京", "雨花台区": "南京", "江宁区": "南京",
    "江岸区": "武汉", "武昌区": "武汉", "洪山区": "武汉", "江汉区": "武汉", "光谷区": "武汉",
    "雁塔区": "西安", "碑林区": "西安", "未央区": "西安", "高新区管委会": "西安",
    "姑苏区": "苏州", "吴中区": "苏州", "相城区": "苏州", "虎丘区": "苏州", "工业园区": "苏州",
    "和平区": "天津", "河西区": "天津", "南开区": "天津", "滨海新区": "天津",
    "渝中区": "重庆", "江北区": "重庆", "南岸区": "重庆", "九龙坡区": "重庆",
    "思明区": "厦门", "湖里区": "厦门", "集美区": "厦门",
    "芙蓉区": "长沙", "岳麓区": "长沙", "天心区": "长沙", "开福区": "长沙",
}


def denoise(text: str) -> str:
    """按行剔除模板噪声。"""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    out: list[str] = []
    for ln in lines:
        if any(re.search(p, ln) for p in NOISE_PATTERNS):
            continue
        out.append(ln)
    return "\n".join(out)


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def deduplicate(jobs: list[RawJob], threshold: float = 0.85) -> list[RawJob]:
    """基于描述文本相似度去重。"""
    unique: list[RawJob] = []
    for j in jobs:
        dup = False
        for u in unique:
            if _similarity(j.description, u.description) >= threshold:
                dup = True
                break
        if not dup:
            unique.append(j)
    return unique


def normalize_city(city: str) -> str:
    """把城市字段归一为「市」级：省→空、区→所属市、市→去「市」、直辖市保留。"""
    c = (city or "").strip()
    if not c:
        return ""
    # 省 / 自治区 → 高于市级，丢弃
    if c.endswith(("省", "自治区")):
        return ""
    if c in ("北京", "上海", "天津", "重庆"):
        return c
    if c.endswith("市"):
        return c[:-1]
    # 「区」结尾归一到所属市，无映射则丢弃
    if c.endswith("区"):
        return DISTRICT_TO_CITY.get(c, "")
    return c


def cross_validate_skills(skill_lists: list[list[str]], min_support: int = 2) -> list[str]:
    """多源交叉验证：仅保留在足够多来源中出现的技能，过滤单源噪声。"""
    counter: Counter[str] = Counter()
    for skills in skill_lists:
        for s in set(skills):
            counter[s] += 1
    return [s for s, c in counter.items() if c >= min_support]


def clean_pipeline(jobs: list[RawJob]) -> list[RawJob]:
    """清洗流水线：去噪 -> 城市归一 -> 去重。"""
    cleaned: list[RawJob] = []
    for j in jobs:
        j.description = denoise(j.description)
        j.city = normalize_city(j.city)
        if len(j.description) < 20:  # 描述过短视为无效样本
            continue
        cleaned.append(j)
    return deduplicate(cleaned)

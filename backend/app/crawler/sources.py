"""招聘站点爬虫实现。

数据源一：中国公共招聘网（job.mohrss.gov.cn，人力资源和社会保障部公共服务站点）。
选择理由：
- 政府公共服务平台，公开数据、无登录/验证码，合规风险低；
- 列表页内嵌结构化岗位 JSON（findjoblist 隐藏域），解析稳定；
- 提供按关键词检索，可聚焦“新一代信息技术”岗位（贴合赛题「岗位与能力图谱」）。

数据源二：国聘（www.iguopin.com，国投人力旗下央企国企招聘平台）。
选择理由：
- 央企国企实名岗位，JD 正文完整规范（职责+任职要求），与 mohrss 互补；
- 站点 robots.txt 完全开放；底层 JSON API 免登录、无验证码（gp-api.iguopin.com）；
- 一次接口响应即含 岗位名/公司/城市/学历/经验/薪资/完整 JD 正文，无需抓详情页。

合规约定：
- 低频率请求（base.fetch/post_json 内置 0.8~2s 随机延迟 + 重试）；
- 仅采集岗位信息（名称/城市/薪资/JD 正文），不采集任何个人联系方式。
"""
from __future__ import annotations

import html
import json
import re

from .base import RawJob, fetch, post_json


def _to_int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


class MohrssCrawler:
    """中国公共招聘网爬虫：按关键词检索并解析内嵌 JSON 岗位列表。"""

    name = "mohrss"
    BASE = "http://job.mohrss.gov.cn/cjobs/jobinfolist/listJobinfolist"
    DETAIL_BASE = "http://job.mohrss.gov.cn/cjobs/htmls/cb21gwPages"

    # 新一代信息技术方向关键词（贴合赛题「岗位与能力图谱」主题）
    KEYWORDS = [
        "算法工程师",
        "人工智能",
        "软件工程师",
        "数据分析",
        "大数据",
        "嵌入式",
        "网络安全",
        "前端",
        "Java",
        "Python",
        "测试开发",
        "云计算",
        "后端开发",
        "前端开发",
        "数据挖掘",
        "软件测试",
    ]

    # 二次过滤：站点关键词匹配较宽，标题须命中 IT 信号，正文作为辅助
    _TECH_TITLE = (
        "工程师", "开发", "算法", "软件", "数据", "人工智能", "嵌入式", "网络安全",
        "前端", "后端", "测试", "运维", "架构", "研发", "程序", "芯片", "机器人",
        "java", "python", "ai",
    )
    _TECH_TOKENS = (
        "算法", "软件", "开发", "工程师", "数据", "人工智能", "ai", "java", "python",
        "前端", "后端", "测试", "运维", "嵌入式", "安全", "云", "产品", "机器人", "硬件",
        "芯片", "程序", "it", "信息", "网络",
    )

    def crawl(self, keyword: str, limit: int = 5, pages: int = 2) -> list[RawJob]:
        jobs: list[RawJob] = []
        seen: set[str] = set()
        for page_no in range(1, pages + 1):
            try:
                resp = fetch(
                    self.BASE,
                    params={"textfield": keyword, "pageNo": page_no},
                    headers={"Referer": self.BASE},
                    encoding="utf-8",
                )
            except Exception:  # noqa: BLE001 单页失败不阻断整体
                continue
            for raw in self._parse(resp.text):
                if not raw.url or raw.url in seen:
                    continue
                if not self._is_tech(raw):
                    continue
                seen.add(raw.url)
                # 列表页摘要过短时，回源详情页抓取完整 JD 正文（gwms 字段）
                if len(raw.description) < 100:
                    detail = self._fetch_detail(raw.url)
                    if detail:
                        raw.description = detail
                jobs.append(raw)
                if len(jobs) >= limit:
                    return jobs
        return jobs

    def _fetch_detail(self, url: str) -> str:
        """抓取详情页完整岗位描述（<span id="gwms"> 正文），失败返回空串。"""
        try:
            resp = fetch(url, headers={"Referer": self.BASE}, encoding="utf-8")
            m = re.search(r'<span id="gwms">(.*?)</span>', resp.text, re.S)
            if not m:
                return ""
            text = re.sub(r"<[^>]+>", "", m.group(1))
            return html.unescape(text).strip()
        except Exception:  # noqa: BLE001 详情页失败不影响列表数据
            return ""

    def _parse(self, page_html: str) -> list[RawJob]:
        """从列表页隐藏域 findjoblist 解析岗位 JSON 数组。"""
        m = re.search(r'findjoblist[^>]*value="([^"]*)"', page_html)
        if not m:
            return []
        try:
            rows = json.loads(html.unescape(m.group(1)))
        except json.JSONDecodeError:
            return []
        if not isinstance(rows, list):
            return []

        out: list[RawJob] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = str(row.get("aca112") or "").strip()
            if not title:
                continue
            description = str(row.get("acb22a") or "").strip()
            city = str(row.get("aab302") or "").strip()
            company = str(row.get("aab004") or "").strip()
            jid = _to_int(row.get("acb200"))
            # 薪资：acb241/acb242 单位为“元/月”，转换为 K/月 对齐前端口径
            sal_min_raw = _to_int(row.get("acb241"))
            sal_max_raw = _to_int(row.get("acb242"))
            sal_min = round(sal_min_raw / 1000, 1) if sal_min_raw > 0 else None
            sal_max = round(sal_max_raw / 1000, 1) if sal_max_raw > 0 else None
            out.append(
                RawJob(
                    title=title,
                    description=description,
                    city=city,
                    salary=self._salary_text(sal_min_raw, sal_max_raw),
                    salary_min=sal_min,
                    salary_max=sal_max,
                    source=self.name,
                    url=f"{self.DETAIL_BASE}/{jid}.html" if jid else self.BASE,
                    extra={"company": company, "jobId": str(jid) if jid else ""},
                )
            )
        return out

    @staticmethod
    def _salary_text(lo: int, hi: int) -> str:
        if lo <= 0 and hi <= 0:
            return "面议"
        if lo > 0 and hi > 0:
            return f"{lo}-{hi}元/月"
        return f"{lo or hi}元/月"

    def _is_tech(self, raw: RawJob) -> bool:
        title = raw.title.lower()
        text = f"{raw.title} {raw.description}".lower()
        return any(tok in title for tok in self._TECH_TITLE) and any(
            tok in text for tok in self._TECH_TOKENS
        )


class IguopinCrawler:
    """国聘爬虫：POST 关键词检索 JSON API，解析岗位列表。

    与 MohrssCrawler 互补：mohrss 有薪资数字但 JD 简短，国聘薪资多为「面议」
    但 JD 正文完整规范。接口免登录，单次响应即含全部字段，无需二跳详情页。
    """

    name = "iguopin"
    BASE = "https://gp-api.iguopin.com/api/jobs/v1/recom-job"
    DETAIL_BASE = "https://www.iguopin.com/job/detail"

    # 聚焦国聘的优势供给（央企国企 AI/算法岗 JD 质量高），量小而稳
    KEYWORDS = [
        "大模型",
        "算法工程师",
        "人工智能",
        "软件工程师",
        "数据工程师",
        "网络安全",
    ]

    # 轻量过滤：关键词检索本已精准，仅剔除明显非技术的岗位（如行政/财务）
    _TECH_TOKENS = (
        "算法", "软件", "开发", "工程师", "数据", "人工智能", "ai", "java", "python",
        "前端", "后端", "测试", "运维", "嵌入式", "安全", "云", "架构", "研发", "程序",
        "芯片", "机器人", "模型", "智能",
    )
    # 关键词虽命中但职业本质非技术研发的排除项（如「人工智能教师」）
    _EXCLUDE_TITLE = ("教师", "讲师", "助教", "培训师", "行政", "财务", "人事", "销售", "客服", "猎头", "招聘")

    def crawl(self, keyword: str, limit: int = 5, pages: int = 1) -> list[RawJob]:
        jobs: list[RawJob] = []
        seen: set[str] = set()
        for page_no in range(1, pages + 1):
            try:
                data = post_json(
                    self.BASE,
                    payload={"search": {"page": page_no, "page_size": 20, "keyword": keyword}},
                    headers={"Origin": "https://www.iguopin.com", "Referer": "https://www.iguopin.com/"},
                )
            except Exception:  # noqa: BLE001 单页失败不阻断整体
                continue
            if not isinstance(data, dict) or data.get("code") != 200:
                continue
            for row in ((data.get("data") or {}).get("list") or []):
                if not isinstance(row, dict):
                    continue
                jid = str(row.get("job_id") or "")
                if not jid or jid in seen:
                    continue
                raw = self._to_raw(row, jid)
                if not raw.title or not raw.description:
                    continue
                if not self._is_tech(raw):
                    continue
                seen.add(jid)
                jobs.append(raw)
                if len(jobs) >= limit:
                    return jobs
        return jobs

    def _to_raw(self, row: dict, jid: str) -> RawJob:
        title = str(row.get("job_name") or "").strip()
        description = str(row.get("contents") or "").strip()
        # 城市取区县级行政区（「北京-海淀区」→「海淀区」，交由 clean.normalize_city 归一市级）
        districts = row.get("district_list") or []
        area = str((districts[0] or {}).get("area_cn") or "") if districts else ""
        city = area.split("-")[-1].rstrip("等") if area else ""
        # 薪资：国聘央企岗多为面议（is_negotiable/min_wage=0），仅少数岗位写明
        sal_min_raw = _to_int(row.get("min_wage"))
        sal_max_raw = _to_int(row.get("max_wage"))
        unit = str(row.get("wage_unit_cn") or "")
        if sal_min_raw > 0 or sal_max_raw > 0:
            # 按单位换算为 K/月（对齐 mohrss 口径）：元→/1000；万→×10；千→原值
            if "万" in unit:
                factor = 10.0
            elif "千" in unit:
                factor = 1.0
            else:
                factor = 0.001
            sal_min = round(sal_min_raw * factor, 1) if sal_min_raw > 0 else None
            sal_max = round(sal_max_raw * factor, 1) if sal_max_raw > 0 else None
            salary = self._salary_text(sal_min_raw, sal_max_raw, unit)
        else:
            sal_min = sal_max = None
            salary = "面议"
        return RawJob(
            title=title,
            description=description,
            city=city,
            salary=salary,
            salary_min=sal_min,
            salary_max=sal_max,
            source=self.name,
            url=f"{self.DETAIL_BASE}?id={jid}",
            published_at=str(row.get("start_time") or "") or None,
            extra={
                "company": str(row.get("company_name") or ""),
                "jobId": jid,
                "education": str(row.get("education_cn") or ""),
                "experience": str(row.get("experience_cn") or ""),
                "recruitmentType": str(row.get("recruitment_type_cn") or ""),
            },
        )

    @staticmethod
    def _salary_text(lo: int, hi: int, unit: str) -> str:
        u = unit or "元/月"
        if lo > 0 and hi > 0:
            return f"{lo}-{hi}{u}"
        return f"{lo or hi}{u}"

    def _is_tech(self, raw: RawJob) -> bool:
        title = raw.title.lower()
        if any(tok in title for tok in self._EXCLUDE_TITLE):
            return False
        text = f"{raw.title} {raw.description}".lower()
        return any(tok in text for tok in self._TECH_TOKENS)


# 站点注册表（ingest 按此遍历）
CRAWLERS = {
    "mohrss": MohrssCrawler,
    "iguopin": IguopinCrawler,
}

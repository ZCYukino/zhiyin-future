"""招聘站点爬虫实现。"""
from __future__ import annotations

import html
import json
import re
import math

from .base import RawJob, fetch, post_json


def _to_int(v) -> int:
    try:
        return int(v or 0)
    except (TypeError, ValueError):
        return 0


def _to_number(value) -> float:
    try:
        number = float(value or 0)
        return number if math.isfinite(number) else 0
    except (ValueError, TypeError):
        return 0


class MohrssCrawler:
    """中国公共招聘网爬虫：按关键词检索并解析内嵌 JSON 岗位列表。"""

    def __init__(self) -> None:
        self.errors: list[str] = []

    name = "mohrss"
    BASE = "http://job.mohrss.gov.cn/cjobs/jobinfolist/listJobinfolist"
    DETAIL_BASE = "http://job.mohrss.gov.cn/cjobs/htmls/cb21gwPages"

    # 新一代信息技术方向关键词
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

    # 二次过滤：标题须命中 IT 信号，正文辅助
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
        seen_pages: set[tuple[str, ...]] = set()
        self.errors: list[str] = []
        for page_no in range(1, pages + 1):
            try:
                resp = fetch(
                    self.BASE,
                    params={"textfield": keyword, "pageNo": page_no},
                    headers={"Referer": self.BASE},
                    encoding="utf-8",
                )
            except Exception as error:  # 已完成的页面仍可用，故障显式返回统计
                self.errors.append(f"page {page_no}: {type(error).__name__}")
                break
            try:
                rows = self._parse(resp.text)
            except ValueError:
                self.errors.append(f"page {page_no}: 岗位列表结构不可识别")
                break
            if not rows:
                break
            page_ids = tuple(raw.url for raw in rows)
            if page_ids in seen_pages:
                break
            seen_pages.add(page_ids)
            for raw in rows:
                if not raw.url or raw.url in seen:
                    continue
                if not self._is_tech(raw):
                    continue
                seen.add(raw.url)
                # 摘要过短时回源详情页抓取完整 JD
                if len(raw.description) < 100:
                    detail = self._fetch_detail(raw.url)
                    if detail:
                        raw.description = detail
                jobs.append(raw)
                if len(jobs) >= limit:
                    return jobs
        return jobs

    def _fetch_detail(self, url: str) -> str:
        """抓取详情页描述；失败保留列表摘要，并把详情故障记入来源统计。"""
        try:
            resp = fetch(url, headers={"Referer": self.BASE}, encoding="utf-8")
            m = re.search(r'<span id="gwms">(.*?)</span>', resp.text, re.S)
            if not m:
                self.errors.append("detail: 岗位描述结构不可识别")
                return ""
            text = re.sub(r"<[^>]+>", "", m.group(1))
            return html.unescape(text).strip()
        except Exception as error:  # noqa: BLE001 详情页失败不影响列表数据
            self.errors.append(f"detail: {type(error).__name__}")
            return ""

    def _parse(self, page_html: str) -> list[RawJob]:
        """从列表页隐藏域 findjoblist 解析岗位 JSON 数组。"""
        m = re.search(r'findjoblist[^>]*value="([^"]*)"', page_html)
        if not m:
            raise ValueError("缺少 findjoblist 列表字段")
        try:
            rows = json.loads(html.unescape(m.group(1)))
        except json.JSONDecodeError as error:
            raise ValueError("岗位列表不是合法 JSON") from error
        if not isinstance(rows, list):
            raise ValueError("岗位列表不是数组")

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
            if not jid:
                continue
            # 元/月 转 K/月
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
    """国聘爬虫：POST 关键词检索 JSON API，解析岗位列表。JD 正文完整规范，与 mohrss 互补。"""

    name = "iguopin"
    BASE = "https://gp-api.iguopin.com/api/jobs/v1/recom-job"
    DETAIL_BASE = "https://www.iguopin.com/job/detail"

    # 央企国企 AI/算法岗 JD 质量高
    KEYWORDS = [
        "大模型",
        "算法工程师",
        "人工智能",
        "软件工程师",
        "数据工程师",
        "网络安全",
    ]

    # 轻量过滤：剔除明显非技术的岗位
    _TECH_TOKENS = (
        "算法", "软件", "开发", "工程师", "数据", "人工智能", "ai", "java", "python",
        "前端", "后端", "测试", "运维", "嵌入式", "安全", "云", "架构", "研发", "程序",
        "芯片", "机器人", "模型", "智能",
    )
    # 命中关键词但本质非技术研发的排除项
    _EXCLUDE_TITLE = ("教师", "讲师", "助教", "培训师", "行政", "财务", "人事", "销售", "客服", "猎头", "招聘")

    def crawl(self, keyword: str, limit: int = 5, pages: int = 1) -> list[RawJob]:
        jobs: list[RawJob] = []
        seen: set[str] = set()
        seen_pages: set[tuple[str, ...]] = set()
        self.errors: list[str] = []
        for page_no in range(1, pages + 1):
            try:
                data = post_json(
                    self.BASE,
                    payload={"search": {"page": page_no, "page_size": 20, "keyword": keyword}},
                    headers={"Origin": "https://www.iguopin.com", "Referer": "https://www.iguopin.com/"},
                )
            except Exception as error:
                self.errors.append(f"page {page_no}: {type(error).__name__}")
                break
            if not isinstance(data, dict) or data.get("code") != 200:
                self.errors.append(f"page {page_no}: API返回错误状态")
                break
            body = data.get("data")
            if not isinstance(body, dict) or not isinstance(body.get("list"), list):
                self.errors.append(f"page {page_no}: 岗位列表结构不可识别")
                break
            rows = body["list"]
            if not rows:
                break
            page_ids = tuple(str(row.get("job_id") or "") for row in rows if isinstance(row, dict))
            if page_ids in seen_pages:
                break
            seen_pages.add(page_ids)
            for row in rows:
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
        # 保留完整层级，供清洗模块选择明确的市
        districts = row.get("district_list")
        district = next((item for item in districts if isinstance(item, dict)), {}) if isinstance(districts, list) else {}
        area = district.get("area_cn")
        city = area.strip().rstrip("等") if isinstance(area, str) else ""
        if district.get("province") and not district.get("city") and city not in ("北京", "北京市", "上海", "上海市", "天津", "天津市", "重庆", "重庆市"):
            city = ""  # 只有省级代码的“广东”等不是城市。
        # 央企岗多为面议，仅少数写明
        sal_min_raw = _to_number(row.get("min_wage"))
        sal_max_raw = _to_number(row.get("max_wage"))
        unit = str(row.get("wage_unit_cn") or "")
        if sal_min_raw > 0 or sal_max_raw > 0:
            # 换算为 K/月：元→/1000，万→×10，千→原值
            if "万" in unit:
                factor = 10.0
            elif "千" in unit:
                factor = 1.0
            else:
                factor = 0.001
            if "年" in unit:
                factor /= 12
            elif unit and "月" not in unit:
                # 周期不可靠时保留原薪资文字
                factor = 0
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


# 站点注册表
CRAWLERS = {
    "mohrss": MohrssCrawler,
    "iguopin": IguopinCrawler,
}

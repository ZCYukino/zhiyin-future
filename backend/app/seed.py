"""内置种子数据：爬虫失败或未配置 API Key 时的降级样本。

仅含“原始 JD 文本”，结构化抽取仍走 LLM（或规则降级），保证系统可运行、可演示。
"""
from __future__ import annotations

from .crawler.base import RawJob

# 新一代信息技术领域代表性岗位 JD（用于离线采集降级 + RAG 向量库演示）
SEED_RAW_JOBS: list[RawJob] = [
    RawJob(
        title="大模型算法工程师",
        city="北京",
        salary="30-55K·16薪",
        salary_min=30,
        salary_max=55,
        description=(
            "岗位职责：负责大语言模型的训练、微调与部署，研究 Prompt Engineering 与 RAG 技术栈；"
            "优化模型推理效率与效果，构建领域大模型应用。"
            "任职要求：硕士及以上学历，3年以上经验；精通 Python、PyTorch、Transformers；"
            "熟悉 CUDA、DeepSpeed 分布式训练；有 RAG、Agent 落地经验者优先。"
        ),
        source="seed",
        url="",
    ),
    RawJob(
        title="后端开发工程师",
        city="上海",
        salary="20-40K·14薪",
        salary_min=20,
        salary_max=40,
        description=(
            "岗位职责：负责服务端架构设计与核心业务开发，涵盖高并发系统设计、数据库优化、微服务治理。"
            "任职要求：本科及以上学历；精通 Java、Spring Boot；熟悉 MySQL、Redis、Kafka；"
            "有分布式系统设计经验者优先。"
        ),
        source="seed",
        url="",
    ),
    RawJob(
        title="前端开发工程师",
        city="深圳",
        salary="15-30K·14薪",
        salary_min=15,
        salary_max=30,
        description=(
            "岗位职责：负责 Web 用户界面开发，运用 Vue/React 构建高性能前端应用。"
            "任职要求：本科及以上学历；精通 Vue、React、TypeScript；熟悉 CSS、Webpack 工程化。"
        ),
        source="seed",
        url="",
    ),
    RawJob(
        title="数据分析师",
        city="北京",
        salary="12-28K·13薪",
        salary_min=12,
        salary_max=28,
        description=(
            "岗位职责：通过 SQL、Python 对业务数据多维度分析，产出洞察报告与数据看板。"
            "任职要求：本科及以上学历；精通 SQL、Python；熟悉 Tableau、统计学；有 BI 经验优先。"
        ),
        source="seed",
        url="",
    ),
    RawJob(
        title="网络安全工程师",
        city="上海",
        salary="20-40K·14薪",
        salary_min=20,
        salary_max=40,
        description=(
            "岗位职责：负责企业安全体系建设，包括威胁监测、漏洞挖掘、安全审计与应急响应。"
            "任职要求：本科及以上学历；熟悉网络协议、渗透测试；掌握 WAF、SIEM；熟练 Python。"
        ),
        source="seed",
        url="",
    ),
    RawJob(
        title="嵌入式软件工程师",
        city="深圳",
        salary="15-30K·13薪",
        salary_min=15,
        salary_max=30,
        description=(
            "岗位职责：负责嵌入式系统软件开发，涵盖 RTOS、驱动编写、硬件抽象层设计与系统调优。"
            "任职要求：本科及以上学历；精通 C、C++；熟悉 RTOS、ARM；有驱动开发经验优先。"
        ),
        source="seed",
        url="",
    ),
    RawJob(
        title="AI 产品经理",
        city="北京",
        salary="20-40K·14薪",
        salary_min=20,
        salary_max=40,
        description=(
            "岗位职责：负责 AI 产品需求定义、功能规划与落地，理解 AI 技术边界并转化为产品价值。"
            "任职要求：本科及以上学历；熟悉产品规划、数据分析、用户研究；具备 AI 基础知识与项目管理能力。"
        ),
        source="seed",
        url="",
    ),
    RawJob(
        title="测试开发工程师",
        city="杭州",
        salary="15-30K·13薪",
        salary_min=15,
        salary_max=30,
        description=(
            "岗位职责：开发自动化测试框架与工具，涵盖接口测试、性能测试、安全测试。"
            "任职要求：本科及以上学历；精通 Python；熟悉 Selenium、JMeter、CI/CD；有测试框架设计经验。"
        ),
        source="seed",
        url="",
    ),
]

# 采集关键词（新一代信息技术领域）
SEED_KEYWORDS = [
    "大模型算法工程师",
    "人工智能",
    "大数据",
    "物联网",
    "算法工程师",
    "深度学习",
    "NLP",
    "数据分析",
    "云计算",
    "网络安全",
]

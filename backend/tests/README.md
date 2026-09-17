# 后端单元测试

对应赛题可验证性要求「单元测试用例（覆盖率 ≥60%）」。测试基于 `pytest` + `pytest-cov`，
覆盖清洗、抽取、入库、匹配、能力画像、认证等核心规则逻辑（LLM / 网络 / 向量库等基础设施层经
`monkeypatch` 打桩或按 `.coveragerc` 排除，避免依赖外部服务与网络）。

## 运行方式

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest --cov=app --cov-report=term -p no:cacheprovider
```

## 覆盖范围

| 测试文件 | 被测模块 | 覆盖点 |
|---|---|---|
| `test_clean.py` | `app/clean.py` | 去噪、城市归一、相似度去重、技能交叉验证、清洗流水线 |
| `test_extract.py` | `app/extract.py` | 技术栈推断、九类分类一致性、LLM 抽取/岗位定义/能力演化（打桩） |
| `test_ingest.py` | `app/ingest.py` | 标题技能推断、分类推断、规则抽取、技能分级、教育归一、聚合、近期周期、能力演化、岗位关系、图谱、JD 存档去重、单条抽取/发现/能力演化、知识构建 |
| `test_matching.py` | `app/matching.py` | 技能归一、技能点拆分（合取/举例）、包含方向、简历正文直扫、三分类、计分、学历/年限区间、匹配报告 |
| `test_profile.py` | `app/profile.py` | 拆分、项目/证据解析、画像结构校验、清洗 |
| `test_llm.py` | `app/llm.py` | 思维链剥离、JSON 抽取（直出/代码块/围栏/括号/空） |
| `test_auth.py` | `app/auth.py` | JWT 签发/解码往返、非法 token |
| `test_seed.py` | `app/seed.py` | 种子 JD 与关键词有效性 |
| `test_crawler_base.py` | `app/crawler/base.py` | RawJob 数据结构默认值与序列化 |
| `test_settings.py` | `app/settings.py` | 凭据解析与配置优先级 |
| `test_server_apikey.py` | `app/server.py` | API Key 接口的鉴权、掩码、增删改契约 |
| `test_hermetic.py` | 全仓 | 防止测试污染真实快照 / 数据库 / 向量库 |

## 覆盖率口径

`.coveragerc` 将 `source` 限定为 `app` 包，并排除纯 I/O / 基础设施模块
（`server.py`、`db.py`、`store.py`、`rag.py`、`crawler/sources.py`、`enrich.py`），
这些模块需真实网络 / 向量库 / 文件系统，不纳入单元测试计量。

最近一次全量结果（用上面那条命令实测）：

```
162 passed，行覆盖率 81%（≥60% 要求 ✓）
按模块：matching 95% / extract 97% / clean 100% / auth 100% / settings 94% / ingest 75%
```

> 数字会随代码变化，以本地实跑为准；改动后请顺手更新本节。

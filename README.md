# 职引未来 · 岗位能力图谱与职业规划平台

依托多源真实招聘数据，构建「岗位—技能」能力图谱，动态追踪岗位能力演化，提供人岗匹配与差距分析支持。

## 功能特性

- **岗位能力图谱**：30 个核心岗位覆盖 9 大技术分类，226 个图谱节点 / 280 条关联边，支持按岗位下钻查看「初级 / 中级 / 高级」三级技能矩阵。
- **能力演化追踪**：60 条能力变化记录，追踪岗位近两年技能的新增、淘汰与重要性升降。
- **人岗匹配与差距分析**：规则算分 + LLM 生成个性化学习路径，输出技能覆盖、硬门槛核查、差距优先级统计。
- **简历解析**：前端本地解析 PDF / DOCX / TXT 简历，自动提取技能、年限、学历（不上传原始文件）。
- **个人能力画像**：LLM 生成五维竞争力评估 + 软技能 + 优劣势 + 提升建议。
- **新岗位发现**：从真实招聘数据中识别新兴岗位，标注来源与置信度。

> 上述岗位 / 技能 / 演化规模为内置种子数据（开箱即用、离线可用）；通过「管理员 → 数据刷新」接入真实招聘数据后，规模会随采集量增长。

## 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + AntV G6 |
| 后端 | FastAPI + SQLite + ChromaDB |
| 大模型 | DeepSeek（结构化抽取 / 岗位画像 / 能力画像 / 学习路径 / 能力演化推演） |
| 向量模型 | 阿里云百炼 DashScope（RAG 检索 / 向量库） |
| 数据源 | 中国公共招聘网（`job.mohrss.gov.cn`，政府公开岗位信息）+ 国聘（`iguopin.com`，JD 正文完整） |

## 快速开始

### Docker（推荐，单容器托管）

```bash
docker compose up --build
```

启动后访问 **http://localhost:8000**（前端与 API 同源）。

> 未配置 API Key 时：内置种子快照仍提供全部只读功能（岗位 / 图谱 / 匹配算分离线可用）；需实时 LLM 的功能会明确提示先配置 Key。
> 端口 / 数据卷 / 环境变量的完整清单见 `docker-compose.yml` 与 `backend/.env.example`；启动后 `/health` 可探活、`/docs` 为 API 接口清单（路由定义见 `backend/app/server.py`）。

### 本地裸跑

后端：
```bash
cd backend
pip install -r requirements.txt
copy .env.example .env
uvicorn app.server:app --port 8000
```

前端（开发模式）：
```bash
cd ../zcFrontend
npm install
npm run dev
```

> Windows 用 `copy`；macOS / Linux 把 `copy` 换成 `cp`。

## API Key 配置（页面配置）

两个 Key 都不写在配置文件里，首次使用登录后在网页端配置。

| 角色 | 配置入口 | 内容 |
|---|---|---|
| 普通用户 | 顶部导航「API Key 管理」 | DeepSeek 大模型 Key（能力画像 / 匹配报告学习路径） |
| 管理员 | 「数据管理」页 | DeepSeek Key + 阿里云百炼 Key（数据刷新流水线） |

| Key | 用途 | 申请地址 |
|---|---|---|
| DeepSeek | 大模型（结构化抽取 / 岗位画像 / 学习路径） | https://platform.deepseek.com |
| 阿里云百炼 | 向量模型（RAG 检索 / 向量库） | https://bailian.console.aliyun.com |

未配置 Key 的功能行为：岗位 / 图谱 / 匹配算分等只读功能完全正常（快照数据离线可用）；能力画像、学习路径在未配置 Key 时明确提示配置，不生成降级内容；管理员未配置 Key 时数据刷新被拒绝。

## 默认账号

| 角色 | 用户名 | 密码 |
|---|---|---|
| 管理员 | `ZCY` | `123456` |

管理员登录后可进入「数据管理」页：先配置 DeepSeek 与阿里云百炼 Key（页面含官网指引），再触发后端离线采集 + 富化流水线。未配置 Key 时刷新会被拒绝。

### 管理员账号配置

- **用户名**在 `backend/.env` 的 `ADMIN_USERNAME` 修改（改完重启后端生效）：

```bash
ADMIN_USERNAME=ZCY      # 管理员用户名
ADMIN_PASSWORD=123456   # 初始密码（仅首次创建账号时使用）
```

- **密码**与普通用户一致，登录后在网页「个人中心 → 修改密码」里自行修改；服务重启**不会**重置密码。`ADMIN_PASSWORD` 只在管理员账号首次创建时作为初始密码。

> 说明：修改 `.env` 只影响管理员账号，不影响数据库里其他已注册的普通用户。

## 测试与验证

```bash
# 后端（163 个用例，覆盖匹配判定 / 采集流水线 / 鉴权 / 配置等）
cd backend
pip install -r requirements-dev.txt
python -m pytest --cov=app --cov-report=term -p no:cacheprovider

# 前端（构建 + 类型检查）
cd ../zcFrontend
npm install
npx vite build
npx vue-tsc --noEmit
```

后端单元测试的行覆盖率约 81%（口径见 `backend/tests/README.md`，`.coveragerc` 排除了需真实网络 / 向量库的基础设施模块）。

## 目录结构

```
├── backend/                 # FastAPI 后端
│   ├── app/                 # 服务代码（server/db/matching/profile/enrich/ingest/extract…）
│   ├── seed/                # 内置种子快照（30 岗完整画像，离线数据）
│   ├── data/                # 运行时生成（快照 JSON / 向量库 / SQLite 用户库，不提交）
│   ├── .env.example         # 非密钥配置模板（Key 登录后在页面配置）
│   └── requirements.txt
├── zcFrontend/              # Vue 3 前端
│   └── src/                 # 源码（views / components / services / models / utils）
├── Dockerfile               # 多阶段构建（前端 → 后端托管）
├── docker-compose.yml       # 一键编排
└── README.md                # 本文件
```

## 数据流

```
爬虫(中国公共招聘网 / 国聘) → 清洗去重 → LLM 结构化抽取 → 组装知识库
  → 岗位画像富化 → 快照落盘(保留最近 2 版) → JD 片段向量化(ChromaDB)

FastAPI 在线服务（基路径 /api/v1）→ 前端按需读取最新快照
```

> 顺序是有意的：**先落盘快照、再重建向量**——向量库绝不能比被服务的快照更新，否则
> RAG 会检索到快照里根本不存在的内容；反过来（快照新、向量旧）只是检索略滞后，可接受。

| 环节 | 失败时行为 |
|---|---|
| 爬虫 | 降级到内置种子 JD（真实数据源切换，非编造内容） |
| LLM 抽取 / 画像 / 学习路径 | **不降级**：失败的岗位被跳过并在刷新结果中列出；未配置 Key 时功能明确提示配置 |
| 向量化 / RAG 检索 | 未配置 Key 时数据刷新被拒绝（需先配置百炼 Key） |

> 关键设计：**离线采集与在线服务解耦**——不跑采集时，前端照常读上次快照；快照已预生成全部岗位画像，只读功能零 LLM 依赖。内容生成类功能（能力画像 / 学习路径）使用**真实 LLM 输出**，不提供模板降级。

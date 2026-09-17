// ============================================================
// 类型定义与纯函数工具层（数据一律来自后端 /api/v1）
// ============================================================

/** 岗位分类 */
export interface JobCategory {
  id: string
  name: string
  icon: string
  definition: string
}

export const jobCategories: JobCategory[] = [
  { id: 'ai', name: '人工智能', icon: 'cpu', definition: '涵盖机器学习、深度学习、自然语言处理、计算机视觉等方向，利用算法和数据驱动智能决策与自动化。' },
  { id: 'backend', name: '后端开发', icon: 'monitor', definition: '负责服务端架构设计、API开发、数据库管理与业务逻辑实现，是软件系统的核心支撑层。' },
  { id: 'frontend', name: '前端开发', icon: 'picture', definition: '构建用户界面与交互体验，涵盖Web、移动端、桌面端等多平台的前端技术栈。' },
  { id: 'data', name: '数据科学', icon: 'odometer', definition: '通过数据采集、清洗、建模与可视化等手段从海量数据中提取价值，支撑业务决策与智能化应用。' },
  { id: 'cloud', name: '云计算与运维', icon: 'set-up', definition: '涵盖容器编排、DevOps、CI/CD 与云基础设施，保障系统稳定运行并推动自动化交付。' },
  { id: 'security', name: '信息安全', icon: 'lock', definition: '保护信息系统与数据免受攻击、泄露和破坏，涵盖网络安全、应用安全、密码学等领域。' },
  { id: 'embedded', name: '嵌入式与物联网', icon: 'cpu', definition: '面向物联网、芯片、机器人等领域的软硬件协同开发，强调实时性与资源约束。' },
  { id: 'product', name: '产品与项目', icon: 'guide', definition: '负责产品规划、需求管理、项目推进与团队协作，连接技术、业务与用户体验。' },
  { id: 'qa', name: '测试与质量', icon: 'finished', definition: '通过自动化测试、性能测试与质量度量保障软件质量，提升研发效能与交付可信度。' },
]

/** 岗位数据
 *  统计类字段（薪资 / 热度 / 在招公司数 / 趋势 / 城市分布）允许为 null：
 *  后端未采集到就不编造，前端统一以「—」或隐藏区块呈现。 */
export interface JobItem {
  id: string
  name: string
  categoryId: string
  salaryMin: number | null
  salaryMax: number | null
  salaryUnit: string
  description: string
  tags: string[]
  hotScore: number | null
  isNew: boolean
  companyCount: number | null
  trend: 'up' | 'stable' | 'down' | null
  skills: string[]
  cityDistribution: { city: string; count: number }[]
  // 新岗位发现溯源（仅 isNew 岗位，赛题①：多源数据挖掘可溯源）
  source?: string
  confidence?: number
  discoveredDate?: string
  // 后端 AI 生成数据内嵌（GET /jobs 时由服务端注入）
  progression?: SkillProgression
  requirements?: JobRequirement
}

export type SkillStack = 'ai' | 'backend' | 'cloud' | 'data' | 'embedded' | 'frontend' | 'product' | 'qa' | 'security' | 'tool'

/** 单项技能规格 */
export interface SkillSpec {
  name: string
  stack: SkillStack
  /** 该技能在本岗位中的具体用途（后端富化快照注入） */
  desc?: string
}

/** 技能递进矩阵 — 按资历分级 */
export interface SkillProgression {
  junior: SkillSpec[]
  mid: SkillSpec[]
  senior: SkillSpec[]
}

/** 任职要求 — 学历/经验等硬性门槛 */
export interface RequirementRow {
  label: string
  value: string
}

export interface JobRequirement {
  /** 后端未采集到门槛时可能为 null / 空串：对应行不展示 */
  education: string | null
  experience: string | null
  extra?: RequirementRow[]
}

/** 岗位定义要素（赛题①）：核心职责 + 典型行业应用场景 */
export interface JobIntroItem {
  name: string
  desc: string
}
export interface JobIntro {
  duties: string[]
  scenarios: JobIntroItem[]
}

export interface GraphNode {
  id: string
  jobId?: string // 岗位节点对应的岗位 id（后端图谱 job 节点携带）
  label: string
  type: 'job' | 'skill' | 'category'
  category?: string
  techStack?: string
  size?: number
  x?: number
  y?: number
  isNew?: boolean
  isHot?: boolean
  level?: 'entry' | 'mid' | 'senior'
  confidence?: number
}

export interface GraphEdge {
  source: string
  target: string
  label: string
  weight: number
  relation?: 'core' | 'required' | 'optional' | 'transfer' | 'similar' | 'advanced' | 'level'
}

/** 技术栈定义 */
export interface TechStack {
  id: string
  name: string
  icon: string
  description: string
}

export const techStacksForGraph: TechStack[] = [
  { id: 'ai', name: '人工智能', icon: 'cpu', description: '大模型、NLP、深度学习、计算机视觉等算法研发方向' },
  { id: 'backend', name: '后端开发', icon: 'monitor', description: '服务端架构、微服务、数据库、API 与分布式系统' },
  { id: 'frontend', name: '前端开发', icon: 'picture', description: 'Web、移动端与跨端应用开发，用户体验与工程化' },
  { id: 'data', name: '数据科学', icon: 'odometer', description: '数据仓库、ETL、大数据平台、数据分析与可视化' },
  { id: 'cloud', name: '云计算与运维', icon: 'set-up', description: '容器编排、DevOps、CI/CD 与云基础设施' },
  { id: 'security', name: '信息安全', icon: 'lock', description: '网络安全、渗透测试、安全合规与红蓝对抗' },
  { id: 'embedded', name: '嵌入式与物联网', icon: 'cpu', description: '嵌入式软件、物联网、芯片与软硬件协同' },
  { id: 'product', name: '产品与项目', icon: 'guide', description: '产品规划、需求管理、项目推进与运营' },
  { id: 'qa', name: '测试与质量', icon: 'finished', description: '自动化测试、性能测试、质量保障与工程效能' },
]

/** 能力演化 — 技能动态变更记录（jobId 为岗位 id，统一 ID 空间） */
export interface CapabilityChange {
  period: string
  jobId: string
  addedSkills: string[]
  removedSkills: string[]
  importanceUp: string[]   // 重要性提升
  importanceDown: string[] // 重要性下降
}

/** 用户信息 */
export interface UserInfo {
  id: string
  username: string
  role?: string
  name: string
  email: string
  phone: string
  education: string
  school: string
  major: string
  experience: string
  certificates?: string
  internship?: string
  hasResume: boolean
  resumeName: string
  resumeText?: string
  resumeYears?: string
  userSkills: string[]
  awards?: string
  projects?: string
  skillEvidence?: string
}

/** 个人能力画像 — 由后端 /profile/analyze 生成（LLM 优先，规则降级）
 *  简历事实驱动：技能达标度 / 学历 / 经验 / 项目含金量 / 证书获奖，均基于简历内部证据。 */
export interface SkillAssessment {
  mastered: string[] // 达标（有项目/经验上下文证据）
  listed: string[]   // 已掌握但仅罗列（缺证据）
  missing: string[]  // 建议补充（方向内基础/进阶技能，简历未体现）
}

export interface EducationAssessment {
  level: string // 博士 / 硕士 / 本科 / 大专 / 未填写
  score: number
  analysis: string
}

export interface ExperienceAssessment {
  years: number
  level: string // 高级 / 中级 / 初级 / 应届
  analysis: string
}

export interface ProjectAssessment {
  count: number
  quality: string // 高 / 中 / 低 / 无
  signals: string[]
  analysis: string
}

export interface CredentialAssessment {
  certificates: string[]
  awards: string[]
  analysis: string
}

export interface AbilityProfile {
  overallScore: number
  competitivenessLevel: string
  skillAssessment: SkillAssessment
  educationAssessment: EducationAssessment
  experienceAssessment: ExperienceAssessment
  projectAssessment: ProjectAssessment
  credentialAssessment: CredentialAssessment
  strengths: string[]
  shortcomings: string[]
  improvementPriority: string[]
}

/** 匹配分析报告 — 由后端 /matching/analyze 计算 */
export type SkillLevel = 'junior' | 'mid' | 'senior'
export type SkillCoverageStatus = 'mastered' | 'partial' | 'missing'
/** 技能优先级：核心必备 / 重要 / 加分 */
export type SkillPriority = 'must' | 'important' | 'bonus'

export interface SkillStatus {
  name: string
  level: SkillLevel
  stack: SkillStack
  status: SkillCoverageStatus
  priority: SkillPriority
}

export interface ReqCheck {
  label: string
  user: string
  required: string
  passed: boolean
}

/** 学习路径：每个缺口技能的落地步骤 */
export interface LearningStep {
  skill: string
  stack: SkillStack
  resource: string
  milestone: string
}
export interface LearningStage {
  stage: string
  period: string
  focus: string
  steps: LearningStep[]
}

export interface MatchReport {
  score: number
  verdict: 'strong' | 'fair' | 'partial' | 'weak'
  verdictLabel: string
  oneLineSummary: string | null
  skillCoverage: {
    total: number
    mastered: SkillStatus[]
    partial: SkillStatus[]
    missing: SkillStatus[]
  }
  requirements: ReqCheck[]
  learningPath: LearningStage[]
  priorityGaps: Record<SkillPriority, number>
  /** 学习路径/总结的 LLM 生成状态：ok=真实生成 / no_api_key=未配置 Key / failed=生成失败 */
  llmStatus: 'ok' | 'no_api_key' | 'failed'
}

/** 后端持久化的匹配报告：连同目标岗位 id 存储，便于再次进入时恢复选择 */
export interface SavedMatchReport {
  jobId: string
  report: MatchReport
}

/** 技能优先级：按资历级别映射（与后端 matching.priority_from_level 一致） */
export function priorityOf(level: SkillLevel): SkillPriority {
  return level === 'junior' ? 'must' : level === 'mid' ? 'important' : 'bonus'
}

/** 从技能名粗略推断 stack（回退场景使用），与 SkillStack 全量对齐 */
export function inferStackFromName(name: string): SkillStack {
  const n = name.toLowerCase()
  if (['python', 'pytorch', 'tensorflow', 'cuda', 'llm', 'bert', 'transformer', 'cnn', 'rnn', '机器学习', '深度学习', '自然语言', '自然语言处理', '计算机视觉', '语音识别', 'rag', 'agent', '多智能体', 'autogen', 'crewai', 'langchain', 'langgraph', 'rlhf', 'diffusion', 'mamba', 'svm', '决策树', '大模型', 'prompt', '推理', '端侧'].some(k => n.includes(k.toLowerCase()))) return 'ai'
  if (['sql', 'spark', 'flink', 'hadoop', 'etl', 'elt', '数仓', 'olap', 'tableau', '数据', '统计分析', '挖掘', '标注', '质检', 'dama', 'cvat', 'label studio', 'scale ai', 'iaa'].some(k => n.includes(k.toLowerCase()))) return 'data'
  if (['java', 'spring', 'golang', 'go', '微服务', '后端', 'jvm', 'redis', 'kafka', 'mysql', 'dubbo', '分布式系统', 'api'].some(k => n.includes(k.toLowerCase()))) return 'backend'
  if (['vue', 'react', 'typescript', 'javascript', 'css', 'webpack', 'wasm', 'webassembly', 'arkts', 'arkui', '前端', 'ssr', 'ssg', '鸿蒙'].some(k => n.includes(k.toLowerCase()))) return 'frontend'
  if (['k8s', 'kubernetes', 'docker', 'istio', 'serverless', '容器', '云原生', 'devops', 'ci/cd', 'jenkins', 'terraform', 'linux'].some(k => n.includes(k.toLowerCase()))) return 'cloud'
  if (['渗透', '安全', 'waf', 'siem', 'soc', '漏洞', '加密', 'cissp', '等保'].some(k => n.includes(k.toLowerCase()))) return 'security'
  if (['rtos', 'arm', '驱动', '单片机', 'iot', '物联网', '芯片', '嵌入式'].some(k => n.includes(k.toLowerCase()))) return 'embedded'
  if (['产品', '用户研究', '项目管理', '需求', '运营', 'prd', '用户故事', '竞品', '可行性', '协作', '优先级', '敏捷', 'pmp'].some(k => n.includes(k.toLowerCase()))) return 'product'
  if (['测试', 'selenium', 'jmeter', '用例', '质量', '自动化测试', '性能测试'].some(k => n.includes(k.toLowerCase()))) return 'qa'
  return 'tool'
}

/** API Key 状态（对齐后端 GET /api/v1/apikey） */
export interface ApiKeyStatus {
  configured: boolean
  masked: string
  updatedAt: string
}

/** 当前账号的 API Key 配置（普通用户仅 deepseek 键；管理员另有 dashscope） */
export interface ApiKeyConfig {
  deepseek: ApiKeyStatus
  dashscope?: ApiKeyStatus
  effective: {
    llmModel: string
    embeddingModel: string
  }
}

// ============================================================
// 缺失值展示工具：后端字段可能为 null（未采集到即不编造），
// 统一以「—」占位，避免出现 0-0K / undefined 这类伪造感数据。
// ============================================================

/** 缺失值占位符 */
export const MISSING_VALUE = '—'

/** 紧凑薪资区间（如 8-15K）；任一端缺失即占位 */
export function salaryRangeText(min: number | null | undefined, max: number | null | undefined): string {
  return min == null || max == null ? MISSING_VALUE : `${min}-${max}K`
}

/** 数值展示（如 23）；null 即占位 */
export function countText(v: number | null | undefined): string {
  return v == null ? MISSING_VALUE : String(v)
}

/** 市场趋势符号：null（未采集）时不显示任何符号，绝不默认成「上升」 */
export function trendGlyph(t: JobItem['trend']): string {
  return t === 'up' ? '↑' : t === 'down' ? '↓' : t === 'stable' ? '→' : ''
}

/** 市场趋势文案 */
export function trendText(t: JobItem['trend']): string {
  return t === 'up' ? '↑ 上升' : t === 'down' ? '↓ 下降' : t === 'stable' ? '→ 稳定' : ''
}

/** 岗位能力变更数据源：当前后端仅采集自中国公共招聘网 */
export function capabilitySourceOf(): string[] {
  return ['中国公共招聘网 JD 聚合']
}

/** 单个周期变更的「更新说明」（数据驱动的解释文案） */
export function changeReasonOf(c: CapabilityChange): string {
  const parts: string[] = []
  if (c.addedSkills.length) parts.push(`新增 ${c.addedSkills.length} 项核心技能`)
  if (c.removedSkills.length) parts.push(`淘汰 ${c.removedSkills.length} 项过时技能`)
  if (c.importanceUp.length) parts.push(`${c.importanceUp.length} 项技能重要性上升`)
  if (c.importanceDown.length) parts.push(`${c.importanceDown.length} 项技能重要性下降`)
  return parts.join('；') || '岗位技能要求趋于稳定'
}

/** 全站统一的岗位名清单（首页 / 登录 / 顶栏浮动背景共用，避免重复硬编码） */
export const careerNames: string[] = [
  '大模型算法工程师', 'AI训练师', 'AI产品经理', '深度学习工程师', 'NLP工程师', '计算机视觉工程师',
  '多模态系统工程师', 'AI代理开发工程师', '模型安全评测工程师', '后端开发工程师', '前端开发工程师',
  '全栈工程师', '鸿蒙开发工程师', '数据分析师', '数据工程师', '数据科学家', '合成数据工程师',
  'DevOps工程师', '云原生工程师', 'MLOps工程师', '网络安全工程师', '信息安全工程师',
  '嵌入式工程师', '物联网工程师', 'RPA工程师', '测试开发工程师', 'AIGC工程师',
  '提示词工程师', 'AI应用开发工程师',
]

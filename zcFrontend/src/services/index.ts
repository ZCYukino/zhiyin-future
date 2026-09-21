// 统一数据访问层：所有数据类接口直接请求后端 /api/v1，失败即抛错
import type {
  JobItem,
  GraphNode,
  GraphEdge,
  CapabilityChange,
  UserInfo,
  MatchReport,
  JobIntro,
  JobRequirement,
  SkillProgression,
  AbilityProfile,
  SavedMatchReport,
  ApiKeyConfig,
  ApiKeyStatus,
} from '@/models'
import {
  parseResumeFile as doParseResumeFile,
  parseResumeText as doParseResumeText,
} from '@/utils/resumeParser'
import type { ResumeParseResult } from '@/utils/resumeParser'
import { http, httpPost, httpPut, httpDelete, qs } from '@/utils/http'

/** 岗位列表查询参数 */
export interface JobListParams {
  categoryId?: string
  keyword?: string
  newOnly?: boolean
  hot?: boolean
}

/** 新岗位发现日志项 */
export interface DiscoveryLogItem {
  date: string
  jobName: string
  jobId: string
  source: string
  confidence: number
  description: string
}

/** 岗位详情聚合（GET /jobs/:id） */
export interface JobDetailData {
  job: JobItem
  intro: JobIntro | null
  requirements: JobRequirement | null
  progression: SkillProgression | null
}

/** 认证响应（注册/登录） */
export interface AuthResponse {
  token: string
  user: UserInfo
}

/** 管理员数据刷新状态 */
export interface RefreshStatus {
  running: boolean
  stage: string
  progress: number
  startedAt: string | null
  finishedAt: string | null
  error: string | null
  result: {
    jobCount: number
    profileCount: number
    failedJobs: string[]
    failedProfiles: string[]
  } | null
}

/** 岗位画像（详情页富文本） */
export interface JobProfileScenario {
  name: string
  desc: string
}
export interface JobProfileRequirement {
  education: string
  experience: string
  extra: { label: string; value: string }[]
}
export interface JobProfileSoftSkill {
  name: string
  desc: string
}
export interface JobProfileCareerStage {
  stage: string
  title: string
  desc: string
}
export interface JobProfileSkillSpec {
  name: string
  desc?: string
}
export interface JobProfileSkillMatrix {
  junior: JobProfileSkillSpec[]
  mid: JobProfileSkillSpec[]
  senior: JobProfileSkillSpec[]
}
export interface JobProfile {
  overview: string
  duties: string[]
  scenarios: JobProfileScenario[]
  requirements: JobProfileRequirement
  skills: JobProfileSkillMatrix
  softSkills: JobProfileSoftSkill[]
  careerPath: JobProfileCareerStage[]
  salaryReference: string
  industryOutlook: string
}

export const services = {
  /** 岗位列表（GET /jobs，支持分类/关键字/新岗位/热门筛选） */
  getJobs(params: JobListParams = {}): Promise<JobItem[]> {
    const path = '/jobs' + qs({ categoryId: params.categoryId, keyword: params.keyword, newOnly: params.newOnly, hot: params.hot })
    return http<JobItem[]>(path)
  },

  /** 热门 TOP10（GET /jobs/hot） */
  getHotJobs(): Promise<JobItem[]> {
    return http<JobItem[]>('/jobs/hot')
  },

  /** 岗位介绍页精选：最热门 30 条（含 5 新兴） */
  getFeaturedJobs(): Promise<JobItem[]> {
    return http<JobItem[]>('/jobs/featured')
  },

  /** 岗位详情聚合（GET /jobs/:id，含岗位介绍/任职要求/技能矩阵） */
  async getJobDetail(jobId: string): Promise<JobDetailData | null> {
    const d = await http<JobDetailData | null>(`/jobs/${jobId}`)
    return d?.job ? d : null
  },

  /** 能力图谱数据（GET /graph） */
  getGraph(): Promise<{ nodes: GraphNode[]; edges: GraphEdge[] }> {
    return http<{ nodes: GraphNode[]; edges: GraphEdge[] }>('/graph')
  },

  /** 能力演化记录（GET /capability-changes，按岗位过滤可选） */
  getCapabilityChanges(jobId?: string): Promise<CapabilityChange[]> {
    const path = '/capability-changes' + (jobId ? qs({ jobId }) : '')
    return http<CapabilityChange[]>(path)
  },

  /** 新岗位发现日志（GET /discoveries） */
  getDiscoveryLog(): Promise<DiscoveryLogItem[]> {
    return http<DiscoveryLogItem[]>('/discoveries')
  },

  /** 简历解析（本地实现：pdfjs/mammoth + 词典匹配） */
  parseResumeFile(file: File): Promise<ResumeParseResult> {
    return doParseResumeFile(file)
  },
  parseResumeText(text: string): ResumeParseResult {
    return doParseResumeText(text)
  },

  /** 人岗匹配分析（规则算分 + LLM 建议） */
  analyzeMatching(job: JobItem, user: UserInfo): Promise<MatchReport> {
    return httpPost<MatchReport>('/matching/analyze', { jobId: job.id, user })
  },

  /** 读取上次持久化的匹配报告（GET /matching/report，未生成返回 null） */
  getMatchReport(): Promise<SavedMatchReport | null> {
    return http<SavedMatchReport | null>('/matching/report')
  },

  /** 清除持久化的匹配报告（DELETE /matching/report） */
  clearMatchReport(): Promise<{ ok: boolean }> {
    return httpDelete<{ ok: boolean }>('/matching/report')
  },

  /** 个人能力画像（后端 LLM 生成，失败即报错） */
  analyzeAbilityProfile(): Promise<AbilityProfile> {
    return httpPost<AbilityProfile>('/profile/analyze', {})
  },

  /** 读取上次持久化的能力画像（GET /profile，未生成返回 null） */
  getAbilityProfile(): Promise<AbilityProfile | null> {
    return http<AbilityProfile | null>('/profile')
  },

  /** 清除持久化的能力画像（DELETE /profile） */
  clearAbilityProfile(): Promise<{ ok: boolean }> {
    return httpDelete<{ ok: boolean }>('/profile')
  },

  /** 注册（POST /auth/register） */
  register(username: string, password: string): Promise<AuthResponse> {
    return httpPost<AuthResponse>('/auth/register', { username, password })
  },

  /** 登录（POST /auth/login） */
  login(username: string, password: string): Promise<AuthResponse> {
    return httpPost<AuthResponse>('/auth/login', { username, password })
  },

  /** 当前用户（GET /auth/me） */
  getMe(): Promise<UserInfo> {
    return http<UserInfo>('/auth/me')
  },

  /** 更新用户资料（PUT /auth/me） */
  updateMe(fields: Partial<UserInfo>): Promise<UserInfo> {
    return httpPut<UserInfo>('/auth/me', fields)
  },

  /** 修改密码（POST /auth/change-password） */
  changePassword(oldPassword: string, newPassword: string): Promise<{ ok: boolean }> {
    return httpPost<{ ok: boolean }>('/auth/change-password', { oldPassword, newPassword })
  },

  /** 岗位画像（快照预生成，缺画像返回 404） */
  async getJobProfile(jobId: string): Promise<JobProfile | null> {
    const d = await http<JobProfile>(`/jobs/${jobId}/profile`)
    return d?.duties?.length ? d : null
  },

  /** 管理员：触发一次完整数据刷新（POST /admin/refresh） */
  adminRefresh(): Promise<{ ok: boolean; message: string }> {
    return httpPost<{ ok: boolean; message: string }>('/admin/refresh', {})
  },

  /** 管理员：查询刷新进度（GET /admin/refresh/status） */
  getAdminRefreshStatus(): Promise<RefreshStatus> {
    return http<RefreshStatus>('/admin/refresh/status')
  },

  /** API Key 状态（GET /apikey，只含脱敏值） */
  getApiKeyConfig(): Promise<ApiKeyConfig> {
    return http<ApiKeyConfig>('/apikey')
  },

  /** 保存 API Key（后端校验，失败抛错）：返回体附带两家最新状态 */
  saveApiKey(
    provider: 'deepseek' | 'dashscope',
    apiKey: string,
  ): Promise<{ ok: boolean; deepseek?: ApiKeyStatus; dashscope?: ApiKeyStatus }> {
    return httpPut<{ ok: boolean; deepseek?: ApiKeyStatus; dashscope?: ApiKeyStatus }>('/apikey', { provider, apiKey })
  },

  /** 清除 API Key（DELETE /apikey?provider=...） */
  clearApiKey(provider: 'deepseek' | 'dashscope'): Promise<{ ok: boolean }> {
    return httpDelete<{ ok: boolean }>(`/apikey?provider=${provider}`)
  },
}

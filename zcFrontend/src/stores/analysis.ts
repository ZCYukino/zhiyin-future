import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AbilityProfile, JobItem, MatchReport, UserInfo } from '@/models'
import { services } from '@/services'

/**
 * 个人能力画像 + 人岗匹配报告 的统一状态：
 * 生成过程较长（后端 LLM），把 loading 状态与结果提升到 Pinia 单例，
 * 使得用户在生成中途切换到其它页面再回来时，等待界面与结果都不会丢失。
 */
export const useAnalysisStore = defineStore('analysis', () => {
  // ===== 个人能力画像 =====
  const abilityProfile = ref<AbilityProfile | null>(null)
  const profileLoading = ref(false)
  const profileError = ref('')
  const profileLoaded = ref(false)

  // ===== 人岗匹配报告 =====
  const matchReport = ref<MatchReport | null>(null)
  const matchJobId = ref<string | null>(null)
  const matchingLoading = ref(false)
  const matchingError = ref('')
  const matchLoaded = ref(false)

  /** 进入用户中心时：拉取上次持久化的能力画像（未生成则为 null） */
  async function loadAbilityProfile(force = false): Promise<void> {
    if (profileLoaded.value && !force) return
    profileLoaded.value = true
    try {
      abilityProfile.value = await services.getAbilityProfile()
    } catch {
      /* 后端读取失败时保持空，用户仍可手动生成 */
    }
  }

  /** 生成能力画像（后端持久化一份，覆盖旧画像） */
  async function generateAbilityProfile(): Promise<void> {
    profileLoading.value = true
    profileError.value = ''
    try {
      abilityProfile.value = await services.analyzeAbilityProfile()
      profileLoaded.value = true
    } catch (err: any) {
      profileError.value = err?.message || '画像生成失败，请检查后端是否已启动'
    } finally {
      profileLoading.value = false
    }
  }

  /** 上传新简历后旧画像失效：清空本地 + 后端 */
  async function clearAbilityProfile(): Promise<void> {
    abilityProfile.value = null
    profileError.value = ''
    profileLoaded.value = false
    try {
      await services.clearAbilityProfile()
    } catch {
      /* 后端清除失败仅影响下次读取，忽略 */
    }
  }

  /** 进入人岗匹配页时：拉取上次持久化的匹配报告（未生成则为 null） */
  async function loadMatchReport(force = false): Promise<void> {
    if (matchLoaded.value && !force) return
    if (matchingLoading.value) return // 生成进行中，避免读取到旧数据覆盖等待态
    matchLoaded.value = true
    try {
      const saved = await services.getMatchReport()
      if (saved?.report) {
        matchReport.value = saved.report
        matchJobId.value = saved.jobId
      }
    } catch {
      /* 后端读取失败时保持空，用户仍可手动重新分析 */
    }
  }

  /** 生成匹配报告（后端持久化一份，覆盖旧报告） */
  async function generateMatchReport(job: JobItem, user: UserInfo): Promise<void> {
    matchingLoading.value = true
    matchingError.value = ''
    matchJobId.value = job.id
    matchLoaded.value = true
    try {
      matchReport.value = await services.analyzeMatching(job, user)
    } catch (err: any) {
      matchingError.value = err?.message || '匹配分析失败，请稍后重试'
      // 重新分析失败时清空旧报告与目标岗位，避免 hasReport 按新 jobId 匹配到旧岗位的报告内容
      matchReport.value = null
      matchJobId.value = null
    } finally {
      matchingLoading.value = false
    }
  }

  /** 上传新简历后旧报告失效：清空本地 + 后端 */
  async function clearMatchReport(): Promise<void> {
    matchReport.value = null
    matchJobId.value = null
    matchingError.value = ''
    matchLoaded.value = false
    try {
      await services.clearMatchReport()
    } catch {
      /* 后端清除失败仅影响下次读取，忽略 */
    }
  }

  /** 账号切换（登录/注册/登出）时清空全部本地状态，避免 A 用户的报告/画像残留给 B 用户。 */
  function reset(): void {
    abilityProfile.value = null
    profileLoading.value = false
    profileError.value = ''
    profileLoaded.value = false
    matchReport.value = null
    matchJobId.value = null
    matchingLoading.value = false
    matchingError.value = ''
    matchLoaded.value = false
  }

  return {
    abilityProfile,
    profileLoading,
    profileError,
    loadAbilityProfile,
    generateAbilityProfile,
    clearAbilityProfile,
    matchReport,
    matchJobId,
    matchingLoading,
    matchingError,
    loadMatchReport,
    generateMatchReport,
    clearMatchReport,
    reset,
  }
})
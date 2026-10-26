import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { AbilityProfile, JobItem, MatchReport, UserInfo } from '@/models'
import { services } from '@/services'
import { captureSession, isCurrentSession } from '@/utils/session'

/**
 * 画像与匹配报告的统一状态：生成过程较长，提升到 Pinia 单例，切页不丢失。
 */
export const useAnalysisStore = defineStore('analysis', () => {
  const abilityProfile = ref<AbilityProfile | null>(null)
  const profileLoading = ref(false)
  const profileError = ref('')
  const profileLoaded = ref(false)

  const matchReport = ref<MatchReport | null>(null)
  const matchJobId = ref<string | null>(null)
  const matchingLoading = ref(false)
  const matchingError = ref('')
  const matchLoaded = ref(false)
  let profileVersion = 0
  let matchVersion = 0
  let profileReading = false
  let matchReading = false

  /** 进入用户中心时：拉取上次持久化的能力画像（未生成则为 null） */
  async function loadAbilityProfile(force = false): Promise<void> {
    if ((profileLoaded.value && !force) || profileLoading.value || profileReading) return
    const session = captureSession()
    const version = ++profileVersion
    profileReading = true
    try {
      const result = await services.getAbilityProfile()
      if (!isCurrentSession(session) || version !== profileVersion) return
      abilityProfile.value = result
      profileLoaded.value = true
      profileError.value = ''
    } catch (err: any) {
      if (isCurrentSession(session) && version === profileVersion) profileError.value = err?.message || '读取画像失败，请重试'
    } finally {
      if (version === profileVersion) profileReading = false
    }
  }

  /** 生成能力画像（后端持久化一份，覆盖旧画像） */
  async function generateAbilityProfile(): Promise<void> {
    if (profileLoading.value) return
    const session = captureSession()
    const version = ++profileVersion
    profileReading = false
    profileLoading.value = true
    profileError.value = ''
    try {
      const result = await services.analyzeAbilityProfile()
      if (!isCurrentSession(session) || version !== profileVersion) return
      abilityProfile.value = result
      profileLoaded.value = true
    } catch (err: any) {
      if (isCurrentSession(session) && version === profileVersion) profileError.value = err?.message || '画像生成失败，请检查后端是否已启动'
    } finally {
      if (version === profileVersion) profileLoading.value = false
    }
  }

  /** 上传新简历后旧画像失效：清空本地 + 后端 */
  async function clearAbilityProfile(): Promise<void> {
    const session = captureSession()
    const version = ++profileVersion
    profileReading = false
    profileLoading.value = false
    abilityProfile.value = null
    profileError.value = ''
    profileLoaded.value = true
    try {
      await services.clearAbilityProfile()
    } catch (err: any) {
      if (isCurrentSession(session) && version === profileVersion) {
        profileLoaded.value = false
        profileError.value = err?.message || '清除画像失败，请重试'
      }
    }
  }

  /** 进入人岗匹配页时：拉取上次持久化的匹配报告（未生成则为 null） */
  async function loadMatchReport(force = false): Promise<void> {
    if ((matchLoaded.value && !force) || matchingLoading.value || matchReading) return
    const session = captureSession()
    const version = ++matchVersion
    matchReading = true
    try {
      const saved = await services.getMatchReport()
      if (!isCurrentSession(session) || version !== matchVersion) return
      matchReport.value = saved?.report ?? null
      matchJobId.value = saved?.jobId ?? null
      matchLoaded.value = true
      matchingError.value = ''
    } catch (err: any) {
      if (isCurrentSession(session) && version === matchVersion) matchingError.value = err?.message || '读取匹配报告失败，请重试'
    } finally {
      if (version === matchVersion) matchReading = false
    }
  }

  /** 生成匹配报告（后端持久化一份，覆盖旧报告） */
  async function generateMatchReport(job: JobItem, user: UserInfo): Promise<void> {
    if (matchingLoading.value) return
    const session = captureSession()
    const version = ++matchVersion
    matchReading = false
    matchingLoading.value = true
    matchingError.value = ''
    matchReport.value = null
    matchJobId.value = job.id
    matchLoaded.value = true
    try {
      const result = await services.analyzeMatching(job, user)
      if (!isCurrentSession(session) || version !== matchVersion) return
      matchReport.value = result
    } catch (err: any) {
      if (!isCurrentSession(session) || version !== matchVersion) return
      matchingError.value = err?.message || '匹配分析失败，请稍后重试'
      // 失败时清空旧报告，避免 hasReport 匹配到旧内容
      matchReport.value = null
      matchJobId.value = null
    } finally {
      if (version === matchVersion) matchingLoading.value = false
    }
  }

  /** 上传新简历后旧报告失效：清空本地 + 后端 */
  async function clearMatchReport(): Promise<void> {
    const session = captureSession()
    const version = ++matchVersion
    matchReading = false
    matchingLoading.value = false
    matchReport.value = null
    matchJobId.value = null
    matchingError.value = ''
    matchLoaded.value = true
    try {
      await services.clearMatchReport()
    } catch (err: any) {
      if (isCurrentSession(session) && version === matchVersion) {
        matchLoaded.value = false
        matchingError.value = err?.message || '清除报告失败，请重试'
      }
    }
  }

  /** 账号切换时清空本地状态，避免残留给下一个用户 */
  function reset(): void {
    profileVersion++
    matchVersion++
    profileReading = false
    matchReading = false
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

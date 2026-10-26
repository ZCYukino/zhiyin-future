import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/models'
import { services } from '@/services'
import { useAnalysisStore } from './analysis'
import { captureSession, isCurrentSession, setSessionToken, clearSession, onSessionExpired, onSessionChanged } from '@/utils/session'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>('')
  const userInfo = ref<UserInfo | null>(null)
  const isLoggedIn = computed(() => !!token.value && !!userInfo.value)
  const authError = ref('')
  let initPromise: Promise<void> | null = null
  let initSession: ReturnType<typeof captureSession> | null = null
  let updateVersion = 0

  function clearLocalState() {
    updateVersion++
    token.value = ''
    userInfo.value = null
    initPromise = null
    initSession = null
    useAnalysisStore().reset()
  }
  onSessionExpired(() => {
    clearLocalState()
    authError.value = '登录已过期，请重新登录'
  })
  onSessionChanged(() => {
    clearLocalState()
    authError.value = ''
    void init()
  })

  /** 应用启动时：读本地 token 并向后端校验，失败则清除登录态 */
  async function init() {
    const session = captureSession()
    const saved = session.token
    if (!saved) {
      if (token.value || userInfo.value) clearLocalState()
      return
    }
    if (userInfo.value && token.value === saved) return
    if (initPromise && initSession && isCurrentSession(initSession)) return initPromise
    if (token.value && token.value !== saved) clearLocalState()
    initSession = session
    const pending = (async () => {
      try {
        const user = await services.getMe()
        if (!isCurrentSession(session)) return
        token.value = saved
        userInfo.value = user
        authError.value = ''
      } catch (err: any) {
        if (!isCurrentSession(session)) return
        if (err?.status === 401) logout()
        authError.value = err?.message || '无法连接服务，请稍后重新登录'
      }
    })()
    initPromise = pending
    await pending
    if (initPromise === pending) {
      initPromise = null
      initSession = null
    }
  }

  async function login(username: string, password: string) {
    const session = captureSession()
    const res = await services.login(username, password)
    if (!isCurrentSession(session)) throw new Error('登录操作已失效，请重试')
    setSessionToken(res.token)
    token.value = res.token
    userInfo.value = res.user
    authError.value = ''
    useAnalysisStore().reset()
  }

  async function register(username: string, password: string) {
    const session = captureSession()
    const res = await services.register(username, password)
    if (!isCurrentSession(session)) throw new Error('注册操作已失效，请重试')
    setSessionToken(res.token)
    token.value = res.token
    userInfo.value = res.user
    authError.value = ''
    useAnalysisStore().reset()
  }

  function logout() {
    clearSession()
    clearLocalState()
    authError.value = ''
  }

  /** 只提交服务端确认后的用户信息，不能把上一个账号的响应写进来。 */
  async function updateUserInfo(info: Partial<UserInfo>): Promise<boolean> {
    const user = userInfo.value
    const session = captureSession()
    if (!user || user !== userInfo.value) return false
    const version = ++updateVersion
    try {
      const updated = await services.updateMe(info)
      if (!isCurrentSession(session) || version !== updateVersion || !updated) return false
      const previous = userInfo.value
      userInfo.value = updated
      if (previous?.analysisRevision !== updated.analysisRevision) useAnalysisStore().reset()
      return true
    } catch {
      return false
    }
  }

  return { token, userInfo, isLoggedIn, authError, init, login, register, logout, updateUserInfo }
})

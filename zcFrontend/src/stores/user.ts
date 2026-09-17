import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserInfo } from '@/models'
import { services } from '@/services'
import { useAnalysisStore } from './analysis'

export const useUserStore = defineStore('user', () => {
  const token = ref<string>('')
  const userInfo = ref<UserInfo | null>(null)
  const isLoggedIn = computed(() => !!token.value)

  /** 应用启动时：读本地 token 并向后端校验，失败则清除登录态 */
  async function init() {
    const saved = localStorage.getItem('zc_token')
    if (!saved) return
    token.value = saved
    try {
      userInfo.value = await services.getMe()
    } catch {
      token.value = ''
      userInfo.value = null
      localStorage.removeItem('zc_token')
    }
  }

  async function login(username: string, password: string) {
    const res = await services.login(username, password)
    token.value = res.token
    userInfo.value = res.user
    localStorage.setItem('zc_token', res.token)
    useAnalysisStore().reset()
  }

  async function register(username: string, password: string) {
    const res = await services.register(username, password)
    token.value = res.token
    userInfo.value = res.user
    localStorage.setItem('zc_token', res.token)
    useAnalysisStore().reset()
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('zc_token')
    useAnalysisStore().reset()
  }

  /** 本地立即更新 + 后端持久化；返回是否成功（失败仅本地，供调用方提示） */
  async function updateUserInfo(info: Partial<UserInfo>): Promise<boolean> {
    if (userInfo.value) {
      userInfo.value = { ...userInfo.value, ...info }
    }
    try {
      const updated = await services.updateMe(info)
      if (updated) userInfo.value = updated
      return true
    } catch {
      /* 后端不可用，仅本地 */
      return false
    }
  }

  return { token, userInfo, isLoggedIn, init, login, register, logout, updateUserInfo }
})

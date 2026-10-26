// 新登录可能复用同一个 token 字符串，不能只靠 token 判断会话是否变化。
let generation = 0
let onExpired: (() => void) | undefined
let onChanged: (() => void) | undefined
let observedToken = localStorage.getItem('zc_token')

function reconcileToken(): string | null {
  const token = localStorage.getItem('zc_token')
  if (token !== observedToken) {
    observedToken = token
    generation++
    onChanged?.()
  }
  return token
}

// 监听器只在这里注册一次，各 store 仅替换回调。
if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.storageArea !== localStorage || (event.key !== 'zc_token' && event.key !== null)) return
    observedToken = localStorage.getItem('zc_token')
    generation++
    onChanged?.()
  })
}

export function captureSession() {
  return { token: reconcileToken(), generation }
}

export function isCurrentSession(session: ReturnType<typeof captureSession>): boolean {
  const current = captureSession()
  return session.generation === current.generation && session.token === current.token
}

export function setSessionToken(token: string): void {
  generation++
  observedToken = token
  localStorage.setItem('zc_token', token)
}

export function clearSession(): void {
  generation++
  observedToken = null
  localStorage.removeItem('zc_token')
}

export function onSessionChanged(handler: () => void): void {
  onChanged = handler
}

export function onSessionExpired(handler: () => void): void {
  onExpired = handler
}

export function expireSession(session: ReturnType<typeof captureSession>): void {
  if (!session.token || !isCurrentSession(session)) return
  clearSession()
  onExpired?.()
}

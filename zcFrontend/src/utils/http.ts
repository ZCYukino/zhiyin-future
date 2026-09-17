// ============================================================
// HTTP 客户端封装：统一 baseURL、token 注入、错误处理
// 后端基路径 /api/v1（接口清单见 backend/app/server.py 的路由定义，启动后可在 /docs 查看）
// ============================================================

const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) || 'http://localhost:8000/api/v1'

/** 通用 GET/POST，失败抛错 */
export async function http<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('zc_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string> | undefined),
  }
  if (token) headers.Authorization = `Bearer ${token}`

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers })
  if (!res.ok) {
    let detail: unknown = ''
    try {
      const data = await res.json()
      detail = (data && (data.detail || data.message)) || ''
    } catch {
      /* 非 JSON 响应，忽略 */
    }
    // FastAPI 422 的 detail 是数组（逐字段校验错误），非字符串一律回退到状态码，
    // 否则 new Error(detail) 会把它字符串化成 [object Object] 弹给用户
    const e = new Error(typeof detail === 'string' && detail ? detail : `HTTP ${res.status}`)
    ;(e as any).status = res.status
    throw e
  }
  // 处理 204 / 空响应体：res.json() 会抛 "Unexpected end of JSON input"
  const text = await res.text()
  return (text ? JSON.parse(text) : undefined) as T
}

/** POST JSON 便捷封装 */
export function httpPost<T>(path: string, body: unknown): Promise<T> {
  return http<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

/** PUT JSON 便捷封装 */
export function httpPut<T>(path: string, body: unknown): Promise<T> {
  return http<T>(path, { method: 'PUT', body: JSON.stringify(body) })
}

/** DELETE 便捷封装 */
export function httpDelete<T>(path: string): Promise<T> {
  return http<T>(path, { method: 'DELETE' })
}

/** 构造查询串 */
export function qs(params: Record<string, string | number | boolean | undefined>): string {
  const entries = Object.entries(params).filter(([, v]) => v !== undefined && v !== '')
  if (!entries.length) return ''
  return '?' + entries.map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`).join('&')
}

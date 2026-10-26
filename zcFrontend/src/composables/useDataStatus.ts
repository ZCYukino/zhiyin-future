import { computed, ref } from 'vue'
import { services } from '@/services'
import type { DataStatus } from '@/services'

const status = ref<DataStatus | null>(null)
const loading = ref(false)
const loadFailed = ref(false)
let version = 0
let pending: Promise<void> | null = null

const message = computed(() => {
  if (loadFailed.value) return '数据来源状态读取失败，请重试；当前来源状态待核验。'
  if (!status.value) return '正在读取数据来源状态…'
  const evolution = status.value.capabilityChangesKind === 'demo'
    ? '能力演化为内置演示示例，非真实历史统计。'
    : ['inferred', 'llm_inferred'].includes(status.value.capabilityChangesKind || '')
      ? '能力演化为模型推演，非市场历史统计。'
      : status.value.capabilityChangesKind === 'unavailable'
        ? '当前暂无可用的能力演化记录。'
        : '能力演化来源待核验。'
  if (status.value.mode === 'demo') return `当前为内置演示数据，尚未完成真实采集。${evolution}`
  if (status.value.mode === 'real') {
    const count = status.value.archiveCount == null ? '' : `累计 ${status.value.archiveCount} 条 JD、`
    return `当前为真实招聘采样数据，${count}${status.value.jobCount} 类岗位；${evolution}`
  }
  return `当前为历史快照，来源状态待核验。${evolution}`
})

async function load(force = false): Promise<void> {
  if (!force && pending) return pending
  if (!force && status.value && !loadFailed.value) return
  const current = ++version
  loading.value = true
  const request = (async () => {
    try {
      const result = await services.getDataStatus()
      if (current !== version) return
      status.value = result
      loadFailed.value = false
    } catch {
      if (current === version) loadFailed.value = true
    } finally {
      if (current === version) loading.value = false
    }
  })()
  pending = request
  await request
  if (pending === request) pending = null
}

/** 顶栏与刷新完成共用；轮询不会顺带拉取岗位列表。 */
export function useDataStatus() {
  return { status, loading, loadFailed, message, load }
}

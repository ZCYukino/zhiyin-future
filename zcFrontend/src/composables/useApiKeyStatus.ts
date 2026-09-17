import { ref } from 'vue'
import { services } from '@/services'
import type { ApiKeyStatus } from '@/models'

/**
 * 拉取某 provider 的 Key 状态：区分「未配置」与「读取失败」，供面板/用户中心/数据管理复用。
 *
 * loaded 是首次读取的落定标志（成功或失败都置 true）：未落定前 status 恒为 null，
 * 消费方若把它当作「未配置」会误报——所以断言「未配置」前必须先看 loaded。
 */
export function useApiKeyStatus(provider: 'deepseek' | 'dashscope') {
  const status = ref<ApiKeyStatus | null>(null)
  const loadFailed = ref(false)
  const loaded = ref(false)
  const modelName = ref('')

  async function load() {
    try {
      const cfg = await services.getApiKeyConfig()
      modelName.value = provider === 'deepseek' ? cfg.effective.llmModel : cfg.effective.embeddingModel
      status.value = provider === 'deepseek' ? cfg.deepseek : (cfg.dashscope || null)
      loadFailed.value = false
    } catch {
      status.value = null
      loadFailed.value = true
    } finally {
      loaded.value = true
    }
  }

  return { status, loadFailed, loaded, modelName, load }
}

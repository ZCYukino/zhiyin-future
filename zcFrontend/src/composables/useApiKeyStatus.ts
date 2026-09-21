import { ref } from 'vue'
import { services } from '@/services'
import type { ApiKeyStatus } from '@/models'

/** 拉取某 provider 的 Key 状态；loaded 是首次读取落定标志，断言未配置前必须先看它 */
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

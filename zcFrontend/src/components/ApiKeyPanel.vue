<template>
	<div class="apikey-panel">
		<div class="guide-area">
			<div class="guide-head">
				<span class="guide-title">{{ guide.title }}</span>
				<a class="guide-link" :href="guide.officialUrl" target="_blank" rel="noopener">
					<IconEpPromotion class="guide-link-icon" />
					{{ guide.officialLabel }}
				</a>
			</div>
			<ol class="guide-steps">
				<li v-for="(s, i) in guide.steps" :key="i" class="guide-step">
					<span class="guide-step-num">{{ i + 1 }}</span>
					<span class="guide-step-text">{{ s }}</span>
				</li>
			</ol>
			<ul class="guide-notes">
				<li v-for="(n, i) in guide.notes" :key="i" class="guide-note">{{ n }}</li>
			</ul>
		</div>

		<div class="config-area">
			<div class="status-line">
				<template v-if="status?.configured">
					<span class="status-dot ok"></span>
					<span class="status-text">
						已配置 {{ status.masked }}
						<span v-if="status.updatedAt" class="status-time"> · 更新于 {{ status.updatedAt }}</span>
					</span>
				</template>
				<template v-else-if="loadFailed">
					<span class="status-dot"></span>
					<span class="status-text">状态读取失败</span>
				</template>
				<template v-else-if="!loaded">
					<span class="status-dot pending"></span>
					<span class="status-text">状态读取中…</span>
				</template>
				<template v-else>
					<span class="status-dot"></span>
					<span class="status-text">尚未配置</span>
				</template>
				<span class="model-info">有效模型：{{ modelName || '—' }}</span>
			</div>
			<div class="config-row">
				<el-input
					v-model="inputKey"
					:type="showKey ? 'text' : 'password'"
					placeholder="粘贴以 sk- 开头的 API Key"
					class="key-input"
					clearable
					@keyup.enter="save"
				>
					<template #suffix>
						<span class="eye-toggle" @click="showKey = !showKey">
							<IconEpView v-if="!showKey" />
							<IconEpHide v-else />
						</span>
					</template>
				</el-input>
				<el-button type="primary" :loading="saving" :disabled="!inputKey.trim() || clearing" @click="save">
					<IconEpCheck /> 保存并验证
				</el-button>
				<el-button v-if="status?.configured" :loading="clearing" :disabled="saving" @click="clear">清除</el-button>
			</div>
			<p v-if="context" class="config-context">{{ context }}</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { services } from '@/services'
import { DEEPSEEK_GUIDE, DASHSCOPE_GUIDE, type ApiKeyGuide } from '@/models/apiKeyGuides'
import { useApiKeyStatus } from '@/composables/useApiKeyStatus'

const props = defineProps<{
  provider: 'deepseek' | 'dashscope'
  context?: string
}>()
const emit = defineEmits<{ (e: 'saved'): void; (e: 'cleared'): void }>()

const guide: ApiKeyGuide = props.provider === 'deepseek' ? DEEPSEEK_GUIDE : DASHSCOPE_GUIDE
const { status, loadFailed, loaded, modelName, load } = useApiKeyStatus(props.provider)
const inputKey = ref('')
const showKey = ref(false)
const saving = ref(false)
const clearing = ref(false)
const confirmingClear = ref(false)

async function save() {
  if (saving.value || clearing.value) return
  const key = inputKey.value.trim()
  if (!key) return
  saving.value = true
  try {
    await services.saveApiKey(props.provider, key)
    ElMessage.success('API Key 已保存并验证通过')
    inputKey.value = ''
    await load()
    emit('saved')
  } catch (err: any) {
    ElMessage.error(err?.message || '保存失败，请检查后端是否已启动')
  } finally {
    saving.value = false
  }
}

async function clear() {
  // 与保存互斥，避免两笔写操作并发时状态短暂错乱
  if (clearing.value || saving.value || confirmingClear.value) return
  confirmingClear.value = true
  try {
    await ElMessageBox.confirm(
      `清除后该账号将恢复为未配置状态，${props.provider === 'deepseek' ? '能力画像与学习路径' : '数据刷新中的向量化与检索'}将不可用。确定清除？`,
      '清除 API Key',
      { confirmButtonText: '确定清除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  } finally {
    confirmingClear.value = false
  }
  clearing.value = true
  try {
    await services.clearApiKey(props.provider)
    ElMessage.success('已清除')
    inputKey.value = ''
    await load()
    emit('cleared')
  } catch (err: any) {
    ElMessage.error(err?.message || '清除失败')
  } finally {
    clearing.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.apikey-panel {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.guide-area {
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 8px rgba(64, 45, 20, 0.12), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
  padding: 18px 22px;
}
.guide-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}
.guide-title {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #3b2412;
}
.guide-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border: 1px solid rgba(87, 64, 36, 0.42);
  background: #3b2412;
  color: #fbf3e2;
  font-size: 13px;
  letter-spacing: 1px;
  text-decoration: none;
  font-family: 'SimSun', 'Songti SC', serif;
  transition: background 0.2s ease, transform 0.2s ease;
}
.guide-link:hover {
  background: #2a1a0e;
  transform: translateY(-1px);
}
.guide-link-icon {
  font-size: 14px;
}
.guide-steps {
  list-style: none;
  margin: 0 0 10px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.guide-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}
.guide-step-num {
  flex: none;
  width: 20px;
  height: 20px;
  border: 1px solid rgba(87, 64, 36, 0.4);
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-family: 'Georgia', serif;
  font-size: 11px;
  color: #6f5438;
  margin-top: 1px;
}
.guide-step-text {
  font-size: 13px;
  line-height: 1.7;
  color: rgba(79, 57, 31, 0.88);
}
.guide-notes {
  list-style: none;
  margin: 0;
  padding: 10px 0 0;
  border-top: 1px dashed rgba(87, 64, 36, 0.32);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.guide-note {
  font-size: 12px;
  color: #8a6d4d;
  padding-left: 14px;
  position: relative;
}
.guide-note::before {
  content: '※';
  position: absolute;
  left: 0;
  color: #b45309;
}
.config-area {
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 8px rgba(64, 45, 20, 0.12), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
  padding: 18px 22px;
}
.status-line {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.status-dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: #c2410c;
  box-shadow: 0 0 6px rgba(194, 65, 12, 0.4);
}
.status-dot.ok {
  background: #2f6b46;
  box-shadow: 0 0 6px rgba(47, 107, 70, 0.4);
}
.status-dot.pending {
  background: rgba(87, 64, 36, 0.35);
  box-shadow: none;
}
.status-text {
  font-size: 13px;
  color: #3b2412;
  font-family: 'SimSun', 'Songti SC', serif;
}
.status-time {
  color: rgba(79, 57, 31, 0.75);
  font-size: 12px;
}
.model-info {
  margin-left: auto;
  font-size: 12px;
  color: #8a6d4d;
}
.config-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.key-input {
  flex: 1;
  min-width: 260px;
}
.key-input :deep(.el-input__wrapper) {
  background: rgba(255, 253, 243, 0.94);
  box-shadow: 0 0 0 1px rgba(87, 64, 36, 0.4) inset;
  border-radius: 3px;
}
.key-input :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px rgba(59, 36, 18, 0.8) inset;
}
.eye-toggle {
  cursor: pointer;
  display: inline-flex;
  color: rgba(87, 64, 36, 0.7);
}
.config-context {
  margin: 12px 0 0;
  font-size: 12px;
  color: #8a6d4d;
  line-height: 1.7;
}
</style>

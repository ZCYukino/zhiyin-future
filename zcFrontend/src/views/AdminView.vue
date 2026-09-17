<template>
  <div class="admin-page">
    <div class="admin-inner">
      <!-- 页头 -->
      <header class="admin-head">
        <div class="head-title">
          <span class="head-kicker">ADMIN CONSOLE</span>
          <h1 class="head-h1">数据管理</h1>
          <p class="head-sub">管理员专属 · 触发后端离线采集与富化流水线，重新生成项目数据快照</p>
        </div>
        <div class="role-badge">
          <span class="role-dot"></span>
          <span class="role-text">管理员 · {{ userStore.userInfo?.username }}</span>
        </div>
      </header>

      <!-- 说明卡 -->
      <section class="paper-card">
        <div class="card-head">
          <span class="card-index">01</span>
          <span class="card-title">刷新流程说明</span>
        </div>
        <p class="card-desc">
          点击「刷新项目数据」后，后端将在后台线程依次执行：爬虫采集原始 JD → 数据清洗 →
          LLM 结构化抽取 → 知识库组装 → 向量化索引 → 快照落盘 → 岗位画像富化。完成后全站数据即时更新。
        </p>
        <div class="stage-strip">
          <div v-for="(s, i) in STAGE_STEPS" :key="s" class="stage-item" :class="stepState(i)">
            <span class="stage-num">{{ stepState(i) === 'done' ? '✓' : i + 1 }}</span>
            <span class="stage-name">{{ s }}</span>
          </div>
        </div>
      </section>

      <!-- 刷新操作卡 -->
      <section class="paper-card">
        <div class="card-head">
          <span class="card-index">02</span>
          <span class="card-title">刷新操作</span>
        </div>
        <div class="refresh-row">
          <button
            class="refresh-btn"
            :disabled="status?.running || starting || keysMissing"
            @click="handleRefresh"
          >
            <IconEpRefresh :class="{ spinning: status?.running }" class="refresh-icon" />
            {{ status?.running ? '刷新进行中…' : starting ? '正在启动…' : '刷新项目数据' }}
          </button>
          <span class="refresh-hint">
            <template v-if="status?.running">
              全量刷新耗时较长（含 LLM 抽取与画像生成），请耐心等待。
            </template>
            <template v-else-if="keysLoading">正在读取 Key 状态…</template>
            <template v-else-if="keysLoadFailed">
              Key 状态读取失败，请检查后端服务后
              <a class="hint-link" @click="refreshKeys">重试</a>。
            </template>
            <template v-else-if="keysMissing">
              刷新前请先配置下方
              <template v-if="!dsKeys.status.value?.configured && !dcKeys.status.value?.configured">DeepSeek 与阿里云百炼 Key</template>
              <template v-else-if="!dsKeys.status.value?.configured">DeepSeek Key</template>
              <template v-else>阿里云百炼 Key</template>
              。
            </template>
            <template v-else>全量刷新耗时较长（含 LLM 抽取与画像生成），请耐心等待。</template>
          </span>
        </div>

        <!-- 进度 -->
        <div v-if="status && (status.running || status.progress > 0)" class="progress-panel">
          <div class="progress-head">
            <span class="progress-stage">当前阶段：{{ status.stage || '—' }}</span>
            <span class="progress-pct">{{ status.progress }}%</span>
          </div>
          <el-progress
            :percentage="status.progress"
            :stroke-width="10"
            :show-text="false"
            class="paper-progress"
          />
          <div v-if="status.startedAt" class="progress-meta">开始于 {{ status.startedAt }}</div>
        </div>

        <!-- 结果 -->
        <div v-if="status?.result" class="result-panel">
          <div class="result-item">
            <span class="result-val">{{ status.result.jobCount }}</span>
            <span class="result-label">岗位总数</span>
          </div>
          <div class="result-item">
            <span class="result-val">{{ status.result.profileCount }}</span>
            <span class="result-label">完整画像</span>
          </div>
          <div v-if="status.finishedAt" class="result-finished">完成于 {{ status.finishedAt }}</div>
          <div
            v-if="(status.result.failedJobs?.length || status.result.failedProfiles?.length)"
            class="failed-panel"
          >
            <p class="failed-title">
              ⚠ {{ (status.result.failedJobs?.length || 0) + (status.result.failedProfiles?.length || 0) }} 项处理失败
            </p>
            <p class="failed-list">
              {{ [...(status.result.failedJobs || []), ...(status.result.failedProfiles || [])].join('、') }}
            </p>
          </div>
        </div>

        <!-- 错误 -->
        <el-alert
          v-if="status?.error"
          :title="status.error"
          type="error"
          :closable="false"
          show-icon
          class="error-alert"
        />
      </section>

      <!-- API Key 配置 -->
      <section class="paper-card">
        <div class="card-head">
          <span class="card-index">03</span>
          <span class="card-title">DeepSeek 配置</span>
        </div>
        <ApiKeyPanel
          provider="deepseek"
          context="该 Key 属于你的管理员账号：同时用于数据刷新流水线与你本人的能力画像 / 学习路径。"
          @saved="refreshKeys"
          @cleared="refreshKeys"
        />
      </section>

      <section class="paper-card">
        <div class="card-head">
          <span class="card-index">04</span>
          <span class="card-title">阿里云百炼配置</span>
        </div>
        <ApiKeyPanel
          provider="dashscope"
          context="该 Key 用于数据刷新中的 JD 片段向量化与 RAG 检索（需在百炼开通模型服务）。"
          @saved="refreshKeys"
          @cleared="refreshKeys"
        />
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ElMessage } from 'element-plus'
import ApiKeyPanel from '@/components/ApiKeyPanel.vue'
import { services } from '@/services'
import type { RefreshStatus } from '@/services'
import { useUserStore } from '@/stores/user'
import { useApiKeyStatus } from '@/composables/useApiKeyStatus'

const userStore = useUserStore()

const status = ref<RefreshStatus | null>(null)
const starting = ref(false)
let timer: number | null = null

const dsKeys = useApiKeyStatus('deepseek')
const dcKeys = useApiKeyStatus('dashscope')
/** 首次读取未落定时两个 loaded 均为 false：此时既不能断言已配置，也不能断言未配置 */
const keysLoading = computed(() => !dsKeys.loaded.value || !dcKeys.loaded.value)
const keysLoadFailed = computed(() => dsKeys.loadFailed.value || dcKeys.loadFailed.value)
const apiKeysReady = computed(() => dsKeys.status.value?.configured === true && dcKeys.status.value?.configured === true)
/** 只在「读取成功且确实缺 Key」时才置灰：读取失败/读取中都不该冒充「未配置」 */
const keysMissing = computed(() => !keysLoading.value && !keysLoadFailed.value && !apiKeysReady.value)

async function refreshKeys() {
  await Promise.all([dsKeys.load(), dcKeys.load()])
}

// 与后端 _run_refresh 实际报告的阶段字符串一一对应（backend/app/server.py），
// 阶段条由 status.stage 实时驱动，真实反映刷新进度，不再是静态说明。
const STAGE_STEPS = [
  '初始化',
  '采集原始 JD',
  '清洗数据',
  'LLM 结构化抽取',
  '组装知识库',
  '向量化索引',
  '快照落盘',
  '岗位画像富化',
  '刷新完成',
]

const stageFlow = computed(() => {
  const s = status.value?.stage || ''
  let idx = STAGE_STEPS.indexOf(s)
  if (idx === -1 && s === '采集完成') idx = STAGE_STEPS.indexOf('岗位画像富化') // 采集完成 = 进入富化阶段
  return { idx, finished: s === '刷新完成' }
})

function stepState(i: number): 'done' | 'active' | 'pending' {
  const { idx, finished } = stageFlow.value
  if (idx < 0) return 'pending'
  if (i < idx) return 'done'
  if (i === idx) return finished ? 'done' : 'active'
  return 'pending'
}

/** skipKeys=true 用于 2s 轮询：省掉重复的 Key 回读，其余时机必须回读 */
async function fetchStatus(skipKeys = false) {
  try {
    status.value = await services.getAdminRefreshStatus()
    if (!status.value.running) stopPolling()
    // 冷加载 / 手动刷新 / 轮询结束都回读 Key 状态。若只在空闲时回读，
    // 「冷加载时后端已在刷新」的整段期间都拿不到 Key 状态，提示会误报「刷新前请先配置…」。
    if (!skipKeys) await refreshKeys()
  } catch (err: any) {
    if (err instanceof TypeError) return // 后端未就绪（网络异常），保持静默
    if (err?.status === 401 || err?.status === 403) {
      // 登录过期/无权限：停止轮询并提示，避免每 2s 静默失败
      stopPolling()
      ElMessage.warning(err?.message || '登录已过期，请重新登录')
    }
    /* 其他 HTTP 错误（如瞬时 5xx）保持静默，下一轮轮询自会重试 */
  }
}

function startPolling() {
  if (timer) return
  timer = window.setInterval(() => fetchStatus(true), 2000)
}

function stopPolling() {
  if (timer) {
    window.clearInterval(timer)
    timer = null
  }
}

async function handleRefresh() {
  if (starting.value) return // 双击防抖：避免连发两次 POST /admin/refresh
  starting.value = true
  try {
    await services.adminRefresh()
    ElMessage.success('数据刷新已启动，正在后台执行')
    await fetchStatus()
    startPolling()
  } catch (err: any) {
    ElMessage.error(err?.message || '刷新启动失败')
  } finally {
    starting.value = false
  }
}

onMounted(async () => {
  // fetchStatus 默认会一并回读 Key 状态（即使后端正在刷新），避免整段刷新期误报未配置
  await fetchStatus()
  if (status.value?.running) startPolling()
})

onUnmounted(stopPolling)
</script>

<style scoped>
.admin-page {
  min-height: calc(100vh - 56px);
  padding: 36px 24px 48px;
  background: #f4e9d6;
}
.admin-inner {
  max-width: 860px;
  margin: 0 auto;
}

/* ===== 页头 ===== */
.admin-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 20px;
  padding-bottom: 22px;
  border-bottom: 1px solid rgba(87, 64, 36, 0.34);
  margin-bottom: 24px;
}
.head-kicker {
  font-family: 'Georgia', serif;
  font-size: 11px;
  letter-spacing: 3px;
  color: rgba(87, 64, 36, 0.8);
}
.head-h1 {
  margin: 8px 0 6px;
  font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif;
  font-size: 30px;
  font-weight: 700;
  letter-spacing: 4px;
  color: #2a1a0e;
}
.head-sub {
  margin: 0;
  font-size: 13px;
  color: rgba(79, 57, 31, 0.85);
}
.role-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: #fbf3e2;
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.5);
  white-space: nowrap;
}
.role-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c2410c;
}
.role-text {
  font-size: 13px;
  letter-spacing: 1px;
  color: #3b2412;
  font-family: 'SimSun', 'Songti SC', serif;
}

/* ===== 纸卡 ===== */
.paper-card {
  position: relative;
  background: #fbf3e2;
  border: 1px solid rgba(87, 64, 36, 0.34);
  box-shadow:
    0 12px 28px rgba(64, 45, 20, 0.12),
    inset 0 0 0 1px rgba(255, 252, 240, 0.55),
    inset 0 0 0 5px rgba(251, 243, 226, 1),
    inset 0 0 0 6px rgba(87, 64, 36, 0.28);
  padding: 24px 26px;
  margin-bottom: 22px;
}
.paper-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image: repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.016) 0 1px, transparent 1px 3px);
  pointer-events: none;
}
.card-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.card-index {
  font-family: 'Georgia', serif;
  font-size: 13px;
  color: #6f5438;
  border: 1px solid rgba(87, 64, 36, 0.3);
  padding: 2px 8px;
}
.card-title {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 2px;
  color: #3b2412;
  font-family: 'SimSun', 'Songti SC', serif;
}
.card-desc {
  margin: 0 0 18px;
  font-size: 13px;
  line-height: 1.9;
  color: rgba(79, 57, 31, 0.85);
}

/* 阶段条 */
.stage-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.stage-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid rgba(87, 64, 36, 0.26);
  background: rgba(243, 230, 203, 0.45);
}
.stage-num {
  font-family: 'Georgia', serif;
  font-size: 11px;
  color: #6f5438;
}
.stage-name {
  font-size: 12px;
  letter-spacing: 0.5px;
  color: #4a2c15;
  font-family: 'SimSun', 'Songti SC', serif;
}
.stage-item.done {
  background: rgba(226, 236, 222, 0.5);
  border-color: rgba(47, 107, 70, 0.4);
}
.stage-item.done .stage-num {
  color: #2f6b46;
}
.stage-item.done .stage-name {
  color: rgba(47, 107, 70, 0.82);
}
.stage-item.active {
  background: #3b2412;
  border-color: #2a1a0e;
  box-shadow: 0 2px 8px rgba(64, 45, 20, 0.22);
}
.stage-item.active .stage-num {
  color: #fbf3e2;
  animation: stage-pulse 1.2s ease-in-out infinite;
}
.stage-item.active .stage-name {
  color: #fbf3e2;
  font-weight: 700;
}

/* ===== 刷新操作 ===== */
.refresh-row {
  display: flex;
  align-items: center;
  gap: 18px;
  flex-wrap: wrap;
}
.refresh-btn {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 26px;
  border: 1px solid rgba(87, 64, 36, 0.42);
  background: #3b2412;
  color: #fbf3e2;
  font-size: 15px;
  font-weight: 700;
  letter-spacing: 2px;
  cursor: pointer;
  font-family: 'SimSun', 'Songti SC', serif;
  transition: background 0.2s ease, transform 0.2s ease, opacity 0.2s ease;
}
.refresh-btn:hover:not(:disabled) {
  background: #2a1a0e;
  transform: translateY(-1px);
}
.refresh-btn:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.refresh-icon {
  font-size: 16px;
}
.refresh-icon.spinning {
  animation: spin 1s linear infinite;
}
.refresh-hint {
  font-size: 12px;
  color: rgba(79, 57, 31, 0.85);
}
.hint-link {
  color: #b45309;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.hint-link:hover {
  color: #7a2a22;
}

/* 进度 */
.progress-panel {
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px dashed rgba(87, 64, 36, 0.32);
}
.progress-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 10px;
}
.progress-stage {
  font-size: 14px;
  letter-spacing: 1px;
  color: #3b2412;
  font-family: 'SimSun', 'Songti SC', serif;
}
.progress-pct {
  font-family: 'Georgia', serif;
  font-size: 22px;
  color: #3b2412;
}
.progress-meta {
  margin-top: 8px;
  font-size: 12px;
  color: rgba(79, 57, 31, 0.85);
}
.paper-progress :deep(.el-progress-bar__outer) {
  background: rgba(87, 64, 36, 0.12);
}
.paper-progress :deep(.el-progress-bar__inner) {
  background: linear-gradient(90deg, #5a3d28, #3b2412);
}

/* 结果 */
.result-panel {
  display: flex;
  align-items: center;
  gap: 22px;
  flex-wrap: wrap;
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px dashed rgba(87, 64, 36, 0.32);
}
.result-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 20px;
  border: 1px solid rgba(87, 64, 36, 0.28);
  background: rgba(243, 230, 203, 0.4);
  text-align: center;
}
.result-val {
  font-family: 'Georgia', serif;
  font-size: 30px;
  line-height: 1;
  color: #3b2412;
}
.result-label {
  font-size: 12px;
  letter-spacing: 1px;
  color: rgba(79, 57, 31, 0.85);
}
.result-finished {
  font-size: 12px;
  color: rgba(79, 57, 31, 0.85);
}

.error-alert {
  margin-top: 20px;
}

.failed-panel {
  margin-top: 20px;
  padding: 14px 16px;
  border: 1px solid rgba(185, 28, 28, 0.35);
  background: rgba(252, 235, 232, 0.6);
}
.failed-title {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 700;
  color: #b91c1c;
}
.failed-list {
  margin: 0;
  font-size: 12px;
  line-height: 1.8;
  color: rgba(122, 42, 34, 0.85);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
@keyframes stage-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>

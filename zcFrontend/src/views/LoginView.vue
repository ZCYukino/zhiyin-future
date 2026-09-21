<template>
  <div class="login-page">
    <div class="careers-layer">
      <div v-for="(item, index) in floatingCareers" :key="index" class="career-drift" :style="item.driftStyle">
        <span class="career-word" :style="item.wordStyle">{{ item.name }}</span>
      </div>
    </div>

    <div class="book-shell" :class="{ visible: contentVisible }">
      <section class="login-story">
        <div class="story-paper">
          <div class="paper-head">
            <span class="paper-dot"></span><span class="paper-dot"></span><span class="paper-dot"></span>
          </div>
          <div class="paper-body">
            <p class="paper-watermark">JOB · SKILL · GRAPH</p>
            <h2 class="story-title">职引未来</h2>
            <div class="story-divider"></div>
            <p class="story-desc">
              依托多源真实招聘数据，构建「岗位 — 技能」能力图谱，动态追踪岗位能力演化，为人才培养与职业规划提供人岗匹配与差距分析支持。
            </p>

            <div class="story-metrics">
              <div class="story-metric" v-for="m in metrics" :key="m.label">
                <span class="metric-val">{{ m.value }}</span>
                <span class="metric-label">{{ m.label }}</span>
              </div>
            </div>

            <div class="story-features">
              <div class="feature-item" v-for="f in features" :key="f.index">
                <span class="feature-index">{{ f.index }}</span>
                <div>
                  <p class="feature-title">{{ f.title }}</p>
                  <p class="feature-desc">{{ f.desc }}</p>
                </div>
              </div>
            </div>

            <div class="printer-stream" :class="{ visible: streamVisible }">
              <div class="printer-head-row">
                <span class="pdot"></span><span class="pdot"></span><span class="pdot"></span>
                <span class="printer-label">SYSTEM STATUS</span>
              </div>
              <div class="printer-body">
                <p class="printer-line">{{ typedLine1 || ' ' }}</p>
                <p class="printer-line">{{ typedLine2 || ' ' }}</p>
                <p class="printer-line">{{ typedLine3 || ' ' }}</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <div class="book-spine-visual"></div>

      <section class="login-panel">
        <div class="auth-paper">
          <div class="paper-head">
            <span class="paper-dot"></span><span class="paper-dot"></span><span class="paper-dot"></span>
          </div>
          <div class="paper-body auth-body">
            <div class="auth-topline">
              <div class="folio">
                <span class="folio-label">ACCESS TERMINAL</span>
                <span class="folio-sep"></span>
                <span class="folio-no">{{ isLogin ? 'LOGIN' : 'REGISTER' }}</span>
              </div>
              <div class="mode-switch">
                <button class="mode-tab" :class="{ active: isLogin }" @click="switchMode('login')">登录</button>
                <button class="mode-tab" :class="{ active: !isLogin }" @click="switchMode('register')">注册</button>
              </div>
            </div>

            <div class="auth-content">
              <div class="auth-title-area">
                <p class="eyebrow">JOB GRAPH PLATFORM</p>
                <h1 class="main-title">{{ typedSubTitle }}<span class="blink-cursor" v-if="typingSub">|</span></h1>
              </div>
              <div class="divider" :class="{ drawn: mainDone }"></div>
              <div class="subhead">
                <p class="sub-desc">{{ isLogin ? '登录后可以浏览岗位图谱、进行人岗匹配分析，追踪岗位能力动态演化。' : '注册即解锁岗位能力图谱全貌，建立你的职业分析档案。' }}</p>
              </div>

              <div class="step-ribbon">
                <span class="ribbon-item" v-for="s in steps" :key="s">{{ s }}</span>
              </div>

              <form v-if="isLogin" class="form-area" :class="{ visible: formVisible }" @submit.prevent="handleAuth">
                <div class="field">
                  <div class="field-head">
                    <span class="field-label">{{ typedLabel1 }}<span class="blink-cursor" v-if="typingL1">|</span></span>
                    <span class="field-tag">账号</span>
                  </div>
                  <div class="field-line">
                    <input v-model="loginForm.username" type="text" class="field-input" placeholder="请输入用户名" autocomplete="username" />
                  </div>
                </div>
                <div class="field">
                  <div class="field-head">
                    <span class="field-label">{{ typedLabel2 }}<span class="blink-cursor" v-if="typingL2">|</span></span>
                    <span class="field-tag">密钥</span>
                  </div>
                  <div class="field-line">
                    <input v-model="loginForm.password" type="password" class="field-input" placeholder="请输入密码" autocomplete="current-password" @keyup.enter="handleAuth" />
                  </div>
                </div>
              </form>

              <form v-else class="form-area" :class="{ visible: formVisible }" @submit.prevent="handleAuth">
                <div class="field">
                  <div class="field-head">
                    <span class="field-label">{{ typedLabel1 }}<span class="blink-cursor" v-if="typingL1">|</span></span>
                    <span class="field-tag">新账号</span>
                  </div>
                  <div class="field-line">
                    <input v-model="registerForm.username" type="text" class="field-input" placeholder="请输入用户名" autocomplete="username" />
                  </div>
                </div>
                <div class="field">
                  <div class="field-head">
                    <span class="field-label">{{ typedLabel2 }}<span class="blink-cursor" v-if="typingL2">|</span></span>
                    <span class="field-tag">密码</span>
                  </div>
                  <div class="field-line">
                    <input v-model="registerForm.password" type="password" class="field-input" placeholder="请输入密码" autocomplete="new-password" />
                  </div>
                </div>
                <div class="field">
                  <div class="field-head">
                    <span class="field-label">{{ typedLabel3 }}<span class="blink-cursor" v-if="typingL3">|</span></span>
                    <span class="field-tag">复核</span>
                  </div>
                  <div class="field-line">
                    <input v-model="registerForm.confirmPassword" type="password" class="field-input" placeholder="再次输入密码" autocomplete="new-password" @keyup.enter="handleAuth" />
                  </div>
                </div>
              </form>

              <div class="bottom-area" :class="{ visible: bottomVisible }">
                <button class="action-line" @click="handleAuth">
                  <span class="action-dash"></span>
                  <span class="action-text">{{ isLogin ? '进入工作台' : '创建账户' }}</span>
                  <span class="action-dash"></span>
                </button>
                <button class="switch-btn" @click="switchMode(isLogin ? 'register' : 'login')">
                  {{ isLogin ? '还没有账号？立即注册' : '已有账号？立即登录' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import { careerNames } from '@/models'

const router = useRouter()
const userStore = useUserStore()

const floatingCareers = (() => {
  const items: any[] = []
  for (let r = 0; r < 4; r++) {
    for (const name of careerNames) {
      const top = Math.random() * 94 + 3
      const size = 11 + Math.random() * 10
      const opacity = 0.22 + Math.random() * 0.14
      const duration = 25 + Math.random() * 35
      const delay = -(Math.random() * duration)
      const drift = Math.random() > 0.5 ? 'drift-left' : 'drift-right'
      items.push({ name, driftStyle: { top: `${top}%`, animation: `${drift} ${duration}s ${delay}s linear infinite` }, wordStyle: { fontSize: `${size}px`, opacity } })
    }
  }
  return items
})()

const metrics = [
  { value: '30+', label: '核心岗位' },
  { value: '9', label: '岗位分类' },
  { value: '270+', label: '技能点' },
  { value: '68', label: '能力演化' },
]

const features = [
  { index: '01', title: '新岗位发现与定义', desc: '基于多源招聘数据聚合与交叉验证，智能识别萌芽期新兴岗位，生成结构化岗位画像' },
  { index: '02', title: '岗位能力动态更新', desc: '追踪岗位技能要求的时间演变，标注新增/淘汰/重要性变化，支持人工优化' },
  { index: '03', title: '全景图谱可视化', desc: '覆盖人工智能、大数据、物联网等新一代信息技术领域，技能点粒度多维关联展示' },
  { index: '04', title: '人岗匹配与差距分析', desc: '简历深度解析结合多维画像匹配，输出差距诊断报告与个性化学习路径规划' },
]

const isLogin = ref(true)
const contentVisible = ref(false)
const streamVisible = ref(false)
const formVisible = ref(false)
const bottomVisible = ref(false)

const typedLine1 = ref('')
const typedLine2 = ref('')
const typedLine3 = ref('')

const mainDone = ref(false)

const typedSubTitle = ref('')
const typingSub = ref(true)

const typedLabel1 = ref('')
const typingL1 = ref(false)
const typedLabel2 = ref('')
const typingL2 = ref(false)
const typedLabel3 = ref('')
const typingL3 = ref(false)

const loginForm = reactive({ username: '', password: '' })
const registerForm = reactive({ username: '', password: '', confirmPassword: '' })

const steps = computed(() => isLogin.value ? ['身份校验', '恢复画像', '进入平台'] : ['创建账户', '激活画像', '解锁规划'])

let seqTimers: number[] = []
let seqIntervals: number[] = []

function queue(fn: () => void, ms: number) {
  const id = window.setTimeout(() => { fn() }, ms)
  seqTimers.push(id)
}

function typeText(ref: Ref<string>, text: string, flag: Ref<boolean>, speed = 25) {
  flag.value = true
  let i = 0
  const id = window.setInterval(() => {
    if (i < text.length) { ref.value = text.slice(0, i + 1); i++ }
    else { window.clearInterval(id); flag.value = false }
  }, speed)
  seqIntervals.push(id)
}

function clearSeq() {
  seqTimers.forEach(id => window.clearTimeout(id))
  seqIntervals.forEach(id => window.clearInterval(id))
  seqTimers = []
  seqIntervals = []
}

function runSequence() {
  clearSeq()

  mainDone.value = false
  typedSubTitle.value = ''; typingSub.value = true
  typedLabel1.value = ''; typingL1.value = false
  typedLabel2.value = ''; typingL2.value = false
  typedLabel3.value = ''; typingL3.value = false
  typedLine1.value = ''; typedLine2.value = ''; typedLine3.value = ''
  streamVisible.value = false; formVisible.value = false; bottomVisible.value = false
  loginForm.password = ''; registerForm.password = ''; registerForm.confirmPassword = ''

  queue(() => { streamVisible.value = true }, 80)
  queue(() => { typeText(typedLine1, '多源数据采集引擎已就绪', ref(false), 10) }, 150)
  queue(() => { typeText(typedLine2, '岗位能力图谱构建完成', ref(false), 10) }, 400)
  queue(() => { typeText(typedLine3, '人岗匹配与差距分析待命中', ref(false), 10) }, 650)

  queue(() => { typeText(typedSubTitle, isLogin.value ? '登录' : '注册', typingSub, 30) }, 800)
  queue(() => { mainDone.value = true }, 1000)
  queue(() => { formVisible.value = true }, 1100)
  queue(() => { typeText(typedLabel1, '用户名', typingL1) }, 1150)
  queue(() => { typeText(typedLabel2, '密码', typingL2) }, 1350)
  queue(() => {
    if (!isLogin.value) typeText(typedLabel3, '确认密码', typingL3)
  }, 1550)
  queue(() => { bottomVisible.value = true }, 1750)
}

function switchMode(mode: string) {
  const newIsLogin = mode === 'login'
  if (newIsLogin === isLogin.value) return
  isLogin.value = newIsLogin
  loginForm.password = ''
  registerForm.password = ''
  registerForm.confirmPassword = ''
  nextTick(() => runSequence())
}

async function handleAuth() {
  if (isLogin.value) {
    if (!loginForm.username || !loginForm.password) { ElMessage.warning('请输入用户名和密码'); return }
    try {
      await userStore.login(loginForm.username.trim(), loginForm.password)
      ElMessage.success('登录成功')
      router.push('/')
    } catch (err: any) {
      ElMessage.error(err?.message || '登录失败，请检查后端是否已启动')
    }
  } else {
    if (!registerForm.username || !registerForm.password || !registerForm.confirmPassword) { ElMessage.warning('请填写完整信息'); return }
    if (registerForm.password !== registerForm.confirmPassword) { ElMessage.warning('两次密码不一致'); return }
    if (registerForm.password.length < 6) { ElMessage.warning('密码至少 6 位'); return }
    try {
      await userStore.register(registerForm.username.trim(), registerForm.password)
      ElMessage.success('注册成功，已自动登录')
      router.push('/')
    } catch (err: any) {
      ElMessage.error(err?.message || '注册失败，请检查后端是否已启动')
    }
  }
}

onMounted(() => {
  queue(() => { contentVisible.value = true }, 100)
  queue(() => { runSequence() }, 200)
})

onUnmounted(() => { clearSeq() })
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 32px 24px;
  background: #f4e9d6;
  position: relative;
  overflow: hidden;
}

.careers-layer { position: absolute; inset: 0; overflow: hidden; z-index: 0; }
.career-drift { position: absolute; white-space: nowrap; will-change: transform; }
.career-drift:hover { animation-play-state: paused; }
.career-word {
  display: inline-block;
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  color: #1a1a1a;
  padding: 2px 8px;
  cursor: pointer;
  transition: transform 0.35s cubic-bezier(0.23, 1, 0.32, 1), opacity 0.35s ease, background 0.35s ease;
}
.career-drift:hover .career-word {
  transform: scale(1.7);
  opacity: 0.9 !important;
  background: rgba(251, 243, 226, 0.95);
}

.book-shell {
  position: relative;
  z-index: 1;
  width: min(1280px, calc(100vw - 48px));
  min-height: 640px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 6px minmax(400px, 1fr);
  gap: 0;
  opacity: 0;
  transform: translateY(16px);
  transition: opacity 0.6s ease, transform 0.6s ease;
}
.book-shell.visible { opacity: 1; transform: translateY(0); }

.book-spine-visual {
  background: linear-gradient(90deg, rgba(87, 64, 36, 0.34), rgba(87, 64, 36, 0.10), rgba(87, 64, 36, 0.34));
  box-shadow: inset 0 0 4px rgba(42, 26, 14, 0.4);
  border-radius: 1px;
}

.story-paper, .auth-paper {
  position: relative;
  background:
    radial-gradient(ellipse 80px 60px at 0% 0%, rgba(120, 80, 30, 0.14), transparent 70%),
    radial-gradient(ellipse 80px 60px at 100% 0%, rgba(120, 80, 30, 0.12), transparent 70%),
    radial-gradient(ellipse 90px 70px at 0% 100%, rgba(120, 80, 30, 0.16), transparent 70%),
    radial-gradient(ellipse 90px 70px at 100% 100%, rgba(120, 80, 30, 0.14), transparent 70%),
    #fbf3e2;
  border: 1px solid rgba(87, 64, 36, 0.34);
  box-shadow:
    0 24px 50px rgba(64, 45, 20, 0.18),
    0 10px 20px rgba(64, 45, 20, 0.10),
    inset 0 0 0 1px rgba(255, 252, 240, 0.55),
    inset 0 0 0 5px rgba(251, 243, 226, 1),
    inset 0 0 0 6px rgba(87, 64, 36, 0.28);
  display: flex;
  flex-direction: column;
  height: 100%;
}
.story-paper::before, .auth-paper::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none;
  z-index: 0;
}

.paper-head {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 22px;
  padding: 0 18px;
  background: rgba(87, 64, 36, 0.03);
  border-bottom: 1px solid rgba(87, 64, 36, 0.06);
}
.paper-dot { width: 6px; height: 6px; border-radius: 50%; background: rgba(87, 64, 36, 0.25); }

.paper-body {
  flex: 1;
  padding: 28px 30px 26px;
  overflow-y: auto;
  position: relative;
  z-index: 1;
}
.paper-watermark {
  font-family: 'Georgia', serif;
  font-size: 9px;
  letter-spacing: 4px;
  color: rgba(26, 26, 26, 0.06);
  text-transform: uppercase;
  user-select: none;
}

.story-title {
  margin: 8px 0 0;
  font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 5px;
  color: #332113;
}
.story-divider {
  width: 54px;
  height: 2px;
  margin: 18px 0 16px;
  background: linear-gradient(90deg, rgba(84, 55, 23, 0.7), rgba(152, 119, 79, 0.18));
}
.story-desc {
  font-size: 14px;
  line-height: 1.9;
  color: rgba(79, 57, 31, 0.85);
}
.story-metrics {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin: 22px 0;
}
.story-metric {
  padding: 14px 12px;
  border: 1px solid rgba(87, 64, 36, 0.22);
  background: rgba(251, 243, 226, 0.6);
  text-align: center;
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
}
.metric-val {
  display: block;
  font-family: 'Cormorant Garamond', 'Noto Serif SC', serif;
  font-size: 26px;
  line-height: 1;
  color: #3b2412;
}
.metric-label {
  display: block;
  margin-top: 8px;
  font-size: 11px;
  letter-spacing: 1px;
  color: rgba(79, 57, 31, 0.85);
}
.story-features { display: grid; gap: 10px; margin-bottom: 22px; }
.feature-item {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  align-items: start;
  padding: 10px 14px;
  border: 1px solid rgba(87, 64, 36, 0.22);
  background: rgba(251, 243, 226, 0.6);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
}
.feature-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 32px; height: 20px;
  padding: 0 6px;
  border: 1px solid rgba(87, 64, 36, 0.32);
  font-size: 11px;
  letter-spacing: 1px;
  color: rgba(83, 57, 28, 0.85);
  background: rgba(243, 230, 203, 0.4);
}
.feature-title { margin: 0 0 4px; font-size: 13px; font-weight: 700; color: #3e2816; }
.feature-desc { margin: 0; font-size: 12px; line-height: 1.7; color: rgba(79, 57, 31, 0.85); }

.printer-stream {
  padding: 14px 16px;
  border: 1px solid rgba(87, 64, 36, 0.26);
  background: rgba(251, 243, 226, 0.65);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
  opacity: 0;
  transform: translateY(10px);
  transition: opacity 0.32s ease, transform 0.32s ease;
}
.printer-stream.visible { opacity: 1; transform: translateY(0); }
.printer-head-row { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.pdot { width: 6px; height: 6px; border-radius: 50%; background: rgba(103, 73, 37, 0.34); }
.printer-label { margin-left: 4px; font-size: 11px; letter-spacing: 1.4px; color: rgba(86, 58, 29, 0.58); }
.printer-body { display: flex; flex-direction: column; gap: 8px; }
.printer-line { margin: 0; min-height: 20px; font-size: 12px; line-height: 1.7; color: rgba(74, 53, 30, 0.76); }

.auth-body { position: relative; }
.auth-body::before {
  content: '';
  position: absolute;
  inset: 8px 0 0;
  background: repeating-linear-gradient(180deg, transparent 0 44px, rgba(106, 75, 40, 0.04) 44px 45px);
  opacity: 0.34;
  pointer-events: none;
}
.auth-content { position: relative; z-index: 1; }

.auth-topline {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-bottom: 18px;
  border-bottom: 1px dashed rgba(87, 64, 36, 0.32);
}
.folio { display: flex; align-items: center; gap: 10px; color: rgba(75, 49, 25, 0.7); font-size: 12px; letter-spacing: 1.8px; }
.folio-label, .folio-no { font-family: 'Cormorant Garamond', 'Noto Serif SC', serif; }
.folio-sep { width: 28px; height: 1px; background: rgba(86, 58, 28, 0.24); }

.mode-switch {
  display: inline-flex;
  padding: 4px; gap: 4px;
  border: 1px solid rgba(87, 64, 36, 0.34);
  background: rgba(243, 230, 203, 0.5);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.45);
}
.mode-tab {
  min-width: 64px; padding: 8px 14px;
  border: 1px solid rgba(87, 64, 36, 0.28);
  background: rgba(251, 243, 226, 0.55);
  font-size: 12px; letter-spacing: 1.2px;
  color: rgba(62, 40, 22, 0.85);
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
  font-family: 'SimSun', 'Songti SC', serif;
}
.mode-tab:hover { background: rgba(243, 230, 203, 0.7); }
.mode-tab.active {
  background: #3b2412;
  color: #fbf3e2;
  border-color: #2a1a0e;
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.18), 0 1px 2px rgba(42, 26, 14, 0.3);
}

.auth-title-area { padding-top: 10px; }
.eyebrow { margin: 0; font-family: 'Cormorant Garamond', 'Noto Serif SC', serif; font-size: 14px; letter-spacing: 2.4px; color: rgba(91, 60, 27, 0.56); }
.main-title {
  margin: 4px 0 0;
  min-height: 52px;
  font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: 8px;
  color: #3b2412;
}
.blink-cursor { margin-left: 1px; font-weight: 300; color: #5f3418; animation: blink 0.45s step-end infinite; }

.divider {
  width: 0; height: 2px;
  margin: 20px 0 18px;
  background: linear-gradient(90deg, rgba(84, 55, 23, 0.7), rgba(152, 119, 79, 0.18));
  transition: width 0.35s cubic-bezier(0.23, 1, 0.32, 1);
}
.divider.drawn { width: 100%; }

.subhead { display: flex; flex-direction: column; gap: 8px; }
.sub-desc { margin: 0; font-size: 13px; line-height: 1.8; color: rgba(74, 53, 30, 0.74); }

.step-ribbon { display: flex; flex-wrap: wrap; gap: 10px; margin: 20px 0 26px; }
.ribbon-item {
  position: relative;
  padding: 8px 14px 8px 18px;
  background: rgba(251, 243, 226, 0.6);
  border: 1px solid rgba(87, 64, 36, 0.28);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
  color: rgba(62, 40, 22, 0.92);
  font-size: 12px;
  letter-spacing: 0.6px;
  font-family: 'SimSun', 'Songti SC', serif;
}
.ribbon-item::before {
  content: '';
  position: absolute;
  left: 8px; top: 50%;
  width: 4px; height: 4px;
  border-radius: 50%;
  background: rgba(92, 60, 26, 0.42);
  transform: translateY(-50%);
}

.form-area {
  opacity: 0;
  transform: translateY(12px);
  transition: opacity 0.28s ease, transform 0.28s ease;
}
.form-area.visible { opacity: 1; transform: translateY(0); }

.field { margin-bottom: 24px; }
.field-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.field-label { min-height: 24px; font-size: 17px; letter-spacing: 2px; color: #3f2815; font-family: 'SimSun', 'Songti SC', serif; }
.field-tag { font-size: 11px; letter-spacing: 1.2px; color: rgba(98, 69, 38, 0.88); padding: 3px 10px; border: 1px solid rgba(87, 64, 36, 0.32); background: rgba(243, 230, 203, 0.45); font-family: 'SimSun', 'Songti SC', serif; }
.field-line {
  border-bottom: 1px solid rgba(87, 64, 36, 0.5);
  transition: border-color 0.2s ease;
  position: relative;
}
.field-line::before {
  content: '';
  position: absolute;
  left: 0; bottom: -1px;
  width: 0; height: 2px;
  background: linear-gradient(90deg, rgba(92, 57, 22, 0.9), rgba(184, 148, 102, 0.35));
  transition: width 0.28s cubic-bezier(0.23, 1, 0.32, 1);
}
.field-line:focus-within { border-bottom-color: rgba(92, 57, 22, 0.6); }
.field-line:focus-within::before { width: 100%; }
.field-input {
  width: 100%;
  padding: 12px 0 11px;
  border: none; outline: none;
  background: transparent;
  color: #2f1c0f;
  font-family: 'Noto Serif SC', 'Songti SC', 'STSong', serif;
  font-size: 17px;
  caret-color: #5a3317;
}
.field-input::placeholder { color: rgba(103, 74, 44, 0.42); font-size: 14px; }

.bottom-area {
  margin-top: 4px;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 16px;
  opacity: 0;
  transition: opacity 0.5s ease;
}
.bottom-area.visible { opacity: 1; }

.action-line {
  display: inline-flex;
  align-items: center;
  gap: 14px;
  padding: 12px 28px;
  border: 1px solid rgba(87, 64, 36, 0.42);
  background: rgba(243, 230, 203, 0.45);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.5);
  cursor: pointer;
  color: #311d10;
  transition: transform 0.2s ease, background 0.2s ease, color 0.2s ease, border-color 0.2s ease;
}
.action-line:hover {
  background: #3b2412;
  color: #fbf3e2;
  border-color: #2a1a0e;
  transform: translateY(-1px);
}
.action-dash { width: 36px; height: 1px; background: linear-gradient(90deg, rgba(100,68,35,0.22), rgba(69,42,17,0.72), rgba(100,68,35,0.22)); }
.action-line:hover .action-dash { background: linear-gradient(90deg, rgba(251,243,226,0.4), rgba(251,243,226,0.9), rgba(251,243,226,0.4)); }
.action-text { font-size: 16px; font-weight: 700; letter-spacing: 5px; font-family: 'SimSun', 'Songti SC', serif; }

.switch-btn {
  padding: 0 2px 2px;
  border: none;
  border-bottom: 1px dotted rgba(87, 64, 36, 0.55);
  background: none;
  cursor: pointer;
  font-size: 13px;
  color: rgba(73, 47, 24, 0.92);
  letter-spacing: 0.5px;
  font-family: 'SimSun', 'Songti SC', serif;
  transition: color 0.2s ease, border-color 0.2s ease;
}
.switch-btn:hover { color: #3b2412; border-bottom-color: #3b2412; }

@media (max-width: 1100px) {
  .book-shell { grid-template-columns: minmax(0, 1fr) 4px minmax(340px, 1fr); }
  .story-metrics { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 900px) {
  .book-shell { grid-template-columns: 1fr; gap: 20px; width: min(640px, calc(100vw - 24px)); }
  .book-spine-visual { display: none; }
  .main-title { font-size: 28px; letter-spacing: 6px; }
}
@media (max-width: 600px) {
  .login-page { padding: 18px 10px; }
  .story-metrics { grid-template-columns: repeat(2, 1fr); }
  .story-title { font-size: 22px; letter-spacing: 3px; }
  .main-title { font-size: 24px; letter-spacing: 4px; }
  .action-text { font-size: 14px; letter-spacing: 3px; }
  .action-dash { width: 36px; }
}
</style>

<style>
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
</style>

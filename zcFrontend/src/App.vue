<template>
  <el-container class="layout-container">
    <el-header v-if="userStore.isLoggedIn" class="header">
      <div class="header-inner">
        <div class="logo" @click="router.push('/')">
          <svg class="logo-mark" viewBox="0 0 44 44" aria-hidden="true">
            <defs>
              <radialGradient id="sealG" cx="50%" cy="42%" r="62%">
                <stop offset="0%" stop-color="#fbf5e6"/>
                <stop offset="70%" stop-color="#f7ecd3"/>
                <stop offset="100%" stop-color="#efe1bd"/>
              </radialGradient>
            </defs>
            <circle cx="22" cy="22" r="21.2" fill="none" stroke="rgba(59,36,18,0.45)" stroke-width="0.5"/>
            <circle cx="22" cy="22" r="20.3" fill="url(#sealG)" stroke="#3b2412" stroke-width="1.7"/>
            <circle cx="22" cy="22" r="17.5" fill="none" stroke="rgba(59,36,18,0.30)" stroke-width="0.7"/>
            <g stroke="rgba(59,36,18,0.38)" stroke-width="0.7" stroke-linecap="round">
              <line x1="41.4" y1="22" x2="40.4" y2="22"/>
              <line x1="35.72" y1="35.72" x2="35.01" y2="35.01"/>
              <line x1="22" y1="41.4" x2="22" y2="40.4"/>
              <line x1="8.28" y1="35.72" x2="8.99" y2="35.01"/>
              <line x1="2.6" y1="22" x2="3.6" y2="22"/>
              <line x1="8.28" y1="8.28" x2="8.99" y2="8.99"/>
              <line x1="22" y1="2.6" x2="22" y2="3.6"/>
              <line x1="35.72" y1="8.28" x2="35.01" y2="8.99"/>
            </g>
            <polygon points="22,22 25.20,14.28 32.5,11.5 29.72,18.80" fill="#3b2412"/>
            <polygon points="22,22 18.80,29.72 11.5,32.5 14.28,25.20" fill="#fbf3e2" stroke="#3b2412" stroke-width="1"/>
            <circle cx="22" cy="22" r="2.4" fill="#3b2412"/>
            <circle cx="22" cy="22" r="0.9" fill="#fbf3e2"/>
          </svg>
          <span class="logo-word">
            <span class="logo-cn">职引未来</span>
            <span class="logo-en">CAREER · GUIDE</span>
          </span>
        </div>
        <el-menu mode="horizontal" router :default-active="route.path" class="menu">
          <el-menu-item index="/">
            <IconEpHomeFilled class="menu-icon" />
            <span>首页</span>
          </el-menu-item>
          <el-menu-item index="/jobs">
            <IconEpBriefcase class="menu-icon" />
            <span>岗位介绍</span>
          </el-menu-item>
          <el-menu-item index="/graph">
            <IconEpShare class="menu-icon" />
            <span>岗位图谱</span>
          </el-menu-item>
          <el-menu-item index="/matching">
            <IconEpConnection class="menu-icon" />
            <span>人岗匹配</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.userInfo && userStore.userInfo.role !== 'admin'" index="/apikey">
            <IconEpKey class="menu-icon" />
            <span>API Key 管理</span>
          </el-menu-item>
          <el-menu-item v-if="userStore.userInfo?.role === 'admin'" index="/admin">
            <IconEpSetting class="menu-icon" />
            <span>数据管理</span>
          </el-menu-item>
        </el-menu>
        <div class="user-info">
          <transition name="bubble-fade">
            <div v-if="showProfileBubble" class="profile-bubble" @click="router.push('/user')">
              <span>去生成能力画像</span>
              <IconEpArrowRight class="profile-bubble-icon" />
            </div>
          </transition>
          <el-dropdown trigger="hover" @command="handleUserCommand">
            <span class="user-dropdown">
              <el-avatar :size="32" class="user-avatar">
                {{ (userStore.userInfo?.name || userStore.userInfo?.username || '?')[0] }}
              </el-avatar>
              <span class="user-name-box">
                <span class="user-entry-label">档案</span>
                <span class="user-name">{{ userStore.userInfo?.name || userStore.userInfo?.username }}</span>
              </span>
              <IconEpArrowDown class="dropdown-arrow" />
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <IconEpUser class="dropdown-item-icon" />个人信息
                </el-dropdown-item>
                <el-dropdown-item command="password">
                  <IconEpLock class="dropdown-item-icon" />修改密码
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <IconEpSwitchButton class="dropdown-item-icon" />退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </el-header>

    <el-main class="main-content" :class="{ 'no-header': !userStore.isLoggedIn }">
      <div v-if="userStore.isLoggedIn" class="global-careers-layer">
        <div v-for="(item, index) in globalFloatingCareers" :key="index" class="global-career-drift" :style="item.driftStyle">
          <span class="global-career-word" :style="item.wordStyle">{{ item.name }}</span>
        </div>
      </div>
      <router-view v-slot="{ Component, route: r }">
        <transition name="page-fade" mode="out-in">
          <div class="page-view-wrapper" :key="r.path">
            <component :is="Component" />
          </div>
        </transition>
      </router-view>
    </el-main>

    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="420px" class="paper-dialog">
      <el-form :model="passwordForm" label-position="top">
        <el-form-item label="原密码">
          <el-input v-model="passwordForm.oldPassword" type="password" placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码（至少 6 位）">
          <el-input v-model="passwordForm.newPassword" type="password" placeholder="请输入新密码" maxlength="32" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="passwordForm.confirmPassword" type="password" placeholder="请再次输入新密码" maxlength="32" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleChangePassword">确认修改</el-button>
      </template>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { useUserStore } from '@/stores/user'
import { useAnalysisStore } from '@/stores/analysis'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { services } from '@/services'
import { careerNames } from '@/models'

const userStore = useUserStore()
const analysisStore = useAnalysisStore()
const router = useRouter()
const route = useRoute()

userStore.init()

const profileChecked = ref(false)
let profileQueryStarted = false
async function ensureProfileCheck() {
  if (!userStore.isLoggedIn || profileQueryStarted) return
  profileQueryStarted = true
  try {
    await analysisStore.loadAbilityProfile()
  } finally {
    profileChecked.value = true
  }
}
watch(() => userStore.isLoggedIn, (v) => { if (v) ensureProfileCheck() }, { immediate: true })

const showProfileBubble = computed(() =>
  userStore.isLoggedIn &&
  profileChecked.value &&
  !analysisStore.abilityProfile &&
  route.path !== '/user'
)

const globalFloatingCareers = (() => {
  const items: any[] = []
  for (let r = 0; r < 2; r++) {
    for (const name of careerNames) {
      const top = Math.random() * 92 + 4
      const size = 10 + Math.random() * 8
      const opacity = 0.12 + Math.random() * 0.12
      const duration = 30 + Math.random() * 40
      const delay = -(Math.random() * duration)
      const drift = Math.random() > 0.5 ? 'drift-left' : 'drift-right'
      items.push({
        name,
        driftStyle: {
          top: `${top}%`,
          animation: `${drift} ${duration}s ${delay}s linear infinite`,
        },
        wordStyle: { fontSize: `${size}px`, opacity },
      })
    }
  }
  return items
})()

const passwordDialogVisible = ref(false)
const passwordForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })

function handleUserCommand(command: string) {
  switch (command) {
    case 'profile':
      router.push('/user')
      break
    case 'password':
      passwordForm.oldPassword = ''
      passwordForm.newPassword = ''
      passwordForm.confirmPassword = ''
      passwordDialogVisible.value = true
      break
    case 'logout':
      userStore.logout()
      router.push('/login')
      ElMessage.success('已退出登录')
      break
  }
}

async function handleChangePassword() {
  if (!passwordForm.oldPassword || !passwordForm.newPassword) {
    ElMessage.warning('请填写完整信息')
    return
  }
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.warning('两次密码不一致')
    return
  }
  if (passwordForm.newPassword.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  try {
    await services.changePassword(passwordForm.oldPassword, passwordForm.newPassword)
    ElMessage.success('密码修改成功')
    passwordDialogVisible.value = false
  } catch (err: any) {
    ElMessage.error(err?.message || '密码修改失败')
  }
}
</script>

<style>
:root {
  --pen-cursor-override: var(--pen-cursor);
}

body {
  margin: 0;
  font-family: 'Inter', 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
  background-color: #f4e9d6;
  -webkit-font-smoothing: antialiased;
}

.layout-container {
  min-height: 100vh;
}

.header {
  position: sticky;
  top: 0;
  z-index: 100;
  height: 56px !important;
  padding: 0;
  background: var(--paper-bg-solid);
  border-bottom: 1px solid rgba(87, 64, 36, 0.34);
  box-shadow:
    0 2px 6px rgba(64, 45, 20, 0.10),
    0 6px 16px rgba(64, 45, 20, 0.06),
    inset 0 -1px 0 rgba(87, 64, 36, 0.18);
}

.header::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    repeating-linear-gradient(0deg,
      transparent,
      transparent 6px,
      rgba(87, 64, 36, 0.012) 6px,
      rgba(87, 64, 36, 0.012) 7px);
  pointer-events: none;
  z-index: 1;
}

.header-inner {
  display: flex;
  align-items: center;
  height: 100%;
  max-width: 1440px;
  margin: 0 auto;
  padding: 0;
  position: relative;
  z-index: 2;
}

.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  flex-shrink: 0;
  padding: 5px 14px;
  margin-left: 24px;
  margin-right: 32px;
  background: var(--paper-bg-solid);
  border: 1px solid rgba(87, 64, 36, 0.32);
  border-radius: 2px;
  box-shadow: 0 1px 3px rgba(64, 45, 20, 0.10), inset 0 0 0 1px rgba(255, 252, 240, 0.4);
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.logo:hover {
  box-shadow: 0 3px 8px rgba(64, 45, 20, 0.14);
  border-color: rgba(87, 64, 36, 0.42);
}

.logo-mark {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  display: block;
  filter: drop-shadow(0 1px 1px rgba(42, 26, 14, 0.16));
  transition: transform 0.3s ease;
}

.logo:hover .logo-mark {
  transform: rotate(-4deg);
}

.logo-word {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}

.logo-cn {
  font-size: 16px;
  font-weight: 700;
  color: #2a1a0e;
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  letter-spacing: 3px;
  white-space: nowrap;
}

.logo-en {
  font-family: 'Georgia', serif;
  font-size: 8px;
  letter-spacing: 1.6px;
  color: rgba(87, 64, 36, 0.8);
  white-space: nowrap;
}

.menu {
  flex: 1;
  margin: 0 24px;
  border-bottom: none !important;
  background: transparent !important;
  --el-menu-active-color: #3b2412;
  --el-menu-hover-text-color: #3b2412;
  --el-menu-hover-bg-color: transparent;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: #5a5a5a;
  --el-menu-item-font-size: 14px;
  --el-menu-item-height: 56px;
  --el-menu-horizontal-submenu-height: 56px;
}

.menu :deep(.el-menu-item) {
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  font-size: 14px;
  letter-spacing: 1px;
  color: #5a5a5a !important;
  border-bottom: none !important;
  margin: 0 2px;
  padding: 0 16px !important;
  height: 40px !important;
  line-height: 40px !important;
  margin-top: 8px;
  border-radius: 2px 2px 0 0;
  border: 1px solid transparent;
  border-bottom: none;
  transition: all 0.22s ease;
}

.menu :deep(.el-menu-item:not(.is-active)) {
  background: rgba(87, 64, 36, 0.02) !important;
}

.menu :deep(.el-menu-item:hover) {
  color: #3b2412 !important;
  background: rgba(87, 64, 36, 0.05) !important;
  border-color: rgba(87, 64, 36, 0.22);
  box-shadow: 0 -1px 3px rgba(64, 45, 20, 0.06);
}

.menu :deep(.el-menu-item.is-active) {
  color: #3b2412 !important;
  font-weight: 600;
  background: #fbf3e2 !important;
  border-color: rgba(87, 64, 36, 0.28) !important;
  border-bottom: 1px solid #fbf3e2 !important;
  box-shadow:
    0 -1px 4px rgba(64, 45, 20, 0.08),
    -1px 0 3px rgba(64, 45, 20, 0.04),
    1px 0 3px rgba(64, 45, 20, 0.04) !important;
}

.menu :deep(.el-menu-item.is-active)::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 50%;
  transform: translateX(-50%);
  width: 20px;
  height: 2px;
  background: #3b2412;
}

.menu :deep(.el-menu-item:focus),
.menu :deep(.el-menu-item:active) {
  outline: none !important;
}

.menu-icon {
  font-size: 15px;
  margin-right: 3px;
  transition: transform 0.2s ease;
}

.user-info { flex-shrink: 0; }

.user-dropdown {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 2px;
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: var(--paper-bg-solid);
  box-shadow: 0 1px 4px rgba(64, 45, 20, 0.10), inset 0 0 0 1px rgba(255, 252, 240, 0.4);
  transition: background 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.user-dropdown:hover {
  background: #f3e6cb;
  border-color: rgba(87, 64, 36, 0.42);
  box-shadow: 0 3px 8px rgba(64, 45, 20, 0.14);
}

.user-avatar {
  background: none !important;
  border: 1.5px solid rgba(87, 64, 36, 0.38);
  border-radius: 2px !important;
  color: #3b2412 !important;
  font-size: 14px;
  font-weight: 700;
  font-family: 'SimSun', 'Songti SC', serif;
}

.user-name-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px;
  border: 1px solid rgba(87, 64, 36, 0.28);
  background: rgba(87, 64, 36, 0.04);
}

.user-entry-label {
  font-size: 11px;
  letter-spacing: 1px;
  color: rgba(87, 64, 36, 0.8);
  padding-right: 8px;
  border-right: 1px solid rgba(87, 64, 36, 0.12);
  font-family: 'SimSun', 'Songti SC', serif;
}

.user-name {
  font-size: 13px;
  font-weight: 500;
  color: #3b2412;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: 'SimSun', 'Songti SC', serif;
}

.dropdown-arrow {
  font-size: 12px;
  color: #6f5438;
  transition: transform 0.2s ease;
}

.user-dropdown:hover .dropdown-arrow {
  transform: rotate(180deg);
}

.dropdown-item-icon {
  margin-right: 6px;
}

.user-info {
  position: relative;
}

.profile-bubble {
  position: absolute;
  right: calc(100% + 16px);
  top: 50%;
  transform: translateY(-50%);
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 15px;
  background: #3b2412;
  border: 1px solid #1d120a;
  border-radius: 999px;
  box-shadow: 0 3px 10px rgba(42, 26, 14, 0.32), inset 0 0 0 1px rgba(255, 252, 240, 0.10);
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 1px;
  color: #fbf3e2;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s ease, box-shadow 0.2s ease;
  z-index: 101;
}

.profile-bubble::before {
  content: '';
  position: absolute;
  left: 100%;
  top: 50%;
  transform: translateY(-50%);
  border: 7px solid transparent;
  border-left-color: #1d120a;
}

.profile-bubble::after {
  content: '';
  position: absolute;
  left: 100%;
  top: 50%;
  transform: translateY(-50%);
  border: 5px solid transparent;
  border-left-color: #3b2412;
  margin-left: -2px;
}

.profile-bubble:hover {
  background: #5a3d28;
  border-color: #1d120a;
  box-shadow: 0 4px 14px rgba(42, 26, 14, 0.4), inset 0 0 0 1px rgba(255, 252, 240, 0.12);
}

.profile-bubble:hover::after {
  border-left-color: #5a3d28;
}

.profile-bubble-icon {
  font-size: 14px;
  color: #e8b268;
}

.bubble-fade-enter-active,
.bubble-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.bubble-fade-enter-from,
.bubble-fade-leave-to {
  opacity: 0;
  transform: translateY(-50%) translateX(-6px);
}

.main-content {
  padding: 0;
  min-height: calc(100vh - 56px);
  position: relative;
  overflow: hidden;
  background: #f4e9d6;
}

.main-content.no-header {
  min-height: 100vh;
  padding: 0;
  overflow: visible;
}

.page-view-wrapper {
  position: relative;
  z-index: 1;
  min-height: calc(100vh - 56px);
}

.main-content.no-header .page-view-wrapper {
  min-height: 100vh;
}

.global-careers-layer {
  position: absolute;
  inset: 0;
  overflow: hidden;
  z-index: 0;
  pointer-events: none;
}

.global-career-drift {
  position: absolute;
  white-space: nowrap;
  will-change: transform;
}

.global-career-word {
  display: inline-block;
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  color: #1a1a1a;
  padding: 2px 8px;
}

.page-fade-enter-active,
.page-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.page-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}

.page-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>

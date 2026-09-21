<template>
  <div class="user-page">
    <div class="user-content">
      <section class="page-hero">
        <div class="hero-paper">
          <h1 class="hero-title">用户中心</h1>
          <p class="hero-desc">管理个人信息与简历，查看能力画像分析结果。</p>
        </div>
      </section>

      <div class="user-layout">
        <div class="user-sidebar">
          <div class="paper-card">
            <div class="card-inner">
              <div class="card-head">
                <span class="card-eyebrow">Basic Profile</span>
                <h3 class="card-section-title">个人信息</h3>
              </div>
              <div class="card-divider"></div>

              <el-form :model="form" label-position="top" class="user-form">
                <el-form-item label="用户名" class="span-2">
                  <el-input v-model="form.username" disabled class="username-readonly" />
                </el-form-item>
                <el-form-item label="姓名">
                  <el-input v-model="form.name" placeholder="请输入姓名" />
                </el-form-item>
                <el-form-item label="邮箱">
                  <el-input v-model="form.email" placeholder="请输入邮箱" />
                </el-form-item>
                <el-form-item label="手机号">
                  <el-input v-model="form.phone" placeholder="请输入手机号" />
                </el-form-item>
                <el-form-item label="学历">
                  <el-select v-model="form.education" placeholder="请选择学历" style="width:100%">
                    <el-option label="大专" value="大专" />
                    <el-option label="本科" value="本科" />
                    <el-option label="硕士" value="硕士" />
                    <el-option label="博士" value="博士" />
                  </el-select>
                </el-form-item>
                <el-form-item label="毕业院校">
                  <el-input v-model="form.school" placeholder="请输入毕业院校" />
                </el-form-item>
                <el-form-item label="专业">
                  <el-input v-model="form.major" placeholder="请输入专业" />
                </el-form-item>
              </el-form>

              <h3 class="card-section-title" style="margin-top: 24px;">简历</h3>
              <div class="card-divider"></div>

              <div class="resume-section">
                <input ref="fileInput" type="file" accept=".pdf,.doc,.docx" style="display:none" @change="handleFileChange" />
                <div v-if="!resumeUploaded" class="upload-area" @click="triggerUpload">
                  <IconEpUpload class="upload-icon" />
                  <p class="upload-text">点击上传简历</p>
                  <p class="upload-hint">支持 PDF / Word 格式</p>
                </div>
                <div v-else class="resume-info">
                  <div class="resume-file-row">
                    <IconEpDocument class="resume-icon" />
                    <div>
                      <span class="resume-name">{{ resumeFileName }}</span>
                      <span class="resume-status-text">{{ resumeParsing ? '解析中…' : '已上传' }}</span>
                    </div>
                  </div>
                  <button class="reupload-btn" :disabled="resumeParsing" @click="triggerUpload">
                    <IconEpRefresh /> 重新上传
                  </button>
                </div>
              </div>

              <div class="form-actions">
                <el-button type="primary" @click="saveProfile" :loading="saving">
                  <IconEpCheck /> 保存信息
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <div class="user-main">
          <div class="paper-card">
            <div class="card-inner">
              <h3 class="card-section-title">能力画像</h3>
              <div class="card-divider"></div>

              <div v-if="!resumeUploaded" class="analysis-empty">
                <div class="empty-doc">
                  <span class="doc-line"></span>
                  <span class="doc-line"></span>
                  <span class="doc-line"></span>
                </div>
                <p class="empty-title">上传简历后生成能力画像</p>
                <p class="empty-desc">系统将提取简历技能与经历，由 AI 生成能力画像分析</p>
              </div>

              <div v-else class="analysis-content">
                <div class="profile-actions">
                  <el-button type="primary" :loading="profileLoading" :disabled="resumeParsing || keyMissing" @click="generateProfile">
                    <IconEpMagicStick /> {{ profile ? '重新生成画像' : '生成能力画像' }}
                  </el-button>
                </div>
                <p v-if="profileError" class="profile-error">{{ profileError }}</p>
                <p v-if="keyMissing" class="profile-error">
                  尚未配置 DeepSeek API Key，无法生成能力画像。
                  <span class="apikey-link" @click="router.push(keyConfigPath)">{{ keyConfigLabel }} →</span>
                </p>
                <p v-else-if="keyLoadFailed" class="profile-error">无法获取 Key 状态，请检查后端服务。</p>
                <p v-else-if="!keyLoaded" class="profile-hint-line">正在读取 Key 状态…</p>

                <template v-if="profile">
                  <div class="analysis-section">
                    <h4 class="analysis-title">
                      <IconEpDataAnalysis class="ana-icon" /> 综合评估
                    </h4>
                    <div class="overall-row">
                      <div class="score-ring" :style="ringStyle">
                        <div class="score-ring-inner">
                          <span class="score-num">{{ profile.overallScore }}</span>
                          <span class="score-cap">综合得分</span>
                        </div>
                      </div>
                      <div class="overall-meta">
                        <span class="level-chip">{{ profile.competitivenessLevel }}</span>
                        <p class="overall-summary">{{ profile.skillAssessment.mastered.length }} 项技能有实战佐证 · {{ profile.projectAssessment.count }} 个项目 · 经验 {{ profile.experienceAssessment.level }}</p>
                      </div>
                    </div>
                  </div>

                  <div class="analysis-section">
                    <h4 class="analysis-title">
                      <IconEpHistogram class="ana-icon" /> 技能达标度
                    </h4>
                    <div class="skill-tiers">
                      <div class="tier-block">
                        <span class="tier-label tier-mastered">达标</span>
                        <div class="tier-chips">
                          <span v-for="s in profile.skillAssessment.mastered" :key="s" class="skill-chip chip-mastered">{{ s }}</span>
                          <span v-if="!profile.skillAssessment.mastered.length" class="tier-empty">暂无</span>
                        </div>
                      </div>
                      <div class="tier-block">
                        <span class="tier-label tier-listed">已掌握</span>
                        <div class="tier-chips">
                          <span v-for="s in profile.skillAssessment.listed" :key="s" class="skill-chip chip-listed">{{ s }}</span>
                          <span v-if="!profile.skillAssessment.listed.length" class="tier-empty">暂无</span>
                        </div>
                      </div>
                      <div class="tier-block">
                        <span class="tier-label tier-missing">建议补充</span>
                        <div class="tier-chips">
                          <span v-for="s in profile.skillAssessment.missing" :key="s" class="skill-chip chip-missing">{{ s }}</span>
                          <span v-if="!profile.skillAssessment.missing.length" class="tier-empty">暂无</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div class="analysis-section">
                    <h4 class="analysis-title">
                      <IconEpSchool class="ana-icon" /> 学历与经验
                    </h4>
                    <div class="edu-exp-grid">
                      <div class="assess-card">
                        <div class="assess-head">
                          <span class="assess-name">学历</span>
                          <span class="assess-badge">{{ profile.educationAssessment.level }}</span>
                        </div>
                        <p class="assess-analysis">{{ profile.educationAssessment.analysis }}</p>
                      </div>
                      <div class="assess-card">
                        <div class="assess-head">
                          <span class="assess-name">经验</span>
                          <span class="assess-badge">{{ profile.experienceAssessment.years }}年 · {{ profile.experienceAssessment.level }}</span>
                        </div>
                        <p class="assess-analysis">{{ profile.experienceAssessment.analysis }}</p>
                      </div>
                    </div>
                  </div>

                  <div class="analysis-section">
                    <h4 class="analysis-title">
                      <IconEpFolderOpened class="ana-icon" /> 项目含金量
                    </h4>
                    <div class="assess-card">
                      <div class="assess-head">
                        <span class="assess-name">项目数量</span>
                        <span class="assess-badge">{{ profile.projectAssessment.count }} 个 · 含金量 {{ profile.projectAssessment.quality }}</span>
                      </div>
                      <div v-if="profile.projectAssessment.signals.length" class="signal-chips">
                        <span v-for="s in profile.projectAssessment.signals" :key="s" class="signal-chip">{{ s }}</span>
                      </div>
                      <p class="assess-analysis">{{ profile.projectAssessment.analysis }}</p>
                    </div>
                  </div>

                  <div class="analysis-section">
                    <h4 class="analysis-title">
                      <IconEpMedal class="ana-icon" /> 证书与获奖
                    </h4>
                    <div class="assess-card">
                      <div v-if="profile.credentialAssessment.certificates.length" class="cred-row">
                        <span class="cred-tag">证书</span>
                        <div class="tier-chips">
                          <span v-for="c in profile.credentialAssessment.certificates" :key="c" class="skill-chip chip-listed">{{ c }}</span>
                        </div>
                      </div>
                      <div v-if="profile.credentialAssessment.awards.length" class="cred-row">
                        <span class="cred-tag">获奖</span>
                        <div class="tier-chips">
                          <span v-for="a in profile.credentialAssessment.awards" :key="a" class="skill-chip chip-mastered">{{ a }}</span>
                        </div>
                      </div>
                      <p class="assess-analysis">{{ profile.credentialAssessment.analysis }}</p>
                    </div>
                  </div>

                  <div class="analysis-section">
                    <h4 class="analysis-title">
                      <IconEpTrophy class="ana-icon" /> 优势
                    </h4>
                    <div class="short-list">
                      <div v-for="s in profile.strengths" :key="s" class="mini-item">
                        <span class="dot ok"></span><span>{{ s }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="analysis-section">
                    <h4 class="analysis-title">
                      <IconEpWarningFilled class="ana-icon" /> 短板
                    </h4>
                    <div class="short-list">
                      <div v-for="s in profile.shortcomings" :key="s" class="mini-item">
                        <span class="dot warn"></span><span>{{ s }}</span>
                      </div>
                    </div>
                  </div>

                  <div class="analysis-section">
                    <h4 class="analysis-title">
                      <IconEpPromotion class="ana-icon" /> 优先提升建议
                    </h4>
                    <div class="priority-list">
                      <div v-for="(p, i) in profile.improvementPriority" :key="p" class="priority-item">
                        <span class="priority-num">{{ i + 1 }}</span><span>{{ p }}</span>
                      </div>
                    </div>
                  </div>
                </template>

                <div v-else-if="profileLoading" class="profile-hint">
                  <p>正在生成能力画像，AI 正在分析您的技能与经历，通常需要几十秒，请稍候…</p>
                </div>
                <div v-else class="profile-hint">
                  <p>上传简历后，点击「生成能力画像」由 AI 生成完整的能力评估。</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useAnalysisStore } from '@/stores/analysis'
import { ElMessage } from 'element-plus'
import { services } from '@/services'
import { useApiKeyStatus } from '@/composables/useApiKeyStatus'
import { flattenSkillTerms, skillEvidenceMap } from '@/utils/resumeParser'
import type { ResumeParseResult } from '@/utils/resumeParser'

const router = useRouter()
const userStore = useUserStore()
const analysisStore = useAnalysisStore()

const form = reactive({
  username: userStore.userInfo?.username || '',
  name: userStore.userInfo?.name || '',
  email: userStore.userInfo?.email || '',
  phone: userStore.userInfo?.phone || '',
  education: userStore.userInfo?.education || '',
  school: userStore.userInfo?.school || '',
  major: userStore.userInfo?.major || '',
})

const saving = ref(false)
const resumeUploaded = ref(false)
const resumeParsing = ref(false)
const resumeFileName = ref('')
const fileInput = ref<HTMLInputElement>()

let resumeRestored = false

const profile = computed(() => analysisStore.abilityProfile)
const profileLoading = computed(() => analysisStore.profileLoading)
const profileError = computed(() => analysisStore.profileError)

const { status: keyStatus, loadFailed: keyLoadFailed, loaded: keyLoaded, load: fetchKeyStatus } = useApiKeyStatus('deepseek')
const apiKeyReady = computed(() => keyStatus.value?.configured === true)
// 读取落定前 keyStatus 为 null，不置灰也不提示未配置
const keyMissing = computed(() => keyLoaded.value && !keyLoadFailed.value && !apiKeyReady.value)
// 管理员去数据管理页，普通用户去 API Key 管理页
const keyConfigPath = computed(() => (userStore.userInfo?.role === 'admin' ? '/admin' : '/apikey'))
const keyConfigLabel = computed(() => (userStore.userInfo?.role === 'admin' ? '前往「数据管理」配置' : '前往「API Key 管理」配置'))

// 失败提示含 API Key 时重新回读状态，不直接置空
watch(() => analysisStore.profileError, (msg) => {
  if (msg && msg.includes('API Key')) fetchKeyStatus()
})

const ringStyle = computed(() => {
  const s = profile.value?.overallScore ?? 0
  return { background: `conic-gradient(#3b2412 ${s * 3.6}deg, rgba(87,64,36,0.14) 0deg)` }
})

async function generateProfile() {
  // 基于已落库的简历解析结果生成，不读左侧表单
  await analysisStore.generateAbilityProfile()
}

function triggerUpload() {
  fileInput.value?.click()
}

async function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files && input.files[0]
  input.value = ''
  if (!file) return
  resumeParsing.value = true
  resumeFileName.value = file.name
  resumeUploaded.value = true
  try {
    const result = await services.parseResumeFile(file)
    await applyParseResult(result)
  } catch (err: any) {
    ElMessage.error(err?.message || '简历解析失败，请重新上传')
    if (userStore.userInfo?.hasResume) {
      resumeFileName.value = userStore.userInfo.resumeName || '已上传简历'
      resumeUploaded.value = true
    } else {
      resumeFileName.value = ''
      resumeUploaded.value = false
    }
  } finally {
    resumeParsing.value = false
  }
}

async function applyParseResult(result: ResumeParseResult) {
  resumeUploaded.value = true
  const cur = userStore.userInfo
  // 学历回填表单，避免保存时被空值覆盖
  const edu = form.education || result.education || cur?.education || ''
  form.education = edu
  if (result.skills.length === 0) {
    ElMessage.warning('未从简历中识别出技能，画像结果可能不完整')
  }
  const ok = await userStore.updateUserInfo({
    hasResume: true,
    resumeName: resumeFileName.value || '已上传简历',
    resumeText: result.rawText,
    resumeYears: result.years ? `${result.years}年` : '',
    userSkills: flattenSkillTerms(result.skills),
    education: edu,
    certificates: result.certificates.join('、'),
    awards: result.awards.join('、'),
    projects: JSON.stringify(result.projects),
    skillEvidence: JSON.stringify(skillEvidenceMap(result.skills)),
  })
  if (!ok) {
    throw new Error('简历保存失败，请检查后端是否已启动')
  }
  // 保存成功后才清旧画像/旧报告，失败时保留旧结果
  analysisStore.clearAbilityProfile()
  analysisStore.clearMatchReport()
  ElMessage.success('简历已解析，可直接生成能力画像')
}

function restoreResume() {
  const u = userStore.userInfo
  if (!u?.hasResume || resumeRestored) return
  resumeRestored = true
  resumeUploaded.value = true
  resumeFileName.value = u.resumeName || '已上传简历'
}

async function saveProfile() {
  saving.value = true
  try {
    const ok = await userStore.updateUserInfo({ ...form })
    if (!ok) {
      ElMessage.error('保存失败，请检查后端是否已启动')
      return
    }
    ElMessage.success('信息保存成功')
  } finally {
    saving.value = false
  }
}

watch(() => userStore.userInfo, (u) => {
  if (!u) return
  if (!form.username) form.username = u.username || ''
  if (!form.name) form.name = u.name || ''
  if (!form.email) form.email = u.email || ''
  if (!form.phone) form.phone = u.phone || ''
  if (!form.education) form.education = u.education || ''
  if (!form.school) form.school = u.school || ''
  if (!form.major) form.major = u.major || ''
  restoreResume()
})

onMounted(() => {
  restoreResume()
  analysisStore.loadAbilityProfile()
  fetchKeyStatus()
})
</script>

<style scoped>
.user-page {
  min-height: calc(100vh - 56px);
}

.user-content {
  max-width: 1240px;
  margin: 0 auto;
  padding: 28px 24px 40px;
}

.page-hero { margin-bottom: 24px; }

.hero-paper {
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
  padding: 24px 30px;
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  position: relative;
}
.hero-paper::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none; z-index: 0;
}

.hero-watermark {
  font-family: 'Georgia', serif;
  font-size: 9px;
  letter-spacing: 4px;
  color: rgba(26, 26, 26, 0.06);
  text-transform: uppercase;
  margin: 0 0 4px;
}

.hero-title {
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 6px;
  color: #2a1a0e;
  margin: 0;
}

.hero-desc {
  font-size: 14px;
  line-height: 1.8;
  color: rgba(79, 57, 31, 0.85);
  margin: 12px 0 0;
}

.user-layout {
  display: grid;
  grid-template-columns: 400px 1fr;
  gap: 24px;
  align-items: start;
}

.paper-card {
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
  position: relative;
}
.paper-card::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none; z-index: 0;
}

.card-inner { padding: 24px; }

.card-section-title {
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  font-size: 15px;
  font-weight: 700;
  color: #2a1a0e;
  letter-spacing: 2px;
  margin: 0;
}

.card-divider {
  height: 1px;
  background: linear-gradient(90deg, rgba(87, 64, 36, 0.24), rgba(87, 64, 36, 0.06), transparent);
  margin: 12px 0 16px;
}

.card-head { margin-bottom: 4px; }

.card-eyebrow {
  display: block;
  font-family: 'Georgia', serif;
  font-size: 9px;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: rgba(87, 64, 36, 0.8);
  margin-bottom: 4px;
}

.user-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  column-gap: 20px;
}

.user-form .el-form-item { margin-bottom: 14px; }
.user-form .span-2 { grid-column: 1 / -1; }

.user-form :deep(.el-form-item__label) {
  font-family: 'SimSun', 'Songti SC', serif !important;
  font-size: 12px !important;
  color: #5a3d28 !important;
  letter-spacing: 0.5px !important;
}

.user-form :deep(.el-input__wrapper) {
  background: rgba(255, 253, 243, 0.94) !important;
  border: 1px solid rgba(87, 64, 36, 0.32) !important;
  border-radius: 3px !important;
  box-shadow: inset 0 1px 2px rgba(87, 64, 36, 0.05), inset 0 0 0 1px rgba(255, 252, 240, 0.5) !important;
}

/* el-select 与输入框统一为 border 描边 */
.user-form :deep(.el-select__wrapper) {
  background: rgba(255, 253, 243, 0.94) !important;
  border: 1px solid rgba(87, 64, 36, 0.32) !important;
  box-shadow: inset 0 1px 2px rgba(87, 64, 36, 0.05) !important;
  border-radius: 3px !important;
}

.user-form :deep(.el-input__inner::placeholder),
.user-form :deep(.el-select__placeholder) {
  color: rgba(87, 64, 36, 0.62) !important;
}

.user-form :deep(.el-input__wrapper:hover),
.user-form :deep(.el-select__wrapper:hover) {
  border-color: rgba(87, 64, 36, 0.5) !important;
}

.user-form :deep(.el-input__wrapper.is-focus),
.user-form :deep(.el-select__wrapper.is-focused) {
  border-color: rgba(87, 64, 36, 0.62) !important;
}

.user-form .username-readonly :deep(.el-input__wrapper) {
  background: rgba(87, 64, 36, 0.05) !important;
  box-shadow: inset 0 0 0 1px rgba(87, 64, 36, 0.12) !important;
  cursor: default;
}
.user-form .username-readonly :deep(.el-input__inner) {
  font-family: 'Georgia', serif !important;
  letter-spacing: 1px !important;
  color: #6f5438 !important;
}

.resume-section { margin-top: 4px; }

.upload-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  border: 1px dashed rgba(87, 64, 36, 0.48);
  background: rgba(252, 247, 235, 0.85);
  cursor: pointer;
  transition: all 0.2s;
}
.upload-area:hover { border-color: rgba(87, 64, 36, 0.62); background: rgba(248, 240, 222, 0.9); }

.upload-icon { font-size: 28px; color: #5a3d28; margin-bottom: 6px; }
.upload-text { font-size: 13px; color: #3b2412; margin: 0 0 2px; font-family: 'SimSun', 'Songti SC', serif; }
.upload-hint { font-size: 11px; color: rgba(87,64,36,0.5); margin: 0; }

.resume-info {
  padding: 14px;
  border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 8px rgba(64, 45, 20, 0.1), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}

.resume-file-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.resume-icon { font-size: 22px; color: #3b2412; }

.resume-name {
  display: block;
  font-size: 13px;
  color: #3b2412;
  font-family: 'SimSun', 'Songti SC', serif;
}

.resume-status-text {
  font-size: 11px;
  color: #10b981;
}

.reupload-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: rgba(243, 230, 203, 0.4);
  font-size: 11px;
  color: #5a3d28;
  cursor: pointer;
  font-family: 'SimSun', 'Songti SC', serif;
}
.reupload-btn:hover { background: rgba(87, 64, 36, 0.08); border-color: rgba(87, 64, 36, 0.42); }
.reupload-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.form-actions {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid rgba(87, 64, 36, 0.18);
}

.analysis-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
}

.empty-doc {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
  padding: 16px;
  border: 1px solid rgba(87, 64, 36, 0.28);
}

.doc-line {
  width: 32px; height: 1px;
  background: rgba(87, 64, 36, 0.28);
}

.empty-title { font-size: 15px; color: #3b2412; margin: 0 0 6px; font-family: 'SimSun', 'Songti SC', serif; letter-spacing: 1px; }
.empty-desc { font-size: 13px; color: rgba(87,64,36,0.55); margin: 0; }

.analysis-content {
  padding-top: 4px;
}

.analysis-section {
  margin-bottom: 24px;
}

.analysis-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 14px;
  font-weight: 700;
  color: #2a1a0e;
  letter-spacing: 1px;
  margin: 0 0 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid rgba(87, 64, 36, 0.18);
}

.ana-icon { font-size: 16px; color: #3b2412; }

.profile-actions { margin-bottom: 16px; }

.profile-error {
  font-size: 12px;
  color: #c2410c;
  margin: 0 0 12px;
}

.profile-hint-line {
  font-size: 12px;
  color: rgba(87, 64, 36, 0.6);
  margin: 0 0 12px;
}

.apikey-link {
  margin-left: 6px;
  color: #b45309;
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.apikey-link:hover {
  color: #7a2a22;
}

.profile-hint {
  padding: 16px;
  border: 1px dashed rgba(87, 64, 36, 0.42);
  background: rgba(252, 247, 235, 0.85);
  font-size: 13px;
  color: rgba(87,64,36,0.65);
  line-height: 1.7;
}
.profile-hint p { margin: 0; }

.overall-row {
  display: flex;
  align-items: center;
  gap: 22px;
}

.score-ring {
  width: 118px; height: 118px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.score-ring-inner {
  width: 92px; height: 92px;
  border-radius: 50%;
  background: #fbf3e2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 0 0 1px rgba(87, 64, 36, 0.18);
}

.score-num {
  font-family: 'Georgia', serif;
  font-size: 34px;
  font-weight: 700;
  color: #3b2412;
  line-height: 1;
}

.score-cap {
  font-size: 10px;
  color: #6f5438;
  margin-top: 4px;
  letter-spacing: 1px;
}

.overall-meta {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.level-chip {
  align-self: flex-start;
  padding: 4px 12px;
  background: #3b2412;
  color: #fbf3e2;
  font-size: 12px;
  letter-spacing: 1px;
  font-family: 'SimSun', 'Songti SC', serif;
}

.overall-summary {
  font-size: 13px;
  color: rgba(87, 64, 36, 0.85);
  line-height: 1.6;
  margin: 0;
}

.mini-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 13px;
  color: #3b2412;
  line-height: 1.6;
}

.dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  margin-top: 6px;
  flex-shrink: 0;
}
.dot.ok { background: #10b981; }
.dot.warn { background: #c2410c; }

.skill-tiers {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tier-block {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.tier-label {
  flex-shrink: 0;
  width: 56px;
  padding-top: 2px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #6f5438;
  font-family: 'SimSun', 'Songti SC', serif;
}
.tier-label.tier-mastered { color: #2f6b46; }
.tier-label.tier-listed { color: #b45309; }
.tier-label.tier-missing { color: #7a2a22; }

.tier-chips {
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.tier-empty {
  font-size: 12px;
  color: rgba(87, 64, 36, 0.6);
  padding-top: 2px;
}

.skill-chip {
  display: inline-block;
  padding: 3px 10px;
  border: 1px solid;
  border-radius: 999px;
  font-size: 12px;
  line-height: 1.5;
  font-family: 'SimSun', 'Songti SC', serif;
}
.chip-mastered { color: #2f6b46; border-color: rgba(47, 107, 70, 0.5); background: rgba(47, 107, 70, 0.08); }
.chip-listed { color: #b45309; border-color: rgba(180, 83, 9, 0.5); background: rgba(180, 83, 9, 0.08); }
.chip-missing { color: #7a2a22; border-color: rgba(122, 42, 34, 0.5); background: rgba(122, 42, 34, 0.08); }

.edu-exp-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.assess-card {
  padding: 12px 14px;
  border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 8px rgba(64, 45, 20, 0.1), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}

.assess-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 8px;
  margin-bottom: 4px;
}

.assess-name {
  font-size: 13px;
  font-weight: 700;
  color: #3b2412;
  font-family: 'SimSun', 'Songti SC', serif;
}

.assess-badge {
  font-size: 12px;
  color: #5a3d28;
  font-family: 'Georgia', serif;
  letter-spacing: 0.5px;
}

.assess-analysis {
  font-size: 12px;
  color: rgba(87, 64, 36, 0.8);
  line-height: 1.6;
  margin: 6px 0 0;
}

.signal-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.signal-chip {
  padding: 2px 9px;
  font-size: 11px;
  color: #5a3d28;
  background: rgba(250, 243, 224, 0.9);
  border: 1px solid rgba(87, 64, 36, 0.32);
  border-radius: 999px;
}

.cred-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-bottom: 8px;
}

.cred-tag {
  flex-shrink: 0;
  width: 32px;
  padding-top: 3px;
  font-size: 12px;
  font-weight: 700;
  color: #3b2412;
  font-family: 'SimSun', 'Songti SC', serif;
}

.short-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.priority-list {
  display: flex;
  flex-direction: column;
  gap: 9px;
}

.priority-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  color: #3b2412;
  line-height: 1.6;
}

.priority-num {
  width: 20px; height: 20px;
  display: flex; align-items: center; justify-content: center;
  border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(250, 243, 224, 0.9);
  font-family: 'Georgia', serif;
  font-size: 11px;
  color: #5a3d28;
  flex-shrink: 0;
}

@media (max-width: 1000px) {
  .user-layout { grid-template-columns: 1fr; }
}
@media (max-width: 600px) {
  .hero-title { font-size: 22px; letter-spacing: 4px; }
  .card-inner { padding: 16px; }
  .edu-exp-grid { grid-template-columns: 1fr; }
  .overall-row { flex-direction: column; align-items: flex-start; }
  .user-form { grid-template-columns: 1fr; column-gap: 0; }
}
</style>

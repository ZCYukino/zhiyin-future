<template>
  <div class="matching-page">
    <div class="matching-content">
      <!-- 标题 -->
      <section class="page-hero">
        <div class="hero-paper">
          <h1 class="hero-title">人岗匹配分析</h1>
          <p class="hero-desc">选择目标岗位并上传简历，基于候选人技能与岗位技能矩阵逐项对照，生成可执行的差距分析报告。</p>
        </div>
      </section>

      <!-- 操作区域 -->
      <div class="matching-layout">
        <!-- 左侧：选择岗位 + 上传简历 -->
        <div class="matching-sidebar" :class="{ 'sidebar-hidden': !cardVisable }">
          <div class="paper-card">
            <div class="card-inner">
              <h3 class="card-section-title">选择岗位</h3>
              <div class="card-divider"></div>

              <el-select v-model="selectedJobId" filterable placeholder="搜索并选择目标岗位..." class="job-select"
                popper-class="job-select-popper" @change="onJobChange">
                <el-option v-for="job in allJobs" :key="job.id" :label="job.name" :value="job.id">
                  <div class="select-option">
                    <span>{{ job.name }}</span>
                    <span class="option-salary">{{ salaryRangeText(job.salaryMin, job.salaryMax) }}</span>
                  </div>
                </el-option>
              </el-select>

              <div v-if="selectedJob" class="selected-job-info">
                <h4 class="selected-job-name">{{ selectedJob.name }}</h4>
                <p class="selected-job-desc">{{ selectedJob.description }}</p>
                <div class="selected-job-skills">
                  <span class="skill-tag" v-for="s in selectedJob.skills" :key="s">{{ s }}</span>
                </div>
              </div>

              <h3 class="card-section-title" style="margin-top: 24px;">上传简历</h3>
              <div class="card-divider"></div>

              <div class="resume-upload-area">
                <!-- 双模式：文件 / 粘贴 -->
                <div class="upload-tabs">
                  <button :class="['tab-btn', uploadMode === 'file' && 'active']" @click="uploadMode = 'file'">上传文件</button>
                  <button :class="['tab-btn', uploadMode === 'text' && 'active']" @click="uploadMode = 'text'">粘贴文本</button>
                </div>

                <div v-if="uploadMode === 'file'">
                  <input ref="fileInput" type="file" accept=".pdf,.doc,.docx,.txt,.md" style="display:none"
                    @change="handleFileChange" />
                  <div v-if="!resumeUploaded" class="upload-zone" @click="triggerUpload">
                    <IconEpUpload class="upload-icon" />
                    <p class="upload-text">点击上传简历</p>
                    <p class="upload-hint">支持 PDF / Word / TXT</p>
                  </div>
                  <div v-else class="resume-status">
                    <div class="resume-file">
                      <IconEpDocument class="resume-file-icon" />
                      <div class="resume-file-info">
                        <span class="resume-file-name">{{ resumeFileName }}</span>
                        <span class="resume-file-hint" :class="parseError ? 'hint-error' : ''">{{ parseError || '简历已选择 · 开始分析时解析' }}</span>
                      </div>
                    </div>
                    <button class="resume-reupload" @click="triggerUpload">
                      <IconEpRefresh /> 重新上传
                    </button>
                  </div>
                </div>

                <div v-else class="paste-zone">
                  <textarea v-model="pasteText" class="paste-textarea" rows="5"
                    placeholder="将简历文本粘贴到此处，例如：张三，本科，3年Python经验，熟悉机器学习、大模型（LLM）与RAG…"></textarea>
                  <div class="paste-actions">
                    <button class="parse-btn" @click="parseTextInput">使用该文本</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右侧：分析报告 -->
        <div class="matching-main">
          <div class="paper-card report-card">
            <div class="card-inner">
              <div class="report-header">
                <h3 class="card-section-title">匹配分析报告</h3>
                <div class="report-actions">
                  <button v-if="hasReport" class="export-btn" @click="backToEdit">
                    <IconEpRefreshLeft class="btn-icon" /> 返回修改
                  </button>
                  <button v-if="hasReport" class="export-btn" @click="exportPDF">
                    <IconEpPrinter class="btn-icon" /> 导出 PDF
                  </button>
                </div>
              </div>
              <div class="card-divider"></div>

              <!-- 分析中：加载提示，避免长时间干等 -->
              <div v-if="analyzing" class="analyzing-panel">
                <div class="analyzing-spinner"></div>
                <p class="analyzing-title">正在生成匹配报告</p>
                <p class="analyzing-desc">AI 正逐项对照技能矩阵，通常约需 1 分钟，请稍候…</p>
              </div>

              <!-- 无报告时的引导 -->
              <div v-else-if="!hasReport" class="report-empty">
                <div class="empty-icon-doc">
                  <div class="doc-lines">
                    <span></span><span></span><span></span><span></span>
                  </div>
                </div>
                <p class="empty-title">选择岗位并上传简历后</p>
                <p class="empty-desc">系统将自动进行技能矩阵对照分析</p>
                <button class="start-btn" :disabled="analyzing" @click="runAnalysis">
                  <IconEpVideoPlay /> 开始分析
                </button>
              </div>

              <!-- 报告内容：5 段纵向流 -->
              <div v-else class="report-body">
                <!-- §1 结论横幅 — 醒目总分 -->
                <div class="verdict-hero" :class="`hero-${report.verdict}`">
                  <div class="hero-stamp">人岗匹配</div>
                  <div class="hero-score-row">
                    <div class="hero-score-block">
                      <span class="hero-score-num">{{ displayScore }}</span>
                      <span class="hero-score-suffix">/100</span>
                    </div>
                    <div class="hero-verdict-block">
                      <span class="hero-verdict-label" :class="`v-${report.verdict}`">{{ report.verdictLabel }}</span>
                      <span class="hero-job-name">{{ selectedJob?.name }}</span>
                    </div>
                  </div>
                  <div class="hero-bar">
                    <div class="hero-bar-fill" :class="`fill-${report.verdict}`" :style="{ width: displayScore + '%' }"></div>
                    <div class="hero-bar-ticks">
                      <span></span><span></span><span></span><span></span>
                    </div>
                  </div>
                  <div v-if="report.oneLineSummary" class="hero-summary">{{ report.oneLineSummary }}</div>
                </div>

                <!-- §2 技能覆盖矩阵 -->
                <div class="report-section">
                  <div class="section-title">
                    <span class="section-line"></span>
                    <span>技能覆盖矩阵</span>
                    <span class="section-line"></span>
                  </div>
                  <div class="coverage-stats">
                    <span class="cov-stat cov-mastered"><i>✓</i> 已掌握 {{ report.skillCoverage.mastered.length }}</span>
                    <span class="cov-stat cov-partial"><i>◐</i> 部分 {{ report.skillCoverage.partial.length }}</span>
                    <span class="cov-stat cov-missing"><i>✕</i> 未掌握 {{ report.skillCoverage.missing.length }}</span>
                    <span class="cov-stat cov-total">共 {{ report.skillCoverage.total }} 项</span>
                  </div>
                  <div class="coverage-grid">
                    <div class="coverage-col col-mastered">
                      <div class="col-head"><span class="col-glyph">✓</span><span>已掌握</span></div>
                      <div class="col-body">
                        <div v-for="s in report.skillCoverage.mastered" :key="'m' + s.name" class="skill-chip chip-mastered">
                          <span class="chip-glyph">✓</span>
                          <span class="chip-name">{{ s.name }}</span>
                          <span class="chip-pri" :class="'pri-' + s.priority">{{ priLabel(s.priority) }}</span>
                          <span class="chip-level">L{{ levelNum(s.level) }}</span>
                        </div>
                        <div v-if="report.skillCoverage.mastered.length === 0" class="col-empty">无</div>
                      </div>
                    </div>
                    <div class="coverage-col col-partial">
                      <div class="col-head"><span class="col-glyph">◐</span><span>部分掌握</span></div>
                      <div class="col-body">
                        <div v-for="s in report.skillCoverage.partial" :key="'p' + s.name" class="skill-chip chip-partial">
                          <span class="chip-glyph">◐</span>
                          <span class="chip-name">{{ s.name }}</span>
                          <span class="chip-pri" :class="'pri-' + s.priority">{{ priLabel(s.priority) }}</span>
                          <span class="chip-level">L{{ levelNum(s.level) }}</span>
                        </div>
                        <div v-if="report.skillCoverage.partial.length === 0" class="col-empty">无</div>
                      </div>
                    </div>
                    <div class="coverage-col col-missing">
                      <div class="col-head"><span class="col-glyph">✕</span><span>未掌握</span></div>
                      <div class="col-body">
                        <div v-for="s in report.skillCoverage.missing" :key="'g' + s.name" class="skill-chip chip-missing">
                          <span class="chip-glyph">✕</span>
                          <span class="chip-name">{{ s.name }}</span>
                          <span class="chip-pri" :class="'pri-' + s.priority">{{ priLabel(s.priority) }}</span>
                          <span class="chip-level">L{{ levelNum(s.level) }}</span>
                        </div>
                        <div v-if="report.skillCoverage.missing.length === 0" class="col-empty">无</div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- §3 硬门槛核查（岗位没给学历/经验要求时整节省略，不留空壳） -->
                <div class="report-section" v-if="report?.requirements?.length">
                  <div class="section-title">
                    <span class="section-line"></span>
                    <span>硬门槛核查</span>
                    <span class="section-line"></span>
                  </div>
                  <div class="req-list">
                    <div v-for="r in report.requirements" :key="r.label" class="req-row" :class="r.passed ? 'req-pass-row' : 'req-fail-row'">
                      <span class="req-label">{{ r.label }}</span>
                      <span class="req-user">{{ r.user }}</span>
                      <span class="req-arrow">→</span>
                      <span class="req-required">{{ r.required }}</span>
                      <span class="req-status" :class="r.passed ? 'req-pass' : 'req-fail'">{{ r.passed ? '✓ 达标' : '✕ 不足' }}</span>
                    </div>
                  </div>
                </div>

                <!-- §4 差距优先级标注 -->
                <div class="report-section">
                  <div class="section-title">
                    <span class="section-line"></span>
                    <span>差距优先级标注</span>
                    <span class="section-line"></span>
                  </div>
                  <div class="gap-strip">
                    <div class="gap-item gap-must">
                      <span class="gap-badge">必备</span>
                      <span class="gap-count">{{ report.priorityGaps.must }}</span>
                      <span class="gap-label">核心必备 · 未达标直接影响录用</span>
                    </div>
                    <div class="gap-item gap-important">
                      <span class="gap-badge">重要</span>
                      <span class="gap-count">{{ report.priorityGaps.important }}</span>
                      <span class="gap-label">重要技能 · 显著影响胜任度</span>
                    </div>
                    <div class="gap-item gap-bonus">
                      <span class="gap-badge">加分</span>
                      <span class="gap-count">{{ report.priorityGaps.bonus }}</span>
                      <span class="gap-label">加分项 · 差异化竞争优势</span>
                    </div>
                  </div>
                </div>

                <!-- §5 学习路径规划 -->
                <div class="report-section">
                  <div class="section-title">
                    <span class="section-line"></span>
                    <span>学习路径规划</span>
                    <span class="section-line"></span>
                  </div>
                  <div v-if="report.learningPath.length" class="path-timeline">
                    <div v-for="(stage, i) in report.learningPath" :key="stage.stage" class="path-stage">
                      <div class="path-stage-head">
                        <span class="path-phase">{{ i + 1 }}</span>
                        <span class="path-stage-name">{{ stage.stage }}</span>
                        <span class="path-period">{{ stage.period }}</span>
                        <span class="path-focus">{{ stage.focus }}</span>
                      </div>
                      <div class="path-steps">
                        <div v-for="st in stage.steps" :key="st.skill" class="path-step">
                          <span class="path-step-skill">{{ st.skill }}</span>
                          <span class="path-step-arrow">→</span>
                          <span class="path-step-resource">{{ st.resource }}</span>
                          <span class="path-step-milestone"><span class="ms-label">目标</span>{{ st.milestone }}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  <!-- 报告里的 llmStatus 是生成时冻结的快照，用户之后可能已配好 Key：
                       这里实时回读当前账号的 Key 状态，再决定是引导配置还是引导重新分析。 -->
                  <div v-else-if="report.llmStatus === 'no_api_key'" class="path-empty">
                    <template v-if="keyConfigured">
                      已配置 DeepSeek API Key，请点击「返回修改」后重新分析以生成学习路径。
                      <a class="path-link" @click="rerunAnalysis">重新分析</a>
                    </template>
                    <template v-else-if="keyLoadFailed">
                      Key 状态读取失败，无法确认是否已配置 DeepSeek API Key；如已配置，请直接重新分析。
                      <a class="path-link" @click="rerunAnalysis">重新分析</a>
                    </template>
                    <template v-else-if="!keyLoaded">正在读取 API Key 状态…</template>
                    <template v-else>
                      尚未配置 DeepSeek API Key，无法生成个性化学习路径。
                      <router-link v-if="isAdmin" to="/admin" class="path-link">前往「数据管理」配置</router-link>
                      <router-link v-else to="/apikey" class="path-link">前往「API Key 管理」配置</router-link>
                    </template>
                  </div>
                  <div v-else-if="report.llmStatus === 'failed'" class="path-empty">
                    学习路径生成失败，请稍后重试。
                  </div>
                  <div v-else class="path-empty">无缺口技能，无需规划学习路径</div>
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
import { useUserStore } from '@/stores/user'
import { useAnalysisStore } from '@/stores/analysis'
import { salaryRangeText } from '@/models'
import type { JobItem, SkillLevel, SkillPriority, SkillStatus } from '@/models'
import { flattenSkillTerms, skillEvidenceMap } from '@/utils/resumeParser'
import type { ResumeParseResult } from '@/utils/resumeParser'
import { services } from '@/services'
import { useApiKeyStatus } from '@/composables/useApiKeyStatus'
import { ElMessage } from 'element-plus'
import { jsPDF } from 'jspdf'
import html2canvas from 'html2canvas'

const userStore = useUserStore()
const analysisStore = useAnalysisStore()

const allJobs = ref<JobItem[]>([])
const selectedJobId = ref('')
const displayScore = ref(0)
let scoreTimer: ReturnType<typeof setInterval> | null = null

// 报告状态统一由 analysis store 持有（跨页面切换等待态/结果不丢失）。
// editing：用户「返回修改 / 改选岗位」时临时隐藏已存报告，回到选择界面。
const editing = ref(false)
const analyzing = computed(() => analysisStore.matchingLoading)
const report = computed(() => analysisStore.matchReport)
const hasReport = computed(() => !editing.value && !!report.value && selectedJobId.value === analysisStore.matchJobId)

const uploadMode = ref<'file' | 'text'>('file')
const pasteText = ref('')
const resumeUploaded = ref(false)
const resumeFileName = ref('')
const parseError = ref('')
const fileInput = ref<HTMLInputElement>()
// 已选文件暂存：上传只选文件，「开始分析」时才解析
const pendingFile = ref<File | null>(null)

const selectedJob = computed(() => {
  return allJobs.value.find(j => j.id === selectedJobId.value) || null
})

// ===== §5 学习路径空态：报告里的 llmStatus 是生成时冻结的快照 =====
// 用户可能在生成之后才配好 Key（报告不会自动重算），因此空态落在「未配置 Key」分支时，
// 必须实时回读一次当前账号的 Key 状态，区分「已配置（需重新分析）」「确实未配置」「读取失败」。
const { status: keyStatus, loadFailed: keyLoadFailed, loaded: keyLoaded, load: loadKeyStatus } = useApiKeyStatus('deepseek')
const keyConfigured = computed(() => keyStatus.value?.configured === true)
const isAdmin = computed(() => userStore.userInfo?.role === 'admin')

watch(
  () => report.value?.llmStatus,
  (s) => {
    if (s === 'no_api_key') loadKeyStatus()
  },
  { immediate: true },
)

/** 重新分析：Key 已配好但报告仍是旧快照时，重跑一次即可生成学习路径（复用 runAnalysis） */
async function rerunAnalysis() {
  if (analyzing.value) return
  // 缺少重跑前提（未选岗位 / 未上传简历）时回到修改界面，避免空转一次警告
  if (!selectedJobId.value || !resumeUploaded.value || !selectedJob.value) {
    backToEdit()
    return
  }
  await runAnalysis()
}

const cardVisable = ref(true)

function levelNum(l: SkillLevel): number {
  return l === 'junior' ? 1 : l === 'mid' ? 2 : 3
}

function priLabel(p: SkillPriority): string {
  return p === 'must' ? '必备' : p === 'important' ? '重要' : '加分'
}

function triggerUpload() {
  fileInput.value?.click()
}

/** 解析结果写入候选人画像（技能 / 学历 / 简历原文）；由「开始分析」时调用 */
/** 写入候选人画像；返回是否成功——调用方必须据此决定要不要继续分析 */
async function applyParseResult(result: ResumeParseResult): Promise<boolean> {
  const cur = userStore.userInfo
  const ok = await userStore.updateUserInfo({
    hasResume: true,
    resumeName: resumeFileName.value || '粘贴简历',
    resumeText: result.rawText,
    resumeYears: result.years ? `${result.years}年` : '',
    userSkills: flattenSkillTerms(result.skills),
    education: result.education || cur?.education || '',
    certificates: result.certificates.join('、'),
    awards: result.awards.join('、'),
    projects: JSON.stringify(result.projects),
    skillEvidence: JSON.stringify(skillEvidenceMap(result.skills)),
  })
  if (!ok) {
    ElMessage.error('简历保存失败，请检查后端是否已启动')
    return false
  }
  // 新简历使旧匹配报告 / 能力画像失效（本地 + 后端各清一份）
  await analysisStore.clearMatchReport()
  await analysisStore.clearAbilityProfile()
  return true
}

/** 上传简历：仅记录文件待解析，真正解析在「开始分析」时执行 */
function handleFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  if (input.files && input.files[0]) {
    pendingFile.value = input.files[0]
    resumeFileName.value = pendingFile.value.name
    resumeUploaded.value = true
    parseError.value = ''
    input.value = ''
  }
}

/** 粘贴文本：仅记录文本待解析，真正解析在「开始分析」时执行 */
function parseTextInput() {
  const text = pasteText.value.trim()
  if (!text) {
    ElMessage.warning('请先粘贴简历文本')
    return
  }
  pendingFile.value = null
  resumeFileName.value = '粘贴文本'
  resumeUploaded.value = true
  parseError.value = ''
}

function onJobChange() {
  editing.value = true
  displayScore.value = 0
}

/** 返回修改：回到选择岗位 / 上传简历界面，用户可重新选择后再分析 */
function backToEdit() {
  editing.value = true
  cardVisable.value = true
  displayScore.value = 0
}

async function runAnalysis() {
  if (analyzing.value) return
  let user = userStore.userInfo
  if (!user) {
    ElMessage.warning('请先登录后再进行人岗匹配分析')
    return
  }
  if (!selectedJobId.value) {
    ElMessage.warning('请先选择目标岗位')
    return
  }
  if (!resumeUploaded.value) {
    ElMessage.warning('请先上传简历')
    return
  }
  if (!selectedJob.value) {
    ElMessage.warning('未找到所选岗位')
    return
  }

  // 延迟解析：上传/粘贴只选简历，「开始分析」时才解析并写入画像
  if (pendingFile.value || (uploadMode.value === 'text' && pasteText.value.trim())) {
    let result: ResumeParseResult
    try {
      result = pendingFile.value
        ? await services.parseResumeFile(pendingFile.value)
        : services.parseResumeText(pasteText.value.trim())
    } catch (err: any) {
      parseError.value = err?.message || '简历解析失败'
      ElMessage.error(parseError.value)
      return
    }
    // 保存失败必须中止：后端库里还是旧简历，继续分析会拿内存里的新技能出报告，
    // 与用户中心 / 能力画像（读库）对不上
    if (!(await applyParseResult(result))) return
    user = userStore.userInfo ?? user
    pendingFile.value = null
  }

  // 触发左侧栏收缩动画 + 进入加载态
  cardVisable.value = false
  editing.value = false

  // 由 analysis store 计算匹配报告（后端持久化一份、覆盖旧报告；跨页面切换等待态不丢失）
  await analysisStore.generateMatchReport(selectedJob.value, user)
  if (analysisStore.matchingError) {
    cardVisable.value = true
    ElMessage.error(analysisStore.matchingError)
    return
  }
  const r = report.value
  if (!r) {
    cardVisable.value = true
    return
  }

  // 分数数字滚动动画
  if (scoreTimer) clearInterval(scoreTimer)
  const target = r.score
  let current = 0
  scoreTimer = setInterval(() => {
    current += 2
    if (current >= target) {
      displayScore.value = target
      clearInterval(scoreTimer!)
      scoreTimer = null
    } else {
      displayScore.value = current
    }
  }, 30)
}


// PDF 导出：构建「打印专用文档」而非截图屏幕上的报告 DOM（暖纸商务风）。
// 流程：用 report 数据拼一份 A4 打印调校的文档 HTML（品牌抬头 + 编号章节 + 打印样式），
// 渲染到隐藏容器 → html2canvas 栅格化完整长图 → 逐页合成 A4 画布（内容切片 + 页脚页码）→ jsPDF。
let pdfExporting = false
async function exportPDF() {
  if (pdfExporting) return
  if (!report.value || !selectedJob.value) return

  pdfExporting = true
  const loading = ElMessage({ type: 'info', message: '正在生成 PDF，请稍候…', duration: 0 })

  const r = report.value
  const job = selectedJob.value
  const name = userStore.userInfo?.name || userStore.userInfo?.username || '用户'
  const date = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric' })

  const verdictColor: Record<string, string> = {
    strong: '#15803d',
    fair: '#3b2412',
    partial: '#b45309',
    weak: '#b91c1c',
  }
  const vc = verdictColor[r.verdict] || '#3b2412'

  const esc = (s: unknown) => String(s ?? '')
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  const coverage = r.skillCoverage || { total: 0, mastered: [], partial: [], missing: [] }
  const requirements = r.requirements || []
  const gaps = r.priorityGaps || { must: 0, important: 0, bonus: 0 }
  const learningPath = r.learningPath || []

  // §1 综合结论：单卡横幅，去掉悬空超宽进度条与死空间
  const section1 = `
    <div class="section">
      <div class="section-head"><span class="sec-num">01</span><span class="sec-title">综合匹配结论</span></div>
      <div class="verdict">
        <div class="verdict-main">
          <div class="verdict-score" style="color:${vc}">${r.score}<span class="verdict-denom">/100</span></div>
          <div class="verdict-info">
            <span class="verdict-label" style="color:${vc};border-color:${vc}">${esc(r.verdictLabel)}</span>
            <span class="verdict-job">${esc(job.name)}</span>
          </div>
        </div>
        <div class="verdict-bar"><div class="verdict-bar-fill" style="width:${r.score}%;background:${vc}"></div></div>
        ${r.oneLineSummary ? `<p class="verdict-summary">${esc(r.oneLineSummary)}</p>` : ''}
      </div>
    </div>`

  // §2 技能覆盖矩阵：流式标签（已/部分/未掌握分组横排换行），消灭单列空柜
  const chip = (s: SkillStatus, kind: 'm' | 'p' | 'g') => {
    const glyph = kind === 'm' ? '✓' : kind === 'p' ? '◐' : '✕'
    return `<span class="chip chip-${kind}"><span class="chip-glyph">${glyph}</span><span class="chip-name">${esc(s.name)}</span><span class="chip-pri pri-${s.priority}">${priLabel(s.priority)}</span><span class="chip-level">L${levelNum(s.level)}</span></span>`
  }
  const covGroup = (title: string, glyph: string, kind: 'm' | 'p' | 'g', items: SkillStatus[]) => `
    <div class="cov-group">
      <div class="cov-group-head"><span class="cov-glyph g-${kind}">${glyph}</span><span class="cov-group-name">${title}</span><span class="cov-group-count">${items.length}</span></div>
      <div class="cov-flow">${items.length ? items.map(s => chip(s, kind)).join('') : '<span class="empty">无</span>'}</div>
    </div>`
  const section2 = `
    <div class="section">
      <div class="section-head"><span class="sec-num">02</span><span class="sec-title">技能覆盖矩阵</span></div>
      <div class="cov-stats">
        <span class="cov-stat"><i class="s-mastered">✓</i> 已掌握 ${coverage.mastered.length}</span>
        <span class="cov-stat"><i class="s-partial">◐</i> 部分掌握 ${coverage.partial.length}</span>
        <span class="cov-stat"><i class="s-missing">✕</i> 未掌握 ${coverage.missing.length}</span>
        <span class="cov-stat">共 ${coverage.total} 项</span>
      </div>
      <div class="cov-body">
        ${covGroup('已掌握', '✓', 'm', coverage.mastered)}
        ${covGroup('部分掌握', '◐', 'p', coverage.partial)}
        ${covGroup('未掌握', '✕', 'g', coverage.missing)}
      </div>
    </div>`

  // §3 硬门槛核查（岗位没给要求时整节省略，不留空壳）
  const section3 = requirements.length
    ? `
    <div class="section">
      <div class="section-head"><span class="sec-num">03</span><span class="sec-title">硬门槛核查</span></div>
      <div class="req-list">
        ${requirements.map(req => `
          <div class="req-row ${req.passed ? 'req-pass' : 'req-fail'}">
            <span class="req-label">${esc(req.label)}</span>
            <span class="req-user">${esc(req.user)}</span>
            <span class="req-arrow">→</span>
            <span class="req-required">${esc(req.required)}</span>
            <span class="req-status">${req.passed ? '✓ 达标' : '✕ 不足'}</span>
          </div>`).join('')}
      </div>
    </div>`
    : ''

  // §4 差距优先级标注
  const gapItem = (label: string, count: number, desc: string, cls: string) => `
    <div class="gap-item ${cls}">
      <span class="gap-badge">${label}</span>
      <span class="gap-count">${count}</span>
      <span class="gap-label">${desc}</span>
    </div>`
  const section4 = `
    <div class="section">
      <div class="section-head"><span class="sec-num">04</span><span class="sec-title">差距优先级标注</span></div>
      <div class="gap-strip">
        ${gapItem('必备', gaps.must, '核心必备 · 未达标直接影响录用', 'gap-must')}
        ${gapItem('重要', gaps.important, '重要技能 · 显著影响胜任度', 'gap-important')}
        ${gapItem('加分', gaps.bonus, '加分项 · 差异化竞争优势', 'gap-bonus')}
      </div>
    </div>`

  // §5 学习路径规划
  const section5 = learningPath.length ? `
    <div class="section">
      <div class="section-head"><span class="sec-num">05</span><span class="sec-title">学习路径规划</span></div>
      <div class="path-list">
        ${learningPath.map((stage, i) => `
          <div class="path-stage">
            <div class="path-head">
              <span class="path-phase">${i + 1}</span>
              <span class="path-name">${esc(stage.stage)}</span>
              <span class="path-focus">${esc(stage.focus)}</span>
              <span class="path-period">${esc(stage.period)}</span>
            </div>
            <div class="path-steps">
              ${stage.steps.map(st => `
                <div class="path-step">
                  <div class="path-step-main"><span class="path-skill">${esc(st.skill)}</span><span class="path-arrow">→</span><span class="path-resource">${esc(st.resource)}</span></div>
                  <div class="path-step-goal"><span class="path-goal-badge">目标</span><span class="path-milestone">${esc(st.milestone)}</span></div>
                </div>`).join('')}
            </div>
          </div>`).join('')}
      </div>
    </div>` : `
    <div class="section">
      <div class="section-head"><span class="sec-num">05</span><span class="sec-title">学习路径规划</span></div>
      <div class="empty-block">${r.llmStatus === 'no_api_key'
        ? '尚未配置 DeepSeek API Key，无法生成个性化学习路径'
        : r.llmStatus === 'failed'
          ? '学习路径生成失败，请稍后重试'
          : '无缺口技能，无需规划学习路径'}</div>
    </div>`

  const doc = `
<style>
*{box-sizing:border-box;margin:0;padding:0}
.report-doc{width:800px;padding:24px 28px;font-family:'SimSun','Songti SC','STSong','Noto Serif SC',serif;font-size:14px;color:#2a1a0e;background:#faf6ec;line-height:1.6}
/* —— 页眉抬头带 —— */
.doc-head{padding-bottom:12px;margin-bottom:18px;border-bottom:2px solid #3b2412}
.doc-topline{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px}
.doc-brand{font-family:'SimSun','Songti SC',serif;color:#2a1a0e;font-size:18px;font-weight:700;letter-spacing:2px}
.doc-brand em{font-style:normal;font-family:Georgia,serif;font-size:11px;letter-spacing:3px;color:#8a7560;margin-left:10px}
.doc-typename{font-size:12px;color:#8a7560;letter-spacing:2px;font-family:Georgia,'SimSun',serif}
.doc-title{font-size:22px;font-weight:700;color:#2a1a0e;letter-spacing:2px;margin-bottom:10px}
.doc-meta{display:flex;flex-wrap:wrap;gap:8px 24px;font-size:13px;color:#5a3d28}
.meta-item{display:flex;align-items:center;gap:8px}
.meta-k{font-size:11px;color:#8a7560;letter-spacing:2px}
.meta-v{color:#2a1a0e}
.meta-v b{font-family:Georgia,serif;font-size:18px}
.meta-v .meta-sub{color:#5a3d28;font-size:12px}
/* —— 章节 —— */
.section{margin-bottom:20px}
.section-head{display:flex;align-items:center;gap:12px;margin-bottom:12px;padding-bottom:7px;border-bottom:2px solid rgba(87,64,36,0.28)}
.sec-num{font-family:Georgia,serif;font-size:24px;font-weight:700;color:rgba(87,64,36,0.30)}
.sec-title{font-size:16px;font-weight:700;color:#3b2412;letter-spacing:1px}
/* §1 */
.verdict{border:1px solid rgba(87,64,36,0.32);background:#fbf3e2;padding:18px 20px;border-radius:2px}
.verdict-main{display:flex;align-items:center;gap:20px;margin-bottom:10px}
.verdict-score{font-family:Georgia,serif;font-size:58px;font-weight:700;line-height:1}
.verdict-denom{font-size:16px;color:#8a7560;font-weight:400;margin-left:4px}
.verdict-info{display:flex;flex-direction:column;gap:6px}
.verdict-label{font-size:12px;font-weight:700;letter-spacing:2px;padding:2px 12px;border:1px solid currentColor;align-self:flex-start;background:rgba(251,243,226,0.6)}
.verdict-job{font-size:14px;color:#3b2412;font-weight:600}
.verdict-bar{height:8px;background:rgba(87,64,36,0.12);margin-bottom:10px;overflow:hidden}
.verdict-bar-fill{height:100%}
.verdict-summary{font-size:13px;color:#5a3d28;line-height:1.65}
/* §2 流式标签 */
.cov-stats{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.cov-stat{font-size:12px;color:#5a3d28;padding:3px 12px;border:1px solid rgba(87,64,36,0.3);background:#fbf3e2;border-radius:1px}
.cov-stat i{font-style:normal;font-weight:700}
.s-mastered{color:#15803d}.s-partial{color:#b45309}.s-missing{color:#b91c1c}
.cov-body{padding:2px 0}
.cov-group{margin-bottom:12px}
.cov-group:last-child{margin-bottom:0}
.cov-group-head{display:flex;align-items:center;gap:8px;margin-bottom:8px;font-size:13px;font-weight:700;color:#3b2412}
.cov-glyph{font-weight:700;font-size:13px}
.g-mastered{color:#15803d}.g-partial{color:#b45309}.g-missing{color:#b91c1c}
.cov-group-name{letter-spacing:1px}
.cov-group-count{font-family:Georgia,serif;font-size:12px;color:#5a3d28;background:rgba(87,64,36,0.08);padding:1px 9px;border-radius:8px}
.cov-flow{display:flex;flex-wrap:wrap;gap:8px}
.chip{display:inline-flex;align-items:center;gap:6px;font-size:12px;padding:5px 9px;border:1px solid;border-radius:3px}
.chip-glyph{font-weight:700}
.chip-name{color:#2a1a0e}
.chip-pri{font-size:10px;padding:0 4px;border:1px solid currentColor;border-radius:1px}
.chip-level{font-family:Georgia,serif;font-size:10px;padding:0 4px;border:1px solid rgba(87,64,36,0.32);color:#5a3d28}
.chip-m{border-color:rgba(21,128,61,0.4);background:rgba(21,128,61,0.08)}
.chip-m .chip-glyph{color:#15803d}
.chip-p{border-color:rgba(180,83,9,0.4);background:rgba(180,83,9,0.08)}
.chip-p .chip-glyph{color:#b45309}
.chip-g{border-color:rgba(185,28,28,0.4);background:rgba(185,28,28,0.08)}
.chip-g .chip-glyph{color:#b91c1c}
.pri-must{color:#7a2a22}.pri-important{color:#b45309}.pri-bonus{color:#8a7560}
.empty{font-size:12px;color:rgba(87,64,36,0.45);padding:4px 0}
/* §3 硬门槛 */
.req-list{display:flex;flex-direction:column;gap:8px}
.req-row{display:flex;align-items:center;gap:10px;padding:9px 12px;border:1px solid rgba(87,64,36,0.3);font-size:13px}
.req-pass{background:linear-gradient(90deg,rgba(21,128,61,0.12),rgba(21,128,61,0.04));border-color:rgba(21,128,61,0.4)}
.req-fail{background:linear-gradient(90deg,rgba(185,28,28,0.12),rgba(185,28,28,0.04));border-color:rgba(185,28,28,0.4)}
.req-label{font-weight:700;color:#2a1a0e;min-width:32px;padding:2px 8px;background:rgba(251,243,226,0.8);border:1px solid rgba(87,64,36,0.32);letter-spacing:1px;text-align:center}
.req-user{color:#2a1a0e;padding:2px 8px;background:rgba(255,252,240,0.6);border:1px solid rgba(87,64,36,0.22)}
.req-arrow{color:#8a7560;font-family:Georgia,serif}
.req-required{color:#3b2412;flex:1;padding:2px 8px;background:rgba(243,230,203,0.4);border:1px solid rgba(87,64,36,0.2)}
.req-status{font-weight:700;font-family:Georgia,serif;padding:3px 10px;border:1px solid currentColor;letter-spacing:1px}
.req-pass .req-status{color:#15803d;background:rgba(21,128,61,0.12)}
.req-fail .req-status{color:#b91c1c;background:rgba(185,28,28,0.12)}
/* §4 差距 */
.gap-strip{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.gap-item{display:flex;flex-direction:column;align-items:center;gap:6px;padding:16px 10px;border:1px solid rgba(87,64,36,0.4);background:#fbf3e2}
.gap-badge{font-size:11px;font-weight:700;letter-spacing:2px;padding:2px 10px;border:1px solid currentColor;background:rgba(251,243,226,0.7)}
.gap-must .gap-badge{color:#7a2a22}
.gap-important .gap-badge{color:#b45309}
.gap-bonus .gap-badge{color:#8a7560}
.gap-count{font-family:Georgia,serif;font-size:34px;font-weight:700;line-height:1}
.gap-must .gap-count{color:#7a2a22}
.gap-important .gap-count{color:#b45309}
.gap-bonus .gap-count{color:#5a3d28}
.gap-label{font-size:11px;color:#5a3d28;text-align:center}
/* §5 学习路径 */
.path-list{display:flex;flex-direction:column;gap:12px}
.path-stage{border:1px solid rgba(87,64,36,0.4);background:#fbf3e2}
.path-head{display:flex;align-items:center;gap:10px;padding:10px 14px;border-bottom:1px dashed rgba(87,64,36,0.22)}
.path-phase{font-family:Georgia,serif;font-size:13px;font-weight:700;color:#fbf3e2;background:#3b2412;width:22px;height:22px;display:flex;align-items:center;justify-content:center}
.path-name{font-size:13px;font-weight:700;color:#2a1a0e;letter-spacing:1px}
.path-focus{font-size:12px;color:#5a3d28}
.path-period{font-size:12px;color:#8a7560;margin-left:auto;font-family:Georgia,serif}
.path-steps{display:flex;flex-direction:column;padding:12px 14px;gap:8px}
.path-step{padding:8px 10px;background:rgba(255,252,240,0.65);border:1px solid rgba(87,64,36,0.18);border-left:3px solid #3b2412}
.path-step-main{display:flex;align-items:center;gap:8px;margin-bottom:4px}
.path-skill{font-weight:700;color:#2a1a0e}
.path-arrow{color:#8a7560;font-family:Georgia,serif}
.path-resource{color:#5a3d28;flex:1;font-size:12px}
.path-step-goal{display:flex;align-items:flex-start;gap:8px;padding-left:2px}
.path-goal-badge{font-size:10px;font-weight:700;color:#fbf3e2;background:#5a3d28;padding:1px 6px;border-radius:3px;letter-spacing:1px;flex-shrink:0;margin-top:1px}
.path-milestone{font-size:12px;color:#3b2412;line-height:1.5}
.empty-block{font-size:13px;color:rgba(87,64,36,0.55);padding:18px;border:1px dashed rgba(87,64,36,0.3);background:#fbf3e2;text-align:center}
</style>
<div class="report-doc">
  <div class="doc-head">
    <div class="doc-topline">
      <span class="doc-brand">职引未来<em>CAREER · GUIDE</em></span>
      <span class="doc-typename">人岗匹配 · 差距分析</span>
    </div>
    <div class="doc-title">人岗匹配分析报告</div>
    <div class="doc-meta">
      <div class="meta-item"><span class="meta-k">目标岗位</span><span class="meta-v">${esc(job.name)}</span></div>
      <div class="meta-item"><span class="meta-k">综合匹配度</span><span class="meta-v"><b style="color:${vc}">${r.score}</b> 分<span class="meta-sub">· ${esc(r.verdictLabel)}</span></span></div>
      <div class="meta-item"><span class="meta-k">生成日期</span><span class="meta-v">${esc(date)}</span></div>
    </div>
  </div>
  ${section1}
  ${section2}
  ${section3}
  ${section4}
  ${section5}
</div>`

  const container = document.createElement('div')
  container.style.cssText = 'position:absolute;left:-9999px;top:0;width:800px;z-index:-1;'
  container.innerHTML = doc
  document.body.appendChild(container)

  const pageWidth = 210
  const pageHeight = 297
  const margin = 10
  const printWidthMm = pageWidth - margin * 2
  const printHeightMm = pageHeight - margin * 2

  try {
    // 智能分页：避免章节标题孤悬页尾（栅格化无法用 CSS 分页，故在 DOM 里量算后插入撑高）。
    const scale = 2
    const domPxPerMm = 800 / printWidthMm          // 800px 容器在 1x DOM 下的 px/mm
    const pageContentDomPx = printHeightMm * domPxPerMm
    const head = container.querySelector('.report-doc > .doc-head') as HTMLElement | null
    let cursor = head ? head.offsetHeight : 0
    const secs = Array.from(container.querySelectorAll<HTMLElement>('.report-doc > .section'))
    for (const sec of secs) {
      const sh = sec.offsetHeight
      if (cursor > 0 && cursor + sh > pageContentDomPx && sh < pageContentDomPx) {
        const spacer = document.createElement('div')
        spacer.style.cssText = `width:100%;height:${Math.round(pageContentDomPx - cursor)}px;`
        sec.parentElement!.insertBefore(spacer, sec)
        cursor = sh
      } else {
        cursor += sh
      }
    }

    const canvas = await html2canvas(container, {
      scale,
      useCORS: true,
      allowTaint: true,
      backgroundColor: '#faf6ec',
      logging: false,
    })

    const pxPerMm = canvas.width / printWidthMm
    const contentHeightPx = canvas.height
    const totalContentHeightMm = contentHeightPx / pxPerMm
    const totalPages = Math.max(1, Math.ceil(totalContentHeightMm / printHeightMm))

    const pageWpx = Math.round(pageWidth * pxPerMm)
    const pageHpx = Math.round(pageHeight * pxPerMm)
    const footRuleY = pageHpx - Math.round(10 * pxPerMm)      // 内容底端的分隔线
    const footTextY = pageHpx - Math.round(6 * pxPerMm)       // 页脚文字基线
    const footFont = Math.round(2.6 * pxPerMm)                // ≈ 7.4pt
    const FOOTER = '职引未来 · CAREER GUIDE'

    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })

    for (let i = 0; i < totalPages; i++) {
      if (i > 0) pdf.addPage()
      const srcY = Math.round(i * printHeightMm * pxPerMm)
      const srcH = Math.min(Math.round(printHeightMm * pxPerMm), contentHeightPx - srcY)

      // 逐页合成 A4 画布：底色 + 内容切片 + 页脚（品牌 + 页码）
      const pageCanvas = document.createElement('canvas')
      pageCanvas.width = pageWpx
      pageCanvas.height = pageHpx
      const ctx = pageCanvas.getContext('2d')!
      ctx.fillStyle = '#faf6ec'
      ctx.fillRect(0, 0, pageWpx, pageHpx)
      ctx.drawImage(canvas, 0, srcY, canvas.width, srcH,
        margin * pxPerMm, margin * pxPerMm, printWidthMm * pxPerMm, srcH)

      // 页脚分隔细线
      ctx.strokeStyle = 'rgba(87,64,36,0.26)'
      ctx.lineWidth = Math.max(1, Math.round(0.4 * pxPerMm))
      ctx.beginPath()
      ctx.moveTo(margin * pxPerMm, footRuleY)
      ctx.lineTo((pageWidth - margin) * pxPerMm, footRuleY)
      ctx.stroke()

      // 页脚文字：左品牌，右页码
      ctx.fillStyle = '#8a7560'
      ctx.font = `${footFont}px Georgia, 'SimSun', serif`
      ctx.textBaseline = 'middle'
      ctx.textAlign = 'left'
      ctx.fillText(FOOTER, margin * pxPerMm, footTextY)
      ctx.textAlign = 'right'
      ctx.fillText(`第 ${i + 1} 页 / 共 ${totalPages} 页`, (pageWidth - margin) * pxPerMm, footTextY)
      ctx.textAlign = 'left'

      const pageImg = pageCanvas.toDataURL('image/jpeg', 0.92)
      pdf.addImage(pageImg, 'JPEG', 0, 0, pageWidth, pageHeight)
    }

    const fileName = `${job.name}_匹配报告_${new Date().toISOString().slice(0, 10)}.pdf`
    pdf.save(fileName)
    ElMessage.success('PDF 导出成功')
  } catch (err) {
    console.error('PDF 导出失败:', err)
    ElMessage.error('PDF 导出失败，请重试')
  } finally {
    container.remove()
    loading.close()
    pdfExporting = false
  }
}

onMounted(async () => {
  try {
    allJobs.value = await services.getJobs()
  } catch {
    allJobs.value = []
  }

  // 拉取上次持久化的匹配报告：有则直接展示，无需重新生成。
  // 只要目标岗位 id 存在就恢复选择（即使报告仍在生成中），否则生成完成后
  // 会因 selectedJobId 为空而无法命中 hasReport，报告卡在空态。
  await analysisStore.loadMatchReport()
  const savedJobId = analysisStore.matchJobId
  if (savedJobId && allJobs.value.some(j => j.id === savedJobId)) {
    selectedJobId.value = savedJobId
    editing.value = false
    if (analysisStore.matchReport) displayScore.value = analysisStore.matchReport.score
  }

  const u = userStore.userInfo
  if (u?.hasResume) {
    resumeUploaded.value = true
    resumeFileName.value = u.resumeName || '已上传简历'
  }
})

onUnmounted(() => {
  if (scoreTimer) clearInterval(scoreTimer)
})
</script>

<style scoped>
.matching-page {
  height: calc(100vh - 56px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.matching-content {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  width: 100%;
  max-width: 1240px;
  margin: 0 auto;
  padding: 24px 24px 28px;
}

/* ===== Hero ===== */
.page-hero {
  flex: 0 0 auto;
  margin-bottom: 20px;
}

.hero-paper {
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
  padding: 24px 30px;
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
}
.hero-paper::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none; z-index: 0;
}
.hero-paper > * { position: relative; z-index: 1; }

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

/* ===== 布局 ===== */
.matching-layout {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-wrap: nowrap;
  align-items: stretch;
}

.matching-sidebar {
  flex: 0 0 360px;
  max-width: 360px;
  margin-right: 24px;
  overflow: hidden;
  min-height: 0;
  transition: max-width 0.4s ease, margin-right 0.4s ease, opacity 0.3s;
}

.matching-sidebar .paper-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.matching-sidebar .card-inner {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}

.sidebar-hidden {
  max-width: 0 !important;
  margin-right: 0 !important;
  opacity: 0;
}

.sidebar-hidden .card-inner {
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.3s;
}

.matching-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
}

/* ===== Paper Card ===== */
.paper-card {
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
}
.paper-card::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none; z-index: 0;
}
.paper-card > * { position: relative; z-index: 1; }

.card-inner {
  padding: 24px;
}

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

/* ===== 岗位搜索 ===== */
.job-select {
  width: 100%;
}

/* EP v2 的 el-select 用 .el-select__wrapper（box-shadow 描边），改成 real border 统一纸感 */
.job-select :deep(.el-select__wrapper) {
  background: rgba(255, 253, 243, 0.94) !important;
  border: 1px solid rgba(87, 64, 36, 0.32) !important;
  border-radius: 2px !important;
  box-shadow: inset 0 1px 2px rgba(87, 64, 36, 0.05), inset 0 0 0 1px rgba(255, 252, 240, 0.5) !important;
}
.job-select :deep(.el-select__wrapper:hover) {
  border-color: rgba(87, 64, 36, 0.5) !important;
}
.job-select :deep(.el-select__wrapper.is-focused) {
  border-color: #3b2412 !important;
}
.job-select :deep(.el-select__placeholder) {
  color: rgba(87, 64, 36, 0.62) !important;
  font-family: 'SimSun', 'Songti SC', serif;
}
.job-select :deep(.el-select__selected-item) {
  color: #3b2412;
  font-family: 'SimSun', 'Songti SC', serif;
}
.job-select :deep(.el-select__input) {
  font-family: 'SimSun', 'Songti SC', serif;
  color: #3b2412;
}

.select-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.option-salary {
  font-size: 12px;
  color: #6f5438;
}

.selected-job-info {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}

.selected-job-name {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 15px;
  font-weight: 700;
  color: #2a1a0e;
  margin: 0 0 6px;
}

.selected-job-desc {
  font-size: 12px;
  line-height: 1.7;
  color: rgba(79, 57, 31, 0.85);
  margin: 0 0 10px;
}

.selected-job-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.skill-tag {
  font-size: 10px;
  padding: 2px 6px;
  border: 1px solid rgba(87, 64, 36, 0.28);
  background: rgba(243, 230, 203, 0.4);
  color: #5a3d28;
  font-family: 'SimSun', 'Songti SC', serif;
}

/* ===== 简历上传 ===== */
.resume-upload-area {
  margin-top: 4px;
}

.upload-zone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 28px;
  border: 1px dashed rgba(87, 64, 36, 0.48);
  background: rgba(252, 247, 235, 0.85);
  cursor: pointer;
  transition: all 0.2s;
}

.upload-zone:hover {
  border-color: rgba(87, 64, 36, 0.62);
  background: rgba(248, 240, 222, 0.9);
}

.upload-icon {
  font-size: 32px;
  color: #5a3d28;
  margin-bottom: 8px;
}

.upload-text {
  font-size: 14px;
  color: #3b2412;
  margin: 0 0 4px;
  font-family: 'SimSun', 'Songti SC', serif;
  letter-spacing: 1px;
}

.upload-hint {
  font-size: 11px;
  color: rgba(87, 64, 36, 0.8);
  margin: 0;
}

.resume-status {
  padding: 14px;
  border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}

.resume-file {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.resume-file-icon {
  font-size: 24px;
  color: #3b2412;
}

.resume-file-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.resume-file-name {
  font-size: 13px;
  color: #3b2412;
  font-family: 'SimSun', 'Songti SC', serif;
}

.resume-file-hint {
  font-size: 11px;
  color: #10b981;
}

.resume-file-hint.hint-error {
  color: #b91c1c;
}

/* 上传模式切换 */
.upload-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 10px;
  border-bottom: 1px solid rgba(87, 64, 36, 0.2);
}

.tab-btn {
  flex: 1;
  padding: 7px 0;
  border: 1px solid rgba(87, 64, 36, 0.24);
  border-bottom: none;
  background: rgba(243, 230, 203, 0.35);
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px;
  color: #5a3d28;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn.active {
  background: #3b2412;
  color: #fbf3e2;
  border-color: #2a1a0e;
}

/* 粘贴文本 */
.paste-zone {
  border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
  padding: 10px;
}

.paste-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 8px 10px;
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: rgba(255, 253, 243, 0.94);
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px;
  line-height: 1.7;
  color: #2a1a0e;
  resize: vertical;
  outline: none;
}

.paste-textarea:focus {
  border-color: rgba(87, 64, 36, 0.5);
}

.paste-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.parse-btn {
  flex: 1;
  padding: 7px 0;
  border: 1px solid rgba(87, 64, 36, 0.34);
  background: rgba(243, 230, 203, 0.5);
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px;
  color: #3b2412;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.2s;
}

.parse-btn:hover {
  background: #3b2412;
  color: #fbf3e2;
  border-color: #2a1a0e;
}

.resume-reupload {
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
  transition: all 0.2s;
}

.resume-reupload:hover {
  background: rgba(87, 64, 36, 0.08);
  border-color: rgba(87, 64, 36, 0.42);
}

/* ===== 报告区域 ===== */
.report-card {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.report-card .card-inner {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.report-card .report-header {
  flex: 0 0 auto;
}

.report-card .card-divider {
  flex: 0 0 auto;
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.report-actions {
  display: flex;
  gap: 8px;
}

.export-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  border: 1px solid rgba(87, 64, 36, 0.42);
  background: rgba(250, 242, 222, 0.9);
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px;
  color: #3b2412;
  letter-spacing: 0.5px;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.1), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}

.export-btn:hover {
  background: #3b2412;
  color: #fbf3e2;
  border-color: #2a1a0e;
}

/* 空态 */
.analyzing-panel {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 70px 20px;
}

.analyzing-spinner {
  width: 42px;
  height: 42px;
  border: 3px solid rgba(87, 64, 36, 0.18);
  border-top-color: #3b2412;
  border-radius: 50%;
  animation: analyzing-spin 0.9s linear infinite;
  margin-bottom: 22px;
}

@keyframes analyzing-spin {
  to { transform: rotate(360deg); }
}

.analyzing-title {
  font-size: 16px;
  color: #3b2412;
  margin: 0 0 8px;
  font-family: 'SimSun', 'Songti SC', serif;
  letter-spacing: 1px;
}

.analyzing-desc {
  font-size: 13px;
  color: rgba(87, 64, 36, 0.8);
  margin: 0;
}

.report-empty {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
}

.empty-icon-doc {
  width: 56px;
  height: 68px;
  border: 1px solid rgba(87, 64, 36, 0.4);
  margin-bottom: 20px;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
}

.doc-lines span {
  display: block;
  width: 28px;
  height: 1px;
  background: rgba(87, 64, 36, 0.28);
  margin-bottom: 6px;
}

.empty-title {
  font-size: 15px;
  color: #3b2412;
  margin: 0 0 6px;
  font-family: 'SimSun', 'Songti SC', serif;
  letter-spacing: 1px;
}

.empty-desc {
  font-size: 13px;
  color: rgba(87, 64, 36, 0.8);
  margin: 0 0 20px;
}

.start-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 28px;
  border: 1px solid var(--color-primary-dark, #2a1a0e);
  background: var(--color-primary, #3b2412);
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 14px;
  font-weight: 600;
  color: #fbf3e2;
  letter-spacing: 2px;
  cursor: pointer;
  transition: all 0.2s;
  border-radius: 2px;
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.2), inset 0 0 0 1px rgba(255, 252, 240, 0.1);
}

.start-btn:hover:not(:disabled) {
  background: var(--color-primary-light, #5a3d28);
  border-color: #2a1a0e;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(64, 45, 20, 0.3);
}

.start-btn:disabled {
  background: var(--color-primary, #3b2412);
  border-color: #2a1a0e;
  color: #fbf3e2;
  box-shadow: none;
  cursor: not-allowed;
}

/* ===== 报告内容 ===== */
.report-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-top: 8px;
  padding-right: 6px;
}

/* §1 结论横幅 — 醒目总分 */
.verdict-hero {
  position: relative;
  padding: 22px 26px 20px;
  margin-bottom: 24px;
  border: 1px solid rgba(87, 64, 36, 0.42);
  background:
    radial-gradient(ellipse 120px 90px at 0% 0%, rgba(120, 80, 30, 0.18), transparent 70%),
    radial-gradient(ellipse 140px 110px at 100% 100%, rgba(120, 80, 30, 0.16), transparent 70%),
    rgba(251, 243, 226, 0.7);
  box-shadow:
    inset 0 0 0 1px rgba(255, 252, 240, 0.5),
    inset 0 0 0 4px rgba(251, 243, 226, 0.9),
    inset 0 0 0 5px rgba(87, 64, 36, 0.28);
}

.verdict-hero::before {
  content: '';
  position: absolute;
  inset: 8px;
  border: 1px dashed rgba(87, 64, 36, 0.24);
  pointer-events: none;
}

.hero-stamp {
  position: absolute;
  top: 10px;
  right: 14px;
  font-family: 'Georgia', serif;
  font-size: 10px;
  letter-spacing: 4px;
  color: rgba(87, 64, 36, 0.8);
  text-transform: uppercase;
}

.hero-score-row {
  display: flex;
  align-items: center;
  gap: 24px;
  flex-wrap: wrap;
}

.hero-score-block {
  display: flex;
  align-items: baseline;
  gap: 4px;
  position: relative;
  padding-right: 14px;
  border-right: 1px solid rgba(87, 64, 36, 0.22);
}

.hero-score-num {
  font-family: 'Georgia', serif;
  font-size: 64px;
  font-weight: 700;
  color: #2a1a0e;
  line-height: 1;
  letter-spacing: -2px;
  text-shadow:
    1px 1px 0 rgba(255, 252, 240, 0.6),
    2px 2px 4px rgba(64, 45, 20, 0.18);
}

.hero-score-suffix {
  font-family: 'Georgia', serif;
  font-size: 18px;
  font-weight: 400;
  color: #6f5438;
  letter-spacing: 1px;
}

.hero-verdict-block {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.hero-verdict-label {
  display: inline-block;
  font-family: 'SimSun', 'Songti SC', 'STSong', serif;
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 4px;
  padding: 4px 14px;
  border: 1px solid currentColor;
  background: rgba(251, 243, 226, 0.7);
  align-self: flex-start;
}

.hero-verdict-label.v-strong { color: #15803d; }
.hero-verdict-label.v-fair { color: #3b2412; }
.hero-verdict-label.v-partial { color: #b45309; }
.hero-verdict-label.v-weak { color: #b91c1c; }

.hero-job-name {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 13px;
  color: #5a3d28;
  letter-spacing: 1px;
}

.hero-bar {
  position: relative;
  height: 10px;
  margin-top: 16px;
  background: rgba(87, 64, 36, 0.1);
  border: 1px solid rgba(87, 64, 36, 0.22);
  overflow: hidden;
}

.hero-bar-fill {
  height: 100%;
  transition: width 0.8s ease;
  background-image: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 6px,
    rgba(255, 252, 240, 0.18) 6px,
    rgba(255, 252, 240, 0.18) 12px
  );
}

.hero-bar-fill.fill-strong { background-color: #15803d; }
.hero-bar-fill.fill-fair { background-color: #3b2412; }
.hero-bar-fill.fill-partial { background-color: #b45309; }
.hero-bar-fill.fill-weak { background-color: #b91c1c; }

.hero-bar-ticks {
  position: absolute;
  inset: 0;
  display: flex;
  justify-content: space-between;
  pointer-events: none;
}

.hero-bar-ticks span {
  width: 1px;
  height: 100%;
  background: rgba(87, 64, 36, 0.2);
}

.hero-summary {
  margin-top: 12px;
  padding: 8px 12px;
  border-left: 3px solid rgba(87, 64, 36, 0.32);
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 13px;
  color: #2a1a0e;
  line-height: 1.75;
  background: rgba(243, 230, 203, 0.28);
}

/* verdict 语义边框色 */
.verdict-hero.hero-strong { border-color: rgba(21, 128, 61, 0.5); }
.verdict-hero.hero-strong::before { border-color: rgba(21, 128, 61, 0.22); }
.verdict-hero.hero-partial { border-color: rgba(180, 83, 9, 0.5); }
.verdict-hero.hero-partial::before { border-color: rgba(180, 83, 9, 0.22); }
.verdict-hero.hero-weak { border-color: rgba(185, 28, 28, 0.5); }
.verdict-hero.hero-weak::before { border-color: rgba(185, 28, 28, 0.22); }

/* §通用段落标题 */
.report-section {
  margin-bottom: 22px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 0 0 14px;
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 14px;
  font-weight: 700;
  color: #3b2412;
  letter-spacing: 1px;
}

.section-line {
  flex: 1;
  height: 1px;
  background: rgba(87, 64, 36, 0.22);
}

/* §2 技能覆盖矩阵 */
.coverage-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-bottom: 14px;
  padding: 10px 14px;
  border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 13px;
}

.cov-stat i {
  font-style: normal;
  margin-right: 4px;
  font-weight: 700;
}

.cov-stat.cov-mastered i { color: #15803d; }
.cov-stat.cov-partial i { color: #b45309; }
.cov-stat.cov-missing i { color: #b91c1c; }
.cov-stat.cov-total { color: #6f5438; margin-left: auto; }

.coverage-grid {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}

.coverage-col {
  display: flex;
  flex-direction: column;
  border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
  min-height: 80px;
}

.col-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px;
  font-weight: 700;
  color: #2a1a0e;
  border-bottom: 1px dashed rgba(87, 64, 36, 0.22);
  letter-spacing: 1px;
}

.col-mastered .col-head { color: #15803d; }
.col-partial .col-head { color: #b45309; }
.col-missing .col-head { color: #b91c1c; }

.col-glyph {
  font-family: 'Georgia', serif;
  font-size: 14px;
}

.col-body {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 10px;
}

.skill-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px;
  padding: 4px 8px;
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: rgba(120, 80, 30, 0.13);
  color: #2a1a0e;
  letter-spacing: 0.5px;
}

.chip-mastered { border-color: rgba(21, 128, 61, 0.4); background: rgba(21, 128, 61, 0.08); }
.chip-mastered .chip-glyph { color: #15803d; }
.chip-partial { border-color: rgba(180, 83, 9, 0.4); background: rgba(180, 83, 9, 0.08); }
.chip-partial .chip-glyph { color: #b45309; }
.chip-missing { border-color: rgba(185, 28, 28, 0.4); background: rgba(185, 28, 28, 0.08); }
.chip-missing .chip-glyph { color: #b91c1c; }

.chip-glyph {
  font-family: 'Georgia', serif;
  font-weight: 700;
}

.chip-name {
  flex: 1;
}

.chip-level {
  font-family: 'Georgia', serif;
  font-size: 10px;
  padding: 0 4px;
  border: 1px solid rgba(87, 64, 36, 0.32);
  color: #5a3d28;
  background: rgba(243, 230, 203, 0.5);
  margin-left: 2px;
}

.chip-pri {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 10px;
  line-height: 1.4;
  padding: 0 4px;
  border: 1px solid currentColor;
  margin-left: 2px;
  background: rgba(251, 243, 226, 0.7);
}

.chip-pri.pri-must { color: #7a2a22; }
.chip-pri.pri-important { color: #b45309; }
.chip-pri.pri-bonus { color: #6f5438; }

.col-empty {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px;
  color: rgba(87, 64, 36, 0.8);
  padding: 4px 0;
}

/* §3 硬门槛 */
.req-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.req-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  border: 1px solid rgba(87, 64, 36, 0.3);
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 13px;
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
}

.req-row.req-pass-row {
  background: linear-gradient(90deg, rgba(21, 128, 61, 0.12), rgba(21, 128, 61, 0.04));
  border-color: rgba(21, 128, 61, 0.4);
}

.req-row.req-fail-row {
  background: linear-gradient(90deg, rgba(185, 28, 28, 0.12), rgba(185, 28, 28, 0.04));
  border-color: rgba(185, 28, 28, 0.4);
}

.req-label {
  font-weight: 700;
  color: #2a1a0e;
  min-width: 32px;
  padding: 2px 8px;
  background: rgba(251, 243, 226, 0.75);
  border: 1px solid rgba(87, 64, 36, 0.32);
  letter-spacing: 1px;
}

.req-user {
  color: #2a1a0e;
  padding: 2px 8px;
  background: rgba(255, 252, 240, 0.55);
  border: 1px solid rgba(87, 64, 36, 0.22);
}

.req-arrow {
  color: #6f5438;
  font-family: 'Georgia', serif;
}

.req-required {
  color: #3b2412;
  flex: 1;
  padding: 2px 8px;
  background: rgba(243, 230, 203, 0.4);
  border: 1px solid rgba(87, 64, 36, 0.2);
}

.req-status {
  font-weight: 700;
  font-family: 'Georgia', serif;
  padding: 3px 10px;
  border: 1px solid currentColor;
  letter-spacing: 1px;
}

.req-status.req-pass {
  color: #15803d;
  background: rgba(21, 128, 61, 0.12);
}

.req-status.req-fail {
  color: #b91c1c;
  background: rgba(185, 28, 28, 0.12);
}

/* §4 差距优先级标注 */
.gap-strip {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 12px;
}

.gap-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 10px;
  border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}

.gap-badge {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 2px;
  padding: 2px 10px;
  border: 1px solid currentColor;
  background: rgba(251, 243, 226, 0.7);
}

.gap-must .gap-badge { color: #7a2a22; }
.gap-important .gap-badge { color: #b45309; }
.gap-bonus .gap-badge { color: #6f5438; }

.gap-count {
  font-family: 'Georgia', serif;
  font-size: 34px;
  font-weight: 700;
  color: #2a1a0e;
  line-height: 1;
}

.gap-must .gap-count { color: #7a2a22; }
.gap-important .gap-count { color: #b45309; }
.gap-bonus .gap-count { color: #5a3d28; }

.gap-label {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 11px;
  color: rgba(79, 57, 31, 0.85);
  text-align: center;
}

/* §5 学习路径规划 */
.path-timeline {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.path-stage {
  border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}

.path-stage-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  border-bottom: 1px dashed rgba(87, 64, 36, 0.22);
}

.path-phase {
  font-family: 'Georgia', serif;
  font-size: 13px;
  font-weight: 700;
  color: #fbf3e2;
  background: #3b2412;
  width: 22px;
  height: 22px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.path-stage-name {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 13px;
  font-weight: 700;
  color: #2a1a0e;
  letter-spacing: 1px;
}

.path-period {
  font-family: 'Georgia', serif;
  font-size: 11px;
  color: #6f5438;
  padding: 1px 8px;
  border: 1px solid rgba(87, 64, 36, 0.3);
  flex-shrink: 0;
}

.path-focus {
  margin-left: auto;
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 11px;
  color: #5a3d28;
  text-align: right;
}

.path-steps {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
}

.path-step {
  display: flex;
  align-items: baseline;
  gap: 6px;
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px;
  padding: 6px 8px;
  border: 1px solid rgba(87, 64, 36, 0.28);
  background: rgba(120, 80, 30, 0.08);
  color: #2a1a0e;
  line-height: 1.5;
  flex-wrap: wrap;
}

.path-step-skill {
  font-weight: 700;
  color: #2a1a0e;
  flex-shrink: 0;
}

.path-step-arrow {
  color: #6f5438;
  flex-shrink: 0;
}

.path-step-resource {
  color: #5a3d28;
  flex: 1;
  min-width: 120px;
}

.path-step-milestone {
  color: #3b2412;
  font-size: 11px;
  flex-basis: 100%;
  padding-left: 14px;
  border-top: 1px dotted rgba(87, 64, 36, 0.2);
  padding-top: 4px;
}

.ms-label {
  display: inline-block;
  font-size: 10px;
  color: #fbf3e2;
  background: #5a3d28;
  padding: 0 4px;
  margin-right: 6px;
}

.path-empty {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 13px;
  color: rgba(87, 64, 36, 0.8);
  padding: 12px;
  border: 1px dashed rgba(87, 64, 36, 0.3);
}

.path-link {
  margin-left: 6px;
  color: #b45309;
  text-decoration: underline;
  text-underline-offset: 3px;
}
.path-link:hover {
  color: #7a2a22;
}

/* ===== Responsive ===== */
@media (max-width: 1000px) {
  .matching-page {
    height: auto;
    overflow: visible;
  }

  .matching-content {
    display: block;
  }

  .matching-layout {
    flex-direction: column;
  }

  .matching-sidebar {
    flex: 0 0 100%;
    max-width: 100%;
    margin-right: 0;
    margin-bottom: 24px;
  }

  .matching-sidebar .paper-card {
    height: auto;
  }

  .matching-sidebar .card-inner {
    overflow: visible;
  }

  .sidebar-hidden {
    max-width: 0 !important;
    margin-bottom: 0 !important;
    opacity: 0;
  }

  .matching-main {
    flex: 0 0 100%;
  }

  .report-card {
    min-height: 500px;
  }

  .report-card .card-inner {
    overflow: visible;
  }

  .report-body {
    overflow: visible;
  }
}

@media (max-width: 720px) {
  .coverage-grid {
    grid-template-columns: 1fr;
  }

  .gap-strip {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 600px) {
  .hero-title {
    font-size: 22px;
    letter-spacing: 4px;
  }

  .hero-score-num {
    font-size: 48px;
  }

  .hero-score-row {
    gap: 14px;
  }

  .hero-score-block {
    padding-right: 0;
    border-right: none;
  }
}
</style>

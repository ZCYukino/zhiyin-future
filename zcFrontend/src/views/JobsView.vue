<template>
  <div class="jobs-page">
    <div class="jobs-content">
      <!-- 标题 -->
      <section class="page-hero">
        <div class="hero-paper">
          <h1 class="hero-title">岗位介绍</h1>
          <p class="hero-desc">浏览各技术分类下的核心岗位，了解岗位职责、薪资区间与核心技能要求。</p>
        </div>
      </section>

      <!-- 岗位搜索框（参考人岗匹配界面） -->
      <div class="search-bar">
        <el-select v-model="searchJobId" filterable clearable placeholder="搜索并选择岗位..." class="job-select"
          popper-class="job-select-popper" @change="onSearchSelect">
          <el-option v-for="job in allJobs" :key="job.id" :label="job.name" :value="job.id">
            <div class="select-option">
              <span>{{ job.name }}</span>
              <span class="option-salary">{{ salaryRangeText(job.salaryMin, job.salaryMax) }}</span>
            </div>
          </el-option>
        </el-select>
      </div>

      <!-- 分类导航栏 -->
      <div class="category-bar">
        <button class="category-tab" :class="{ active: activeCategory === '' }" @click="selectCategory('')">
          <IconEpMenu class="cat-icon" />
          <span class="cat-name">全部</span>
          <span class="cat-count">{{ allJobs.length }}</span>
        </button>
        <el-tooltip v-for="cat in categories" :key="cat.id" :content="cat.definition" placement="bottom" effect="light"
          :show-after="300" :hide-after="0" popper-class="category-tooltip">
          <button class="category-tab" :class="{ active: activeCategory === cat.id }" @click="selectCategory(cat.id)">
            <IconEpCpu v-if="cat.icon === 'cpu'" class="cat-icon" />
            <IconEpMonitor v-else-if="cat.icon === 'monitor'" class="cat-icon" />
            <IconEpPicture v-else-if="cat.icon === 'picture'" class="cat-icon" />
            <IconEpOdometer v-else-if="cat.icon === 'odometer'" class="cat-icon" />
            <IconEpSetUp v-else-if="cat.icon === 'set-up'" class="cat-icon" />
            <IconEpLock v-else-if="cat.icon === 'lock'" class="cat-icon" />
            <IconEpGuide v-else-if="cat.icon === 'guide'" class="cat-icon" />
            <IconEpFinished v-else-if="cat.icon === 'finished'" class="cat-icon" />
            <IconEpCpu v-else class="cat-icon" />
            <span class="cat-name">{{ cat.name }}</span>
            <span class="cat-count">{{ getJobCount(cat.id) }}</span>
          </button>
        </el-tooltip>
      </div>

      <!-- 选中分类的定义摘要 -->
      <div v-if="activeDefinition" class="category-definition-bar">
        <span class="def-icon">●</span>
        <span class="def-text">{{ activeDefinition }}</span>
      </div>

      <!-- 岗位卡片列表 -->
      <div class="jobs-grid">
        <div v-for="job in filteredJobs" :key="job.id" class="job-card"
          :class="{ highlighted: highlightId && highlightId === job.id }" @click="jobCardClick(job.id)">
          <div class="job-card-inner">
            <!-- 头部：岗位名称 + 标识 + 薪资 -->
            <div class="job-card-head">
              <div class="job-card-title-row">
                <h3 class="job-name">{{ job.name }}</h3>
                <span v-if="topRank(job) > 0" class="job-badge hot">TOP {{ topRank(job) }}</span>
                <span v-if="job.isNew" class="job-badge new">NEW</span>
              </div>
              <div class="job-salary">
                <span class="salary-amount">{{ jobSalary(job) }}</span>
                <span v-if="job.salaryMin != null && job.salaryMax != null" class="salary-unit">/ 月</span>
              </div>
            </div>

            <div class="job-card-divider"></div>

            <!-- 核心职责（两行截断） -->
            <p class="job-desc">{{ job.description }}</p>

            <!-- 技能点级能力要求 -->
            <div class="job-req-block">
              <div class="req-head">
                <span class="req-title">技能点要求</span>
                <span class="req-count">共 {{ jobSkills(job).total }} 项</span>
              </div>
              <div class="req-chips">
                <span v-for="s in jobSkills(job).top" :key="s.name" class="req-chip"
                  :class="s.priority === 'must' ? 'req-must' : 'req-other'"
                  :title="priTitle(s.priority) + ' · ' + (s.level === 'junior' ? '入门' : s.level === 'mid' ? '进阶' : '资深')">
                  {{ s.name }}
                </span>
                <span v-if="jobSkills(job).extra > 0" class="req-more">+{{ jobSkills(job).extra }}</span>
              </div>
            </div>

            <!-- 底部信息 -->
            <div class="job-card-footer">
              <div class="job-meta">
                <span v-if="job.companyCount != null" class="job-companies">{{ job.companyCount }} 家在招</span>
                <span v-if="job.trend" class="job-trend" :class="job.trend">{{ trendText(job.trend) }}</span>
              </div>
              <span v-if="jobEdu(job)" class="job-edu">{{ jobEdu(job) }}</span>
            </div>
          </div>
        </div>

        <!-- 空态 -->
        <div v-if="filteredJobs.length === 0" class="empty-state">
          <div class="empty-icon"></div>
          <p class="empty-text">该分类下暂无岗位数据</p>
        </div>
      </div>
      <div class="job-detail-container" v-if="jobUseDisabled" @click="closeDetail">
        <div class="job-Detail" @click.stop>
          <button class="detail-close-fab" @click="closeDetail" aria-label="关闭">✕</button>
          <jobDetail v-if="selectedJob" :job="selectedJob" @select-job="onSelectJob"></jobDetail>
        </div>
      </div>


    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'
import { jobCategories, priorityOf, salaryRangeText, trendText, MISSING_VALUE } from '@/models'
import type { JobItem, SkillLevel, SkillPriority } from '@/models'
import { services } from '@/services'

import jobDetail from '@/components/jobDetail.vue'

const route = useRoute()

const categories = jobCategories
const activeCategory = ref('')
const highlightId = ref<string>('')
const searchJobId = ref('')

const jobUseDisabled = ref(false);
const selectedJob = ref<JobItem | null>(null);

const allJobs = ref<JobItem[]>([])

// 展示数据 = 后端精选的 30 条（含 5 新兴，已按热门程度降序）
const TOP_HOT_COUNT = 5

/** 岗位在展示列表中的热门排名（1-5 为最热门 TOP5，0 表示非 TOP） */
function topRank(job: JobItem): number {
  const idx = allJobs.value.findIndex(j => j.id === job.id)
  return idx >= 0 && idx < TOP_HOT_COUNT ? idx + 1 : 0
}

const filteredJobs = computed(() => {
  if (!activeCategory.value) return allJobs.value
  return allJobs.value.filter(j => j.categoryId === activeCategory.value)
})

const activeDefinition = computed(() => {
  if (!activeCategory.value) return ''
  return categories.find(c => c.id === activeCategory.value)?.definition || ''
})

function openJob(jobId: string) {
  const j = allJobs.value.find(j => j.id === jobId)
  if (!j) return
  highlightId.value = jobId
  selectedJob.value = j
  jobUseDisabled.value = true
}
function jobCardClick(jobId: string) {
  openJob(jobId)
}
function onSearchSelect(id: string) {
  if (id) openJob(id)
}
function closeDetail() {
  jobUseDisabled.value = false
  selectedJob.value = null
  highlightId.value = ''
}
function onSelectJob(jobId: string) {
  const j = allJobs.value.find(j => j.id === jobId)
  if (j) {
    selectedJob.value = j
    highlightId.value = jobId
  }
}
function getJobCount(catId: string): number {
  return allJobs.value.filter(j => j.categoryId === catId).length
}

// ===== 岗位卡片：技能点级能力要求 =====
interface CardSkill {
  name: string
  priority: SkillPriority
  level: SkillLevel
}
const priRank: Record<SkillPriority, number> = { must: 0, important: 1, bonus: 2 }
const lvlRank: Record<SkillLevel, number> = { junior: 0, mid: 1, senior: 2 }

/** 取岗位技能矩阵（后端内嵌 progression，缺失回退 job.skills），按 优先级→资历 排序 */
function jobSkillItems(job: JobItem): CardSkill[] {
  const prog = job.progression
  let specs: { name: string; level: SkillLevel }[] = []
  if (prog) {
    specs = [
      ...prog.junior.map(s => ({ name: s.name, level: 'junior' as const })),
      ...prog.mid.map(s => ({ name: s.name, level: 'mid' as const })),
      ...prog.senior.map(s => ({ name: s.name, level: 'senior' as const })),
    ]
  } else {
    specs = job.skills.map(s => ({ name: s, level: 'junior' as SkillLevel }))
  }
  return specs
    .map(s => ({ name: s.name, priority: priorityOf(s.level), level: s.level }))
    .sort((a, b) => priRank[a.priority] - priRank[b.priority] || lvlRank[a.level] - lvlRank[b.level])
}
function jobSkills(job: JobItem) {
  const all = jobSkillItems(job)
  return { all, top: all.slice(0, 6), extra: Math.max(0, all.length - 6), total: all.length }
}
/** 学历门槛短标签：统一为「X及以上」/「不限」（去掉「学历/学位」后缀、归一「以上」） */
function jobEdu(job: JobItem): string {
  const s = (job.requirements?.education || '').trim()
  if (!s) return ''
  if (s.includes('不限')) return '不限'
  const m = s.match(/^(博士|硕士|本科|大专)[^，,]*/)
  if (!m) return s.split(/[，,]/)[0]
  let v = m[0].replace(/(学历|学位|毕业)$/, '')
  if (v.endsWith('以上') && !v.endsWith('及以上')) v = v.slice(0, -2) + '及以上'
  return v
}
function priTitle(p: SkillPriority): string {
  return p === 'must' ? '必备技能' : p === 'important' ? '重要技能' : '加分技能'
}
/** 薪资区间（带 K 与空格分隔）；任一端缺失即「—」，不显示 / 月 */
function jobSalary(job: JobItem): string {
  if (job.salaryMin == null || job.salaryMax == null) return MISSING_VALUE
  return `${job.salaryMin}K - ${job.salaryMax}K`
}

function selectCategory(catId: string) {
  activeCategory.value = activeCategory.value === catId ? '' : catId
}

onMounted(async () => {
  try {
    allJobs.value = await services.getFeaturedJobs()
  } catch {
    allJobs.value = []
  }
  const hl = (route.query.highlight as string) || ''
  if (hl) openJob(hl)
  else highlightId.value = ''
})

// 支持从首页「新岗位发现」跳转：query.highlight 变化时自动打开详情
watch(() => route.query.highlight, (v) => {
  if (v) openJob(v as string)
})

// 详情弹窗打开时锁定背景滚动，避免滚动弹窗内容时背景页也跟着滚
watch(jobUseDisabled, (open) => {
  document.body.style.overflow = open ? 'hidden' : ''
})

onUnmounted(() => {
  document.body.style.overflow = ''
})
</script>

<style scoped>
.jobs-page {
  min-height: calc(100vh - 56px);
}

.jobs-content {
  max-width: 1240px;
  margin: 0 auto;
  padding: 28px 24px 40px;
}

/* ===== Hero ===== */
.page-hero {
  margin-bottom: 24px;
}

.hero-paper {
  background:
    radial-gradient(ellipse 80px 60px at 0% 0%, rgba(120, 80, 30, 0.14), transparent 70%),
    radial-gradient(ellipse 80px 60px at 100% 0%, rgba(120, 80, 30, 0.12), transparent 70%),
    radial-gradient(ellipse 90px 70px at 0% 100%, rgba(120, 80, 30, 0.16), transparent 70%),
    radial-gradient(ellipse 90px 70px at 100% 100%, rgba(120, 80, 30, 0.14), transparent 70%),
    #fbf3e2;
  border: 1px solid rgba(87, 64, 36, 0.34);
  box-shadow:
    0 16px 36px rgba(64, 45, 20, 0.12),
    0 6px 14px rgba(64, 45, 20, 0.06),
    inset 0 0 0 1px rgba(255, 252, 240, 0.55),
    inset 0 0 0 4px rgba(251, 243, 226, 1),
    inset 0 0 0 5px rgba(87, 64, 36, 0.24);
  padding: 24px 30px;
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
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

/* ===== 岗位搜索框 ===== */
.search-bar {
  margin-bottom: 16px;
}

.job-select {
  width: 100%;
  max-width: 420px;
}

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

/* ===== 分类导航栏 ===== */
.category-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 20px;
  padding: 16px 20px;
  background: #fbf3e2;
  border: 1px solid rgba(87, 64, 36, 0.30);
  box-shadow: 0 6px 16px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.4);
}

.category-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid rgba(87, 64, 36, 0.42);
  background: rgba(252, 247, 235, 0.9);
  color: #5a3d28;
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  font-size: 13px;
  letter-spacing: 1px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  box-shadow: 0 2px 8px rgba(64,45,20,0.12), inset 0 0 0 1px rgba(255,252,240,0.5);
}

.category-tab:hover {
  color: #3b2412;
  background: rgba(248, 240, 222, 0.92);
  border-color: rgba(87, 64, 36, 0.55);
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(64,45,20,0.12), inset 0 0 0 1px rgba(255,252,240,0.5);
}

.category-tab.active {
  color: #fbf3e2;
  background: #3b2412;
  border-color: #2a1a0e;
  font-weight: 600;
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.18), 0 1px 3px rgba(42, 26, 14, 0.3);
}

.category-tab.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 20%;
  width: 60%;
  height: 2px;
  background: #fbf3e2;
}

.cat-icon {
  font-size: 14px;
}

.cat-count {
  font-size: 11px;
  color: #5a3d28;
  padding: 1px 6px;
  border: 1px solid rgba(87, 64, 36, 0.34);
  background: rgba(250, 243, 224, 0.9);
}
.category-tab.active .cat-count {
  color: #fbf3e2;
  border-color: rgba(251, 243, 226, 0.5);
  background: rgba(251, 243, 226, 0.12);
}

/* ===== 分类定义摘要 ===== */
.category-definition-bar {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 16px;
  margin-bottom: 20px;
  border-left: 3px solid #3b2412;
  background: rgba(87, 64, 36, 0.03);
  font-size: 13px;
  color: #5a3d28;
  line-height: 1.7;
  animation: slide-down 0.25s ease;
  font-family: 'SimSun', 'Songti SC', serif;
}

.def-icon {
  font-size: 8px;
  color: #3b2412;
  margin-top: 5px;
  flex-shrink: 0;
}

/* ===== 岗位卡片网格 ===== */
.jobs-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
}

.job-card {
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
  transition: all 0.3s ease;
  animation: card-rise 0.4s ease both;
  position: relative;
  overflow: hidden;
}
.job-card::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none; z-index: 0;
}

.job-card::after {
  content: '';
  position: absolute;
  top: 0;
  right: 0;
  width: 0;
  height: 0;
  border-style: solid;
  border-width: 0;
  border-color: transparent rgba(255, 248, 233, 0.9) transparent transparent;
  transition: border-width 0.3s ease;
}

.job-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 14px 32px rgba(64, 45, 20, 0.14), inset 0 0 0 1px rgba(255, 252, 240, 0.55);
  border-color: rgba(87, 64, 36, 0.42);
}

.job-card:hover::after {
  border-width: 16px;
}

.job-card.highlighted {
  border-color: rgba(87, 64, 36, 0.42);
  box-shadow: 0 0 0 2px rgba(87, 64, 36, 0.18);
}

.job-card-inner {
  padding: 22px 24px;
  display: flex;
  flex-direction: column;
  height: 100%;
}

.job-card-inner:hover {
  background: rgba(243, 230, 203, 0.18);
}

/* 卡片头部 */
.job-card-head {
  margin-bottom: 14px;
}

.job-card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.job-name {
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  font-size: 17px;
  font-weight: 700;
  color: #2a1a0e;
  letter-spacing: 1px;
  margin: 0;
}

.job-badge {
  font-size: 10px;
  letter-spacing: 1px;
  padding: 2px 6px;
  font-family: 'Georgia', serif;
  font-weight: 700;
}

.job-badge.new {
  color: #3b2412;
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: rgba(243, 230, 203, 0.45);
}

.job-badge.hot {
  color: #c2410c;
  border: 1px solid rgba(194, 65, 12, 0.32);
  background: rgba(194, 65, 12, 0.06);
}

.job-salary {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.salary-amount {
  font-size: 18px;
  font-weight: 700;
  color: #3b2412;
  font-family: 'Georgia', serif;
  letter-spacing: 0.5px;
}

.salary-unit {
  font-size: 12px;
  color: #6f5438;
}

/* 分割线 */
.job-card-divider {
  height: 1px;
  background: rgba(87, 64, 36, 0.18);
  margin-bottom: 12px;
}

/* 核心职责：两行截断，避免拉长卡片 */
.job-desc {
  font-size: 13px;
  line-height: 1.7;
  color: rgba(79, 57, 31, 0.85);
  margin: 0 0 14px;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 技能点级能力要求 */
.job-req-block {
  flex: 1;
  margin-bottom: 14px;
}

.req-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}

.req-title {
  font-family: 'SimSun', 'Songti SC', 'STSong', serif;
  font-size: 12px;
  font-weight: 700;
  color: #3b2412;
  letter-spacing: 1px;
}

.req-count {
  font-family: 'Georgia', serif;
  font-size: 11px;
  color: #6f5438;
}

.req-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.req-chip {
  font-size: 11px;
  padding: 3px 8px;
  font-family: 'SimSun', 'Songti SC', serif;
  letter-spacing: 0.3px;
  line-height: 1.4;
  border: 1px solid rgba(87, 64, 36, 0.28);
  background: rgba(243, 230, 203, 0.4);
  color: #5a3d28;
  cursor: help;
  transition: all 0.2s;
}

.req-chip.req-must {
  background: #3b2412;
  color: #fbf3e2;
  border-color: #2a1a0e;
  font-weight: 600;
}

.req-chip.req-other:hover {
  border-color: rgba(87, 64, 36, 0.5);
  background: rgba(243, 230, 203, 0.65);
}

.req-chip.req-must:hover {
  background: #2a1a0e;
}

.req-more {
  font-size: 11px;
  color: #5a3d28;
  padding: 3px 6px;
  align-self: center;
  font-family: 'Georgia', serif;
}

/* 底部 */
.job-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgba(87, 64, 36, 0.14);
}

.job-meta {
  display: flex;
  align-items: center;
  gap: 10px;
}

.job-companies {
  font-size: 11px;
  color: rgba(87,64,36,0.55);
}

.job-trend {
  font-size: 11px;
}

.job-trend.up {
  color: #10b981;
}

.job-trend.down {
  color: #ef4444;
}

.job-trend.stable {
  color: rgba(87,64,36,0.5);
}

.job-edu {
  font-size: 10px;
  padding: 2px 8px;
  border: 1px solid rgba(87, 64, 36, 0.3);
  background: rgba(251, 243, 226, 0.6);
  color: #5a3d28;
  font-family: 'SimSun', 'Songti SC', serif;
  letter-spacing: 0.3px;
}

/* 空态 */
.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 20px;
  color: rgba(87,64,36,0.5);
  font-family: 'SimSun', 'Songti SC', serif;
}

.empty-icon {
  width: 48px;
  height: 56px;
  border: 1px solid rgba(87, 64, 36, 0.28);
  margin-bottom: 16px;
  position: relative;
}

.empty-icon::before {
  content: '';
  position: absolute;
  top: 8px;
  left: 8px;
  right: 8px;
  height: 1px;
  background: rgba(87, 64, 36, 0.2);
  box-shadow: 0 10px 0 rgba(87, 64, 36, 0.2);
}

.empty-text {
  font-size: 14px;
  letter-spacing: 1px;
}

/* ===== Responsive ===== */
@media (max-width: 1100px) {
  .jobs-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 700px) {
  .jobs-grid {
    grid-template-columns: 1fr;
  }

  .hero-title {
    font-size: 22px;
    letter-spacing: 4px;
  }

  .category-bar {
    padding: 12px;
    gap: 6px;
  }

  .category-tab {
    padding: 6px 12px;
    font-size: 12px;
  }
}
</style>

<style>
/* ===== Popper 自定义样式 ===== */
.job-select-popper {
  background: #fbf3e2 !important;
  border: 1px solid rgba(87, 64, 36, 0.34) !important;
  border-radius: 2px !important;
  box-shadow: 0 8px 24px rgba(64, 45, 20, 0.14) !important;
}

.job-select-popper .el-select-dropdown__item {
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif !important;
  font-size: 13px !important;
  color: #3b2412 !important;
}

.job-select-popper .el-select-dropdown__item.is-hovering {
  background: rgba(243, 230, 203, 0.5) !important;
}

.job-select-popper .el-select-dropdown__item.is-selected {
  background: #3b2412 !important;
  color: #fbf3e2 !important;
}

.job-select-popper .el-select-dropdown__item.is-selected .option-salary {
  color: rgba(251, 243, 226, 0.75) !important;
}

.category-tooltip {
  background: #fbf3e2 !important;
  border: 1px solid rgba(87, 64, 36, 0.34) !important;
  border-radius: 2px !important;
  box-shadow: 0 8px 24px rgba(64, 45, 20, 0.14) !important;
  padding: 12px 16px !important;
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif !important;
  font-size: 13px !important;
  color: #3b2412 !important;
  line-height: 1.8 !important;
  max-width: 320px !important;
  word-wrap: break-word;
}

.category-tooltip .el-popper__arrow::before {
  background: #fbf3e2 !important;
  border: 1px solid rgba(87, 64, 36, 0.34) !important;
}

.job-Detail {
  position: fixed;
  top: 10%;
  left: 25%;
  width: 50%;
  height: 80%;
  background: #fbf3e2;
  border: 1px solid rgba(87, 64, 36, 0.34);
  box-shadow: 0 24px 50px rgba(64, 45, 20, 0.20), 0 10px 20px rgba(64, 45, 20, 0.10), inset 0 0 0 1px rgba(255, 252, 240, 0.55);
  z-index: 1000;
  overflow: auto;
  overscroll-behavior: contain;
}

.detail-close-fab {
  position: sticky;
  top: 12px;
  float: right;
  z-index: 20;
  width: 32px;
  height: 32px;
  margin: 12px 12px 0 0;
  border-radius: 50%;
  background: #3b2412;
  color: #fbf3e2;
  border: 1px solid #2a1a0e;
  cursor: pointer;
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  font-size: 16px;
  line-height: 1;
  box-shadow: 0 2px 8px rgba(42, 26, 14, 0.25);
  transition: transform 0.15s ease, background 0.15s ease;
}

.detail-close-fab:hover {
  transform: scale(1.08);
  background: #2a1a0e;
}
.job-detail-container{
  width: 100%;
  height: 100%;
  position: fixed;
  top: 0;
  left: 0;
  background: rgba(0, 0, 0, 0.4);
  z-index: 999;
}

@keyframes slide-down {
  from {
    opacity: 0;
    transform: translateY(-6px);
  }

  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

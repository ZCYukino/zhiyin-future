<script setup lang="ts">
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import {
  jobCategories,
  techStacksForGraph,
  capabilitySourceOf,
  changeReasonOf,
  salaryRangeText,
  countText,
  MISSING_VALUE,
} from '@/models'
import type { JobItem, GraphNode, GraphEdge, CapabilityChange, SkillProgression, JobRequirement, JobIntro } from '@/models'
import { services } from '@/services'
import type { JobProfile } from '@/services'

const props = defineProps<{ job: JobItem | null }>()
const emit = defineEmits<{
  (e: 'select-job', id: string): void
}>()

const SERIF = "'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif"

const graphData = ref<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] })
const capabilityChanges = ref<CapabilityChange[]>([])
const backendIntro = ref<JobIntro | null>(null)
const backendRequirement = ref<JobRequirement | null>(null)
const backendProgression = ref<SkillProgression | null>(null)
const profile = ref<JobProfile | null>(null)
const introLoading = ref(false)

const detailNote = computed(() => {
  if (!props.job) return ''
  return profile.value?.overview || backendIntro.value?.duties?.join('；') || props.job.description || ''
})

// 岗位画像优先，快照降级
const jobIntro = computed<JobIntro | null>(() => {
  if (!props.job) return null
  const base = backendIntro.value
  if (!base && !profile.value) return null
  const duties = profile.value?.duties?.length ? profile.value.duties : (base?.duties || [])
  const scenarios = profile.value?.scenarios?.length ? profile.value.scenarios : (base?.scenarios || [])
  return { duties, scenarios }
})

const introOverview = computed(() => profile.value?.overview || '')
const softSkills = computed(() => profile.value?.softSkills || [])
const careerPath = computed(() => profile.value?.careerPath || [])
const salaryReference = computed(() => profile.value?.salaryReference || '')
const industryOutlook = computed(() => profile.value?.industryOutlook || '')

const skillProgression = computed<SkillProgression | null>(() => {
  if (!props.job) return null
  return backendProgression.value || props.job.progression || null
})

const profileSkills = computed(() => profile.value?.skills || null)

interface LevelSkill {
  name: string
  desc?: string
  trend: 'up' | 'down' | 'stable' | 'new'
}
function toLevelSkills(specs: { name: string; desc?: string }[]): LevelSkill[] {
  return specs.map(s => ({
    name: s.name,
    desc: s.desc,
    trend: skillTrendFor(s.name),
  }))
}
const juniorSkills = computed<LevelSkill[]>(() => {
  const src = profileSkills.value?.junior?.length ? profileSkills.value.junior : (skillProgression.value?.junior || [])
  return toLevelSkills(src)
})
const midSkills = computed<LevelSkill[]>(() => {
  const src = profileSkills.value?.mid?.length ? profileSkills.value.mid : (skillProgression.value?.mid || [])
  return toLevelSkills(src)
})
const seniorSkills = computed<LevelSkill[]>(() => {
  const src = profileSkills.value?.senior?.length ? profileSkills.value.senior : (skillProgression.value?.senior || [])
  return toLevelSkills(src)
})

interface LevelColumn {
  key: string
  mark: string
  name: string
  sub: string
  pri: string
  priCls: string
  skills: LevelSkill[]
}
const levelColumns = computed<LevelColumn[]>(() => [
  { key: 'junior', mark: 'L1', name: '初级', sub: '基础必备', pri: '必备技能', priCls: 'pri-must', skills: juniorSkills.value },
  { key: 'mid', mark: 'L2', name: '中级', sub: '进阶掌握', pri: '重要技能', priCls: 'pri-important', skills: midSkills.value },
  { key: 'senior', mark: 'L3', name: '高级', sub: '资深专家', pri: '加分技能', priCls: 'pri-bonus', skills: seniorSkills.value },
])

const activeSkill = ref<string | null>(null)
function toggleSkill(level: string, name: string) {
  const k = `${level}:${name}`
  activeSkill.value = activeSkill.value === k ? null : k
}
function onDocClick(e: MouseEvent) {
  if (!(e.target as HTMLElement).closest('.skill-chip')) {
    activeSkill.value = null
  }
}

const graphNode = computed<GraphNode | null>(() => {
  if (!props.job) return null
  return graphData.value.nodes.find(n => n.type === 'job' && n.jobId === props.job!.id) || null
})

const graphJobId = computed(() => graphNode.value?.id || '')

const rawSkills = computed<string[]>(() => {
  if (!props.job) return []
  return props.job.skills || []
})

function skillTrendFor(skillName: string): 'up' | 'down' | 'stable' | 'new' {
  if (!skillName) return 'stable'
  const s = skillName.replace(/\s+/g, '').toLowerCase()
  let up = false,
    down = false,
    added = false
  for (const c of capabilityChanges.value) {
    for (const a of c.addedSkills || []) {
      if (a.replace(/\s+/g, '').toLowerCase().includes(s) || s.includes(a.replace(/\s+/g, '').toLowerCase())) {
        added = true
      }
    }
    for (const u of c.importanceUp || []) {
      if (u.replace(/\s+/g, '').toLowerCase().includes(s) || s.includes(u.replace(/\s+/g, '').toLowerCase())) {
        up = true
      }
    }
    for (const d of c.importanceDown || []) {
      if (d.replace(/\s+/g, '').toLowerCase().includes(s) || s.includes(d.replace(/\s+/g, '').toLowerCase())) {
        down = true
      }
    }
  }
  if (added) return 'new'
  if (up && !down) return 'up'
  if (down && !up) return 'down'
  if (up && down) return 'stable'
  return 'stable'
}

const evolutionChanges = computed<CapabilityChange[]>(() => {
  if (!graphJobId.value || !props.job) return []
  return capabilityChanges.value
    .filter(c => c.jobId === props.job!.id)
    .sort((a, b) => (a.period < b.period ? 1 : -1))
})

interface AdjacentJob {
  label: string
  relation: 'similar' | 'transfer' | 'advanced'
  edgeLabel: string
  jobId: string
}
const adjacentJobs = computed<AdjacentJob[]>(() => {
  if (!graphJobId.value) return []
  const id = graphJobId.value
  const edges = graphData.value.edges.filter(
    (e: GraphEdge) =>
      (e.source === id || e.target === id) &&
      e.relation &&
      ['similar', 'transfer', 'advanced'].includes(e.relation),
  )
  const out: AdjacentJob[] = []
  for (const e of edges) {
    const otherId = e.source === id ? e.target : e.source
    const node = graphData.value.nodes.find(n => n.id === otherId && n.type === 'job')
    if (!node) continue
    out.push({
      label: node.label,
      relation: e.relation as 'similar' | 'transfer' | 'advanced',
      edgeLabel: e.label,
      jobId: node.jobId || '',
    })
  }
  return out
})

const adjacentSimilar = computed(() => adjacentJobs.value.filter(a => a.relation === 'similar'))
const adjacentTransfer = computed(() => adjacentJobs.value.filter(a => a.relation === 'transfer'))
const adjacentAdvanced = computed(() => adjacentJobs.value.filter(a => a.relation === 'advanced'))

const discovered = computed(() => {
  if (!props.job || !props.job.isNew) return null
  if (!props.job.confidence) return null
  return {
    source: props.job.source || '多源数据聚合',
    confidence: props.job.confidence,
    discoveredDate: props.job.discoveredDate || '2026-07',
  }
})

const categoryName = computed(() => {
  if (!props.job) return ''
  return jobCategories.find(c => c.id === props.job!.categoryId)?.name || ''
})
const techStackName = computed(() => {
  const gn = graphNode.value
  if (!gn?.techStack) return ''
  return techStacksForGraph.find(t => t.id === gn.techStack)?.name || ''
})

// 空数组时 Math.max 得 -Infinity，以 0 兜底
const cityMax = computed(() => {
  if (!props.job) return 1
  const list = props.job.cityDistribution || []
  return Math.max(0, ...list.map(c => c.count)) || 1
})

const jobRequirement = computed<JobRequirement | null>(() => {
  if (!props.job) return null
  const p = profile.value?.requirements
  if (p && (p.education || p.experience || p.extra?.length)) {
    return { education: p.education, experience: p.experience, extra: p.extra }
  }
  return backendRequirement.value || null
})
const requirementRows = computed<{ label: string; value: string }[]>(() => {
  const r = jobRequirement.value
  if (!r) return []
  const rows: { label: string; value: string }[] = []
  if (r.education) rows.push({ label: '学历要求', value: r.education })
  if (r.experience) rows.push({ label: '工作经验', value: r.experience })
  for (const e of r.extra || []) if (e.value) rows.push({ label: e.label, value: e.value })
  return rows
})

function trendMeta(t: 'up' | 'down' | 'stable' | 'new') {
  switch (t) {
    case 'up':
      return { glyph: '▲', color: '#059669', text: '重要性上升' }
    case 'down':
      return { glyph: '▼', color: '#dc2626', text: '重要性下降' }
    case 'new':
      return { glyph: '✦', color: '#b45309', text: '新增技能' }
    default:
      return { glyph: '●', color: '#94a3b8', text: '稳定' }
  }
}
function jobTrendMeta(t: JobItem['trend']) {
  switch (t) {
    case 'up':
      return { glyph: '▲', text: '上升', color: '#10b981' }
    case 'down':
      return { glyph: '▼', text: '下降', color: '#ef4444' }
    case 'stable':
      return { glyph: '→', text: '稳定', color: 'rgba(87,64,36,0.55)' }
    default:
      return { glyph: '', text: MISSING_VALUE, color: 'rgba(87,64,36,0.55)' }
  }
}

function onAdjacentClick(jid: string) {
  if (jid) emit('select-job', jid)
}

async function loadJobDetail(jobId: string) {
  backendIntro.value = null
  backendRequirement.value = null
  backendProgression.value = null
  profile.value = null
  introLoading.value = true
  const d = await services.getJobDetail(jobId).catch(() => null)
  if (props.job?.id !== jobId) return
  if (d?.intro) backendIntro.value = d.intro
  if (d?.requirements) backendRequirement.value = d.requirements
  if (d?.progression) backendProgression.value = d.progression

  const p = await services.getJobProfile(jobId).catch(() => null)
  if (props.job?.id !== jobId) return
  if (p && p.duties?.length) profile.value = p
  introLoading.value = false
}

onMounted(async () => {
  document.addEventListener('click', onDocClick)
  const [g, cc] = await Promise.all([services.getGraph(), services.getCapabilityChanges()])
  if (g?.nodes?.length) graphData.value = g
  if (cc?.length) capabilityChanges.value = cc

  if (props.job?.id) loadJobDetail(props.job.id)
})

watch(
  () => props.job?.id,
  id => {
    activeSkill.value = null
    if (id) loadJobDetail(id)
  },
)

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
})
</script>

<template>
  <div v-if="job" class="detail-root paper-surface" @click.stop>
    <header class="detail-header">
      <div class="header-top">
        <div class="header-crumbs">
          <span class="crumb-cat">{{ categoryName }}</span>
          <span v-if="techStackName" class="crumb-sep">·</span>
          <span v-if="techStackName" class="crumb-stack">{{ techStackName }}</span>
        </div>
      </div>
      <div class="header-title-row">
        <h1 class="detail-title">{{ job.name }}</h1>
        <span v-if="job.isNew" class="badge new">NEW</span>
        <span v-if="job.hotScore != null && job.hotScore >= 90" class="badge hot">HOT</span>
      </div>
      <p class="detail-desc">{{ detailNote }}</p>
      <div v-if="discovered" class="discovered-bar">
        <span class="discovered-tag">✦ 新兴岗位</span>
        <span class="discovered-meta">来源 {{ discovered.source }}</span>
        <span class="discovered-meta">置信度 {{ Math.round(discovered.confidence * 100) }}%</span>
        <span class="discovered-meta">发现于 {{ discovered.discoveredDate }}</span>
      </div>
    </header>

    <section class="metrics-grid">
      <div class="metric-cell paper-inner">
        <div class="metric-value">{{ salaryRangeText(job.salaryMin, job.salaryMax) }}<span
          v-if="job.salaryMin != null && job.salaryMax != null" class="metric-unit">{{ job.salaryUnit }}</span></div>
        <div class="metric-label">薪资参考</div>
      </div>
      <div class="metric-cell paper-inner">
        <div class="metric-value">{{ countText(job.companyCount) }}<span
          v-if="job.companyCount != null" class="metric-unit">家在招</span></div>
        <div class="metric-label">招聘公司</div>
      </div>
      <div class="metric-cell paper-inner">
        <div class="metric-value">{{ countText(job.hotScore) }}<span
          v-if="job.hotScore != null" class="metric-unit">/100</span></div>
        <div class="metric-label">岗位热度</div>
      </div>
      <div class="metric-cell paper-inner">
        <div class="metric-value" :style="{ color: jobTrendMeta(job.trend).color }">
          <template v-if="job.trend">{{ jobTrendMeta(job.trend).glyph }} </template>{{ jobTrendMeta(job.trend).text }}
        </div>
        <div class="metric-label">市场趋势</div>
      </div>
    </section>

    <details v-if="jobIntro" class="acc-section" open>
      <summary class="acc-header">
        <span class="title-bar"></span>
        <span class="acc-title">岗位介绍</span>
        <span class="acc-arrow">▾</span>
      </summary>
      <div class="acc-body">
        <p class="section-note">核心职责与典型行业应用场景 — 岗位定义的要素构成。</p>
        <p v-if="introOverview" class="intro-overview">{{ introOverview }}</p>
        <div class="intro-grid">
          <div class="intro-block paper-inner">
            <div class="intro-head">
              <span class="intro-caption">核心职责</span>
            </div>
            <ul class="duty-list">
              <li v-for="(d, i) in jobIntro.duties" :key="i" class="duty-item">
                <span class="duty-num">{{ i + 1 }}</span>
                <span class="duty-text">{{ d }}</span>
              </li>
            </ul>
          </div>
          <div class="intro-block paper-inner">
            <div class="intro-head">
              <span class="intro-caption">典型行业应用场景</span>
              <span v-if="introLoading" class="intro-ai-badge">AI 生成中…</span>
            </div>
            <div v-if="jobIntro.scenarios.length" class="scenario-list">
              <div v-for="sc in jobIntro.scenarios" :key="sc.name" class="scenario-item">
                <span class="scenario-name">{{ sc.name }}</span>
                <span class="scenario-desc">{{ sc.desc }}</span>
              </div>
            </div>
            <p v-else class="scenario-empty">正在结合知识库生成典型应用场景…</p>
          </div>
        </div>
      </div>
    </details>

    <details v-if="requirementRows.length || skillProgression || profileSkills || rawSkills.length || softSkills.length" class="acc-section">
      <summary class="acc-header">
        <span class="title-bar"></span>
        <span class="acc-title">岗位要求</span>
        <span class="acc-arrow">▾</span>
      </summary>
      <div class="acc-body">
        <p class="section-note">岗位的硬性门槛、专业技能与综合素养要求。</p>

        <div v-if="requirementRows.length" class="req-sub">
          <div class="sub-label">硬性门槛</div>
          <div class="gate-row">
            <span v-for="row in requirementRows" :key="row.label" class="gate-chip">
              <span class="gate-key">{{ row.label }}</span>
              <span class="gate-val">{{ row.value }}</span>
            </span>
          </div>
        </div>

        <div v-if="skillProgression || profileSkills" class="req-sub">
          <div class="sub-label">专业技能</div>
          <p class="sub-hint">按初 / 中 / 高三级资历梳理，必备 / 重要 / 加分 对应岗位定义要素；▲▼●✦ 标记近期市场趋势，点击技能查看介绍。</p>
          <div class="progression-grid">
            <div v-for="col in levelColumns" :key="col.key" class="level-col">
              <div class="level-head">
                <span class="level-mark">{{ col.mark }}</span>
                <span class="level-name">{{ col.name }}</span>
                <span class="level-sub">{{ col.sub }}</span>
                <span class="level-pri" :class="col.priCls">{{ col.pri }}</span>
              </div>
              <div class="level-chips">
                <span v-for="s in col.skills" :key="s.name" class="skill-chip" :class="{ active: activeSkill === col.key + ':' + s.name }" @click="toggleSkill(col.key, s.name)">
                  <span class="chip-top">
                    <span class="chip-name">{{ s.name }}</span>
                    <span class="trend-glyph" :style="{ color: trendMeta(s.trend).color }">{{ trendMeta(s.trend).glyph }}</span>
                  </span>
                  <transition name="skill-pop">
                    <div v-if="activeSkill === col.key + ':' + s.name" class="skill-pop" @click.stop>
                      <div class="skill-pop-head">
                        <span class="skill-pop-name">{{ s.name }}</span>
                        <span class="skill-pop-pri" :class="col.priCls">{{ col.pri }} · {{ col.name }}</span>
                      </div>
                      <p class="skill-pop-desc">{{ s.desc || '该技能暂未收录详细说明。' }}</p>
                    </div>
                  </transition>
                </span>
              </div>
            </div>
          </div>
          <p class="skill-legend">
            <span class="legend-item"><span class="legend-glyph" style="color:#059669">▲</span>重要性上升</span>
            <span class="legend-item"><span class="legend-glyph" style="color:#dc2626">▼</span>重要性下降</span>
            <span class="legend-item"><span class="legend-glyph" style="color:#b45309">✦</span>新增技能</span>
            <span class="legend-item"><span class="legend-glyph" style="color:#94a3b8">●</span>稳定</span>
          </p>
        </div>
        <div v-else-if="rawSkills.length" class="req-sub">
          <div class="sub-label">专业技能</div>
          <p class="sub-hint">该岗位暂未接入技能图谱，以下为招聘 JD 摘录技能。</p>
          <div class="skill-chips">
            <span v-for="s in rawSkills" :key="s" class="skill-chip">{{ s }}</span>
          </div>
        </div>

        <div v-if="softSkills.length" class="req-sub">
          <div class="sub-label">软技能</div>
          <div class="soft-grid">
            <span v-for="s in softSkills" :key="s.name" class="soft-chip">
              <span class="soft-name">{{ s.name }}</span>
              <span v-if="s.desc" class="soft-desc">{{ s.desc }}</span>
            </span>
          </div>
        </div>
      </div>
    </details>

    <details v-if="careerPath.length || industryOutlook || salaryReference || job.cityDistribution?.length" class="acc-section">
      <summary class="acc-header">
        <span class="title-bar"></span>
        <span class="acc-title">职业前景</span>
        <span class="acc-arrow">▾</span>
      </summary>
      <div class="acc-body">
        <p class="section-note">从成长路径、行业前景到地域分布，全景了解岗位发展空间。</p>

        <div v-if="careerPath.length" class="req-sub">
          <div class="sub-label">发展路径</div>
          <div class="path-list">
            <div v-for="(p, i) in careerPath" :key="p.title" class="path-step paper-inner">
              <span class="path-stage">{{ p.stage || '阶段 ' + (i + 1) }}</span>
              <span class="path-title">{{ p.title }}</span>
              <span v-if="p.desc" class="path-desc">{{ p.desc }}</span>
            </div>
          </div>
        </div>

        <div v-if="industryOutlook || salaryReference" class="req-sub">
          <div class="sub-label">行业前景 · 薪资参考</div>
          <div class="outlook-grid">
            <div v-if="industryOutlook" class="outlook-cell paper-inner">
              <span class="outlook-caption">行业前景</span>
              <p class="outlook-text">{{ industryOutlook }}</p>
            </div>
            <div v-if="salaryReference" class="outlook-cell paper-inner">
              <span class="outlook-caption">薪资参考</span>
              <p class="outlook-text">{{ salaryReference }}</p>
            </div>
          </div>
        </div>

        <div v-if="job.cityDistribution?.length" class="req-sub">
          <div class="sub-label">城市分布</div>
          <div class="city-list paper-inner">
            <div v-for="city in job.cityDistribution" :key="city.city" class="city-row">
              <span class="city-name">{{ city.city }}</span>
              <div class="city-bar-track">
                <div class="city-bar-fill" :style="{ width: (city.count / cityMax * 100) + '%' }"></div>
              </div>
              <span class="city-count">{{ city.count }}</span>
            </div>
          </div>
        </div>
      </div>
    </details>

    <details v-if="evolutionChanges.length" class="acc-section">
      <summary class="acc-header">
        <span class="title-bar"></span>
        <span class="acc-title">能力演化时间线</span>
        <span class="acc-arrow">▾</span>
      </summary>
      <div class="acc-body">
        <p class="section-note">该岗位能力要求随行业多源数据持续更新，以下为近几个周期的变更记录。</p>
        <div v-for="c in evolutionChanges" :key="c.period" class="evo-block paper-inner">
          <div class="evo-period">{{ c.period }}</div>
          <div v-if="c.addedSkills.length" class="evo-row">
            <span class="evo-mark add">✦ 新增</span>
            <span v-for="s in c.addedSkills" :key="s" class="evo-chip add">{{ s }}</span>
          </div>
          <div v-if="c.removedSkills.length" class="evo-row">
            <span class="evo-mark remove">✕ 淘汰</span>
            <span v-for="s in c.removedSkills" :key="s" class="evo-chip remove">{{ s }}</span>
          </div>
          <div v-if="c.importanceUp.length" class="evo-row">
            <span class="evo-mark up">▲ 上升</span>
            <span v-for="s in c.importanceUp" :key="s" class="evo-chip up">{{ s }}</span>
          </div>
          <div v-if="c.importanceDown.length" class="evo-row">
            <span class="evo-mark down">▼ 下降</span>
            <span v-for="s in c.importanceDown" :key="s" class="evo-chip down">{{ s }}</span>
          </div>
          <div class="evo-meta">
            <span class="evo-meta-item"><span class="meta-label">更新说明</span>{{ changeReasonOf(c) }}</span>
            <span class="evo-meta-item"><span class="meta-label">数据源</span>{{ capabilitySourceOf().join(' · ') }}</span>
          </div>
        </div>
      </div>
    </details>

    <details v-if="adjacentJobs.length" class="acc-section">
      <summary class="acc-header">
        <span class="title-bar"></span>
        <span class="acc-title">相邻岗位</span>
        <span class="acc-arrow">▾</span>
      </summary>
      <div class="acc-body">
        <div v-if="adjacentSimilar.length" class="adj-group">
          <div class="adj-head"><span class="adj-mark similar">能力相近</span></div>
          <div class="adj-chips">
            <button v-for="a in adjacentSimilar" :key="a.label" class="adj-chip similar" :disabled="!a.jobId" @click="onAdjacentClick(a.jobId)">{{ a.label }}</button>
          </div>
        </div>
        <div v-if="adjacentTransfer.length" class="adj-group">
          <div class="adj-head"><span class="adj-mark transfer">转岗相关</span></div>
          <div class="adj-chips">
            <button v-for="a in adjacentTransfer" :key="a.label" class="adj-chip transfer" :disabled="!a.jobId" @click="onAdjacentClick(a.jobId)">{{ a.label }}</button>
          </div>
        </div>
        <div v-if="adjacentAdvanced.length" class="adj-group">
          <div class="adj-head"><span class="adj-mark advanced">进阶方向</span></div>
          <div class="adj-chips">
            <button v-for="a in adjacentAdvanced" :key="a.label" class="adj-chip advanced" :disabled="!a.jobId" @click="onAdjacentClick(a.jobId)">→ {{ a.label }}</button>
          </div>
        </div>
      </div>
    </details>
  </div>
</template>

<style scoped>
.detail-root {
  font-family: v-bind("SERIF");
  position: relative;
  padding: 28px 30px 36px;
  color: #2a1a0e;
  max-width: 900px;
  margin: 0 auto;
  background:
    radial-gradient(ellipse 80px 60px at 0% 0%, rgba(120, 80, 30, 0.14), transparent 70%),
    radial-gradient(ellipse 80px 60px at 100% 0%, rgba(120, 80, 30, 0.12), transparent 70%),
    radial-gradient(ellipse 90px 70px at 0% 100%, rgba(120, 80, 30, 0.16), transparent 70%),
    radial-gradient(ellipse 90px 70px at 100% 100%, rgba(120, 80, 30, 0.14), transparent 70%),
    #fbf3e2;
  border: 1px solid rgba(87, 64, 36, 0.34);
  box-shadow:
    0 24px 50px rgba(64, 45, 20, 0.20),
    0 10px 20px rgba(64, 45, 20, 0.10),
    inset 0 0 0 1px rgba(255, 252, 240, 0.55),
    inset 0 0 0 5px rgba(251, 243, 226, 1),
    inset 0 0 0 6px rgba(87, 64, 36, 0.28);
}
.detail-root::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none;
  z-index: 0;
}
.detail-root > * {
  position: relative;
  z-index: 1;
}

.header-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.header-crumbs {
  font-size: 12px;
  color: #6f5438;
  letter-spacing: 1px;
}
.crumb-sep {
  margin: 0 6px;
  color: rgba(87, 64, 36, 0.8);
}
.header-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}
.detail-title {
  font-size: 28px;
  font-weight: 700;
  color: #2a1a0e;
  letter-spacing: 2px;
  margin: 0;
  line-height: 1.2;
}
.badge {
  font-size: 10px;
  letter-spacing: 1px;
  padding: 2px 6px;
  font-family: 'Georgia', serif;
  font-weight: 700;
}
.badge.new {
  color: #3b2412;
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: rgba(243, 230, 203, 0.45);
}
.badge.hot {
  color: #c2410c;
  border: 1px solid rgba(194, 65, 12, 0.32);
  background: rgba(194, 65, 12, 0.06);
}
.detail-desc {
  font-size: 13px;
  line-height: 1.75;
  color: rgba(79, 57, 31, 0.85);
  margin: 0 0 14px;
}
.discovered-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding: 10px 14px;
  margin-bottom: 4px;
  background: rgba(180, 83, 9, 0.06);
  border-left: 3px solid #b45309;
  font-size: 12px;
  color: #5a3d28;
}
.discovered-tag {
  color: #b45309;
  font-weight: 700;
  letter-spacing: 1px;
}
.discovered-meta {
  color: rgba(90, 61, 40, 0.75);
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin: 18px 0 24px;
}
.metric-cell {
  padding: 16px 14px;
  border: 1px solid rgba(87, 64, 36, 0.22);
  background: rgba(251, 243, 226, 0.6);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
  text-align: center;
}
.metric-value {
  font-size: 20px;
  font-weight: 700;
  color: #2a1a0e;
  font-family: 'Georgia', v-bind("SERIF");
  line-height: 1.2;
  margin-bottom: 6px;
}
.metric-unit {
  font-size: 12px;
  color: #6f5438;
  font-weight: 400;
  margin-left: 3px;
}
.metric-label {
  font-size: 12px;
  color: #5a3d28;
  letter-spacing: 1px;
}

.req-sub + .req-sub {
  margin-top: 22px;
}
.sub-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-family: 'Georgia', serif;
  font-size: 12px;
  font-weight: 700;
  color: #3b2412;
  letter-spacing: 2px;
  margin: 0 0 12px;
}
.sub-label::before {
  content: '';
  width: 16px;
  height: 2px;
  background: #3b2412;
  flex-shrink: 0;
}
.sub-label::after {
  content: '';
  flex: 1;
  height: 1px;
  background: rgba(87, 64, 36, 0.22);
}
.sub-hint {
  font-size: 12px;
  color: rgba(87, 64, 36, 0.8);
  line-height: 1.7;
  margin: 0 0 12px;
  font-style: italic;
}

.gate-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.gate-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid rgba(87, 64, 36, 0.28);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.gate-key {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #6f5438;
  padding-right: 8px;
  border-right: 1px solid rgba(87, 64, 36, 0.2);
}
.gate-val {
  font-size: 13px;
  color: #2a1a0e;
  letter-spacing: 0.3px;
}

.acc-section {
  margin-bottom: 12px;
  border: 1px solid rgba(87, 64, 36, 0.26);
  background: rgba(252, 247, 235, 0.55);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
  transition: border-color 0.2s ease, background 0.2s ease;
}
.acc-section[open] {
  border-color: rgba(87, 64, 36, 0.36);
  background: rgba(252, 247, 235, 0.72);
}
.acc-header {
  list-style: none;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  cursor: pointer;
  user-select: none;
}
.acc-header::-webkit-details-marker {
  display: none;
}
.acc-header:hover {
  background: rgba(243, 230, 203, 0.32);
}
.acc-title {
  font-size: 16px;
  font-weight: 700;
  color: #2a1a0e;
  letter-spacing: 2px;
}
.acc-arrow {
  margin-left: auto;
  font-size: 14px;
  color: #5a3d28;
  line-height: 1;
  transition: transform 0.2s ease;
}
.acc-section[open] .acc-arrow {
  transform: rotate(180deg);
}
.acc-body {
  padding: 0 18px 18px;
}
.title-bar {
  width: 4px;
  height: 18px;
  background: #3b2412;
  flex-shrink: 0;
}
.section-note {
  font-size: 12px;
  color: rgba(87, 64, 36, 0.8);
  margin: 0 0 12px;
  font-style: italic;
}

.intro-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.intro-block {
  padding: 16px 18px;
  border: 1px solid rgba(87, 64, 36, 0.22);
  background: rgba(251, 243, 226, 0.55);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
}
.intro-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(87, 64, 36, 0.22);
}
.intro-caption {
  font-size: 13px;
  font-weight: 700;
  color: #2a1a0e;
  letter-spacing: 2px;
  padding-left: 10px;
  border-left: 3px solid #3b2412;
}
.duty-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.duty-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  font-size: 13px;
  line-height: 1.7;
  color: #2a1a0e;
}
.duty-num {
  flex-shrink: 0;
  font-family: 'Georgia', serif;
  font-size: 11px;
  font-weight: 700;
  color: #fbf3e2;
  background: #5a3d28;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 2px;
}
.duty-text {
  flex: 1;
  letter-spacing: 0.3px;
}
.scenario-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.scenario-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 12px;
  border: 1px solid rgba(87, 64, 36, 0.26);
  background: rgba(243, 230, 203, 0.32);
}
.scenario-name {
  font-size: 13px;
  font-weight: 700;
  color: #3b2412;
  letter-spacing: 1px;
}
.scenario-desc {
  font-size: 12px;
  line-height: 1.6;
  color: rgba(79, 57, 31, 0.85);
}
.intro-overview {
  font-size: 13px;
  line-height: 1.7;
  color: #3b2412;
  margin: 0 0 12px;
  padding: 10px 14px;
  border-left: 3px solid #b45309;
  background: rgba(243, 230, 203, 0.35);
  letter-spacing: 0.3px;
}
.intro-ai-badge {
  margin-left: auto;
  font-size: 11px;
  color: #b45309;
  letter-spacing: 1px;
  animation: pulse-soft 1.2s ease-in-out infinite;
}
.scenario-empty {
  font-size: 12px;
  color: rgba(87, 64, 36, 0.8);
  margin: 0;
  padding: 12px;
  font-style: italic;
}

.progression-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-bottom: 14px;
}
.level-col {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.level-head {
  display: flex;
  align-items: baseline;
  gap: 6px;
  flex-wrap: wrap;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(87, 64, 36, 0.22);
}
.level-mark {
  font-family: 'Georgia', v-bind("SERIF");
  font-size: 13px;
  font-weight: 700;
  color: #3b2412;
  padding: 1px 6px;
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: rgba(243, 230, 203, 0.45);
  letter-spacing: 1px;
}
.level-name {
  font-size: 14px;
  font-weight: 700;
  color: #2a1a0e;
  letter-spacing: 2px;
}
.level-sub {
  font-size: 11px;
  color: #6f5438;
  letter-spacing: 1px;
}
.level-pri {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 1px;
  padding: 1px 6px;
  border: 1px solid currentColor;
  background: rgba(251, 243, 226, 0.7);
}
.level-pri.pri-must { color: #7a2a22; }
.level-pri.pri-important { color: #b45309; }
.level-pri.pri-bonus { color: #6f5438; }
.level-chips {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.skill-chip {
  position: relative;
  font-size: 12px;
  padding: 7px 10px;
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: rgba(120, 80, 30, 0.13);
  color: #2a1a0e;
  letter-spacing: 0.5px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  line-height: 1.4;
  cursor: pointer;
  transition: filter 0.15s ease, transform 0.15s ease;
}
.skill-chip:hover {
  filter: brightness(1.04);
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.08);
}
.skill-chip.active {
  z-index: 30;
  border-color: rgba(87, 64, 36, 0.55);
}
.chip-top {
  display: flex;
  align-items: center;
  gap: 6px;
}
.chip-name {
  flex: 1;
  min-width: 0;
  font-weight: 700;
}
.trend-glyph {
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
}

.skill-pop {
  position: absolute;
  left: 0;
  bottom: calc(100% + 8px);
  width: min(320px, 100%);
  padding: 12px 14px;
  background:
    radial-gradient(ellipse 60px 40px at 0% 0%, rgba(120, 80, 30, 0.10), transparent 70%),
    radial-gradient(ellipse 60px 40px at 100% 100%, rgba(120, 80, 30, 0.10), transparent 70%),
    #fbf3e2;
  border: 1px solid rgba(87, 64, 36, 0.42);
  box-shadow:
    0 10px 26px rgba(64, 45, 20, 0.22),
    0 4px 10px rgba(64, 45, 20, 0.12),
    inset 0 0 0 1px rgba(255, 252, 240, 0.55);
  z-index: 40;
}
.skill-pop::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none;
}
.skill-pop::after {
  content: '';
  position: absolute;
  left: 20px;
  bottom: -6px;
  width: 11px;
  height: 11px;
  background: #fbf3e2;
  border-right: 1px solid rgba(87, 64, 36, 0.42);
  border-bottom: 1px solid rgba(87, 64, 36, 0.42);
  transform: rotate(45deg);
}
.skill-pop-head {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.skill-pop-name {
  font-size: 13px;
  font-weight: 700;
  color: #2a1a0e;
  letter-spacing: 0.5px;
}
.skill-pop-pri {
  flex-shrink: 0;
  font-size: 10px;
  padding: 2px 6px;
  border: 1px solid currentColor;
  letter-spacing: 0.5px;
  background: rgba(251, 243, 226, 0.7);
}
.skill-pop-pri.pri-must { color: #7a2a22; }
.skill-pop-pri.pri-important { color: #b45309; }
.skill-pop-pri.pri-bonus { color: #6f5438; }
.skill-pop-desc {
  position: relative;
  z-index: 1;
  margin: 0;
  font-size: 12px;
  line-height: 1.7;
  color: rgba(62, 40, 22, 0.82);
}
.skill-pop-enter-active,
.skill-pop-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.skill-pop-enter-from,
.skill-pop-leave-to {
  opacity: 0;
  transform: translateY(6px);
}

.skill-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin: 12px 0 0;
  font-size: 11px;
  color: rgba(87, 64, 36, 0.8);
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.legend-glyph {
  font-weight: 700;
}

.skill-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.evo-block {
  border: 1px solid rgba(87, 64, 36, 0.22);
  padding: 14px 16px;
  margin-bottom: 12px;
  background: rgba(251, 243, 226, 0.55);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
}
.evo-period {
  font-size: 15px;
  font-weight: 700;
  color: #2a1a0e;
  letter-spacing: 2px;
  margin-bottom: 10px;
  padding-bottom: 6px;
  border-bottom: 1px dashed rgba(87, 64, 36, 0.22);
}
.evo-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 18px;
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px dashed rgba(87, 64, 36, 0.18);
  font-size: 12px;
  line-height: 1.6;
  color: rgba(90, 61, 40, 0.8);
}
.evo-meta-item {
  display: inline-flex;
  align-items: baseline;
  gap: 6px;
}
.meta-label {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #3b2412;
  padding: 1px 6px;
  border: 1px solid rgba(87, 64, 36, 0.28);
  background: rgba(243, 230, 203, 0.45);
  white-space: nowrap;
}
.evo-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.evo-row:last-child {
  margin-bottom: 0;
}
.evo-mark {
  font-size: 11px;
  letter-spacing: 1px;
  padding: 2px 8px;
  border: 1px solid currentColor;
  min-width: 64px;
  text-align: center;
}
.evo-mark.add { color: #b45309; }
.evo-mark.remove { color: #6b7280; }
.evo-mark.up { color: #059669; }
.evo-mark.down { color: #dc2626; }
.evo-chip {
  font-size: 12px;
  padding: 3px 8px;
  border: 1px solid rgba(87, 64, 36, 0.28);
  background: rgba(251, 243, 226, 0.6);
  color: #5a3d28;
}
.evo-chip.add { border-color: rgba(180, 83, 9, 0.4); color: #b45309; background: rgba(180, 83, 9, 0.05); }
.evo-chip.remove { color: #6b7280; text-decoration: line-through; background: rgba(107, 114, 128, 0.05); border-color: rgba(107, 114, 128, 0.35); }
.evo-chip.up { border-color: rgba(5, 150, 105, 0.4); color: #047857; background: rgba(5, 150, 105, 0.05); }
.evo-chip.down { border-color: rgba(220, 38, 38, 0.4); color: #b91c1c; background: rgba(220, 38, 38, 0.05); }

.city-list {
  padding: 14px 16px;
  border: 1px solid rgba(87, 64, 36, 0.22);
  background: rgba(251, 243, 226, 0.55);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
}
.city-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.city-row:last-child {
  margin-bottom: 0;
}
.city-name {
  flex: 0 0 64px;
  font-size: 13px;
  color: #2a1a0e;
  letter-spacing: 1px;
  white-space: nowrap;
}
.city-bar-track {
  flex: 0 0 150px;
  height: 8px;
  background: rgba(243, 230, 203, 0.6);
  border: 1px solid rgba(87, 64, 36, 0.22);
  position: relative;
  overflow: hidden;
}
.city-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b2412, #5a3d28);
}
.city-count {
  margin-left: auto;
  font-size: 12px;
  color: #5a3d28;
  text-align: right;
  font-family: 'Georgia', serif;
  white-space: nowrap;
}

.soft-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.soft-chip {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 12px;
  border: 1px solid rgba(87, 64, 36, 0.28);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.5);
  max-width: 260px;
}
.soft-name {
  font-size: 12px;
  font-weight: 700;
  color: #3b2412;
  letter-spacing: 0.5px;
}
.soft-desc {
  font-size: 11px;
  line-height: 1.5;
  color: rgba(79, 57, 31, 0.85);
}

.path-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.path-step {
  display: grid;
  grid-template-columns: 64px 1fr;
  gap: 6px 14px;
  align-items: baseline;
  padding: 12px 14px;
  border: 1px solid rgba(87, 64, 36, 0.22);
  background: rgba(251, 243, 226, 0.55);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
}
.path-stage {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 1px;
  color: #3b2412;
  padding: 2px 8px;
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: rgba(243, 230, 203, 0.45);
  text-align: center;
}
.path-title {
  font-size: 13px;
  font-weight: 700;
  color: #2a1a0e;
  letter-spacing: 1px;
}
.path-desc {
  grid-column: 2;
  font-size: 12px;
  line-height: 1.6;
  color: rgba(79, 57, 31, 0.85);
}

.outlook-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.outlook-cell {
  padding: 14px 16px;
  border: 1px solid rgba(87, 64, 36, 0.22);
  background: rgba(251, 243, 226, 0.55);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
}
.outlook-caption {
  display: block;
  font-size: 12px;
  font-weight: 700;
  color: #3b2412;
  letter-spacing: 2px;
  padding-left: 10px;
  border-left: 3px solid #3b2412;
  margin-bottom: 8px;
}
.outlook-text {
  font-size: 13px;
  line-height: 1.7;
  color: #2a1a0e;
  letter-spacing: 0.3px;
  margin: 0;
}

.adj-group {
  margin-bottom: 14px;
}
.adj-head {
  margin-bottom: 8px;
}
.adj-mark {
  font-size: 11px;
  letter-spacing: 1px;
  padding: 2px 8px;
  border: 1px solid currentColor;
}
.adj-mark.similar { color: #3b2412; }
.adj-mark.transfer { color: #5a3d28; }
.adj-mark.advanced { color: #b45309; }
.adj-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.adj-chip {
  font-family: v-bind("SERIF");
  font-size: 13px;
  padding: 5px 12px;
  border: 1px solid rgba(87, 64, 36, 0.32);
  background: rgba(251, 243, 226, 0.55);
  color: #3b2412;
  cursor: pointer;
  letter-spacing: 0.5px;
  transition: all 0.2s ease;
}
.adj-chip:hover:not(:disabled) {
  background: #3b2412;
  color: #fbf3e2;
  border-color: #2a1a0e;
}
.adj-chip:disabled {
  cursor: default;
  opacity: 0.55;
}
.adj-chip.similar { border-left: 3px solid #3b2412; }
.adj-chip.transfer { border-left: 3px solid #5a3d28; }
.adj-chip.advanced { border-left: 3px solid #b45309; }

@media (max-width: 768px) {
  .detail-root {
    padding: 18px 16px 24px;
  }
  .soft-chip {
    max-width: none;
  }
  .detail-title {
    font-size: 22px;
    letter-spacing: 1px;
  }
  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }
  .metric-value {
    font-size: 16px;
  }
  .city-row {
    gap: 8px;
  }
  .city-name {
    flex-basis: 48px;
  }
  .city-bar-track {
    flex-basis: 110px;
  }
  .progression-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }
  .skill-chip {
    font-size: 13px;
  }
  .intro-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .soft-grid {
    grid-template-columns: 1fr;
  }
  .outlook-grid {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  .path-step {
    grid-template-columns: 1fr;
  }
  .path-desc {
    grid-column: 1;
  }
}

@keyframes pulse-soft {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.45; }
}
</style>

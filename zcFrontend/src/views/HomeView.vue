<template>
  <div class="home-page">
    <!-- 浮动职业名背景 -->
    <div class="careers-layer">
      <div v-for="(item, index) in floatingCareers" :key="index" class="career-drift" :style="item.driftStyle">
        <span class="career-word" :style="item.wordStyle">{{ item.name }}</span>
      </div>
    </div>

    <div class="home-scroll">
      <!-- ===== 1. 主卡片：轮播图 + TOP5 ===== -->
      <div class="home-card">
        <div class="carousel-col">
          <el-carousel class="home-carousel" height="100%" :interval="4600" arrow="hover">
            <el-carousel-item>
              <div class="slide-surface">
                <svg class="slide-art" viewBox="0 0 240 150" fill="none" aria-hidden="true">
                  <defs>
                    <pattern id="s1hatch" width="4" height="4" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
                      <line x1="0" y1="0" x2="0" y2="4" stroke="#3b2412" stroke-width="0.8" opacity="0.22"/>
                    </pattern>
                  </defs>
                  <line x1="22" y1="130" x2="218" y2="130" stroke="#3b2412" stroke-width="1" stroke-dasharray="2 4" opacity="0.3"/>
                  <rect x="34" y="96" width="20" height="34" fill="url(#s1hatch)" stroke="#3b2412" stroke-width="1.2"/>
                  <rect x="62" y="74" width="20" height="56" fill="url(#s1hatch)" stroke="#3b2412" stroke-width="1.2"/>
                  <rect x="90" y="88" width="20" height="42" fill="url(#s1hatch)" stroke="#3b2412" stroke-width="1.2"/>
                  <rect x="118" y="58" width="20" height="72" fill="url(#s1hatch)" stroke="#3b2412" stroke-width="1.2"/>
                  <rect x="146" y="70" width="20" height="60" fill="url(#s1hatch)" stroke="#3b2412" stroke-width="1.2"/>
                  <path d="M30 102 C 78 78, 126 64, 214 30" stroke="#3b2412" stroke-width="2" stroke-linecap="round"/>
                  <path d="M214 30 l-10 2.6 M214 30 l-2.6 10" stroke="#3b2412" stroke-width="1.3" stroke-linecap="round"/>
                  <circle cx="198" cy="118" r="13" stroke="#3b2412" stroke-width="1.2" opacity="0.5"/>
                  <circle cx="198" cy="118" r="5.5" stroke="#3b2412" stroke-width="1" opacity="0.7"/>
                  <path d="M198 101 v-6 M198 135 v6 M181 118 h-6 M215 118 h6" stroke="#3b2412" stroke-width="1" opacity="0.6" stroke-linecap="round"/>
                </svg>
                <span class="slide-eyebrow">Data · Insight</span>
                <span class="slide-title">数据驱动 · 职业洞察</span>
                <span class="slide-rule"></span>
                <span class="slide-sub">多源数据采集与智能分析</span>
                <svg class="slide-frame" viewBox="0 0 240 150" preserveAspectRatio="none" aria-hidden="true">
                  <rect x="10" y="8" width="220" height="134" fill="none" stroke="#3b2412" stroke-opacity="0.30" stroke-width="1"/>
                  <rect x="15" y="13" width="210" height="124" fill="none" stroke="#3b2412" stroke-opacity="0.15" stroke-width="0.6"/>
                  <rect x="19" y="17" width="4" height="4" transform="rotate(45 21 19)" fill="#3b2412" fill-opacity="0.5"/>
                  <rect x="217" y="17" width="4" height="4" transform="rotate(45 219 19)" fill="#3b2412" fill-opacity="0.5"/>
                  <rect x="19" y="129" width="4" height="4" transform="rotate(45 21 131)" fill="#3b2412" fill-opacity="0.5"/>
                  <rect x="217" y="129" width="4" height="4" transform="rotate(45 219 131)" fill="#3b2412" fill-opacity="0.5"/>
                </svg>
              </div>
            </el-carousel-item>
            <el-carousel-item>
              <div class="slide-surface">
                <svg class="slide-art" viewBox="0 0 240 150" fill="none" aria-hidden="true">
                  <defs>
                    <pattern id="s2hatch" width="4" height="4" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
                      <line x1="0" y1="0" x2="0" y2="4" stroke="#3b2412" stroke-width="0.8" opacity="0.22"/>
                    </pattern>
                  </defs>
                  <circle cx="120" cy="72" r="40" stroke="#3b2412" stroke-opacity="0.18" stroke-dasharray="2 4" stroke-width="1"/>
                  <circle cx="120" cy="72" r="64" stroke="#3b2412" stroke-opacity="0.12" stroke-dasharray="2 4" stroke-width="1"/>
                  <g stroke="#3b2412" stroke-width="0.9" opacity="0.5">
                    <line x1="120" y1="72" x2="160" y2="72"/>
                    <line x1="120" y1="72" x2="140" y2="106"/>
                    <line x1="120" y1="72" x2="100" y2="106"/>
                    <line x1="120" y1="72" x2="80" y2="72"/>
                    <line x1="120" y1="72" x2="100" y2="37"/>
                    <line x1="120" y1="72" x2="140" y2="37"/>
                  </g>
                  <g stroke="#3b2412" stroke-width="0.6" opacity="0.28">
                    <line x1="160" y1="72" x2="140" y2="106"/>
                    <line x1="100" y1="106" x2="80" y2="72"/>
                    <line x1="80" y1="72" x2="100" y2="37"/>
                    <line x1="140" y1="37" x2="160" y2="72"/>
                  </g>
                  <g fill="url(#s2hatch)" stroke="#3b2412" stroke-width="1.2">
                    <rect x="156" y="68" width="8" height="8" transform="rotate(45 160 72)"/>
                    <rect x="136" y="102" width="8" height="8" transform="rotate(45 140 106)"/>
                    <rect x="96" y="102" width="8" height="8" transform="rotate(45 100 106)"/>
                    <rect x="76" y="68" width="8" height="8" transform="rotate(45 80 72)"/>
                    <rect x="96" y="33" width="8" height="8" transform="rotate(45 100 37)"/>
                    <rect x="136" y="33" width="8" height="8" transform="rotate(45 140 37)"/>
                  </g>
                  <g stroke="#3b2412" stroke-width="0.7" opacity="0.4">
                    <line x1="160" y1="72" x2="168" y2="32"/>
                    <line x1="80" y1="72" x2="72" y2="32"/>
                    <line x1="100" y1="106" x2="74" y2="120"/>
                    <line x1="140" y1="106" x2="166" y2="120"/>
                  </g>
                  <g fill="#3b2412" fill-opacity="0.6">
                    <circle cx="168" cy="32" r="4"/>
                    <circle cx="72" cy="32" r="4"/>
                    <circle cx="74" cy="120" r="4"/>
                    <circle cx="166" cy="120" r="4"/>
                  </g>
                  <circle cx="120" cy="72" r="13" stroke="#3b2412" stroke-width="2"/>
                  <circle cx="120" cy="72" r="4.5" fill="#3b2412"/>
                </svg>
                <span class="slide-eyebrow">Knowledge · Graph</span>
                <span class="slide-title">知识图谱 · 全景构建</span>
                <span class="slide-rule"></span>
                <span class="slide-sub">岗位技能关系网络可视化</span>
                <svg class="slide-frame" viewBox="0 0 240 150" preserveAspectRatio="none" aria-hidden="true">
                  <rect x="10" y="8" width="220" height="134" fill="none" stroke="#3b2412" stroke-opacity="0.30" stroke-width="1"/>
                  <rect x="15" y="13" width="210" height="124" fill="none" stroke="#3b2412" stroke-opacity="0.15" stroke-width="0.6"/>
                  <rect x="19" y="17" width="4" height="4" transform="rotate(45 21 19)" fill="#3b2412" fill-opacity="0.5"/>
                  <rect x="217" y="17" width="4" height="4" transform="rotate(45 219 19)" fill="#3b2412" fill-opacity="0.5"/>
                  <rect x="19" y="129" width="4" height="4" transform="rotate(45 21 131)" fill="#3b2412" fill-opacity="0.5"/>
                  <rect x="217" y="129" width="4" height="4" transform="rotate(45 219 131)" fill="#3b2412" fill-opacity="0.5"/>
                </svg>
              </div>
            </el-carousel-item>
            <el-carousel-item>
              <div class="slide-surface">
                <svg class="slide-art" viewBox="0 0 240 150" fill="none" aria-hidden="true">
                  <defs>
                    <pattern id="s3hatch" width="4" height="4" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
                      <line x1="0" y1="0" x2="0" y2="4" stroke="#3b2412" stroke-width="0.8" opacity="0.22"/>
                    </pattern>
                  </defs>
                  <circle cx="98" cy="72" r="44" stroke="#3b2412" stroke-width="1.6" opacity="0.62"/>
                  <circle cx="142" cy="72" r="44" stroke="#3b2412" stroke-width="1.6" opacity="0.62"/>
                  <ellipse cx="120" cy="72" rx="13" ry="37" fill="url(#s3hatch)" opacity="0.9"/>
                  <circle cx="120" cy="72" r="21" stroke="#3b2412" stroke-dasharray="3 4" opacity="0.4" stroke-width="1"/>
                  <text x="80" y="79" font-family="'SimSun','Songti SC',serif" font-size="15" fill="#3b2412" opacity="0.7">人</text>
                  <text x="150" y="79" font-family="'SimSun','Songti SC',serif" font-size="15" fill="#3b2412" opacity="0.7">岗</text>
                  <path d="M120 63 L122 70 129 72 L122 74 120 81 L118 74 111 72 L118 70 Z" fill="#3b2412"/>
                </svg>
                <span class="slide-eyebrow">Matching · Recommend</span>
                <span class="slide-title">人岗匹配 · 精准推荐</span>
                <span class="slide-rule"></span>
                <span class="slide-sub">AI 驱动的个性化职业规划</span>
                <svg class="slide-frame" viewBox="0 0 240 150" preserveAspectRatio="none" aria-hidden="true">
                  <rect x="10" y="8" width="220" height="134" fill="none" stroke="#3b2412" stroke-opacity="0.30" stroke-width="1"/>
                  <rect x="15" y="13" width="210" height="124" fill="none" stroke="#3b2412" stroke-opacity="0.15" stroke-width="0.6"/>
                  <rect x="19" y="17" width="4" height="4" transform="rotate(45 21 19)" fill="#3b2412" fill-opacity="0.5"/>
                  <rect x="217" y="17" width="4" height="4" transform="rotate(45 219 19)" fill="#3b2412" fill-opacity="0.5"/>
                  <rect x="19" y="129" width="4" height="4" transform="rotate(45 21 131)" fill="#3b2412" fill-opacity="0.5"/>
                  <rect x="217" y="129" width="4" height="4" transform="rotate(45 219 131)" fill="#3b2412" fill-opacity="0.5"/>
                </svg>
              </div>
            </el-carousel-item>
          </el-carousel>
        </div>

        <div class="col-divider"></div>

        <div class="jobs-col">
          <div class="jobs-header">
            <h2 class="jobs-title">热门岗位</h2>
            <span class="jobs-badge">TOP 5</span>
          </div>
          <div class="jobs-list">
            <div v-for="(job, index) in top5Jobs" :key="job.id" class="job-row" @click="goToJobDetail(job)">
              <span class="job-rank" :class="{ gold: index === 0, silver: index === 1, bronze: index === 2 }">{{ index + 1 }}</span>
              <div class="job-left">
                <span class="job-name">{{ job.name }}</span>
                <span class="job-cat">{{ getCategoryName(job.categoryId) }}</span>
              </div>
              <span v-if="job.trend" class="job-trend" :class="job.trend">{{ trendGlyph(job.trend) }}</span>
              <span class="job-hot">{{ countText(job.hotScore) }}</span>
            </div>
          </div>
          <button class="view-all" @click="router.push('/jobs')">
            查看全部岗位 <span class="va-arrow">→</span>
          </button>
        </div>
      </div>

      <!-- ===== 2. 新岗位发现 + 新兴技术栈 ===== -->
      <div class="bottom-row">
        <!-- 新岗位发现 -->
        <section class="section-card discovery-card">
          <div class="section-head">
            <div class="section-head-left">
              <IconEpOpportunity class="section-icon" />
              <h2 class="section-title">新岗位发现</h2>
            </div>
            <span class="section-hint">AI 驱动的多源数据挖掘</span>
          </div>
          <div class="section-divider"></div>
          <div class="discovery-list">
            <div v-for="d in discoveries" :key="d.jobName" class="discovery-item" @click="goToDiscovery(d.jobId)">
              <div class="disc-head">
                <span class="disc-name">{{ d.jobName }}</span>
                <span class="disc-conf">{{ Math.round(d.confidence * 100) }}%</span>
              </div>
              <div class="disc-foot">
                <span class="disc-date">{{ d.date }}</span>
                <span class="disc-go">查看岗位 →</span>
              </div>
            </div>
          </div>
        </section>

        <!-- 新兴技术栈 -->
        <section class="section-card tech-stack-card">
          <div class="section-head">
            <div class="section-head-left">
              <IconEpCpu class="section-icon" />
              <h2 class="section-title">新兴技术栈</h2>
            </div>
            <span class="section-hint">AI 领域前沿技术动向</span>
          </div>
          <div class="section-divider"></div>
          <div class="tech-grid">
            <div
              v-for="(tech, i) in techStacks"
              :key="tech.name"
              class="tech-item"
              :class="{ active: activeTech === tech.name }"
              @click="toggleTech(tech.name)"
            >
              <span class="tech-seal">{{ String(i + 1).padStart(2, '0') }}</span>
              <div class="tech-info">
                <span class="tech-name">{{ tech.name }}</span>
                <span class="tech-desc">{{ tech.desc }}</span>
              </div>
              <span class="tech-tag" :class="tech.level">{{ tech.level }}</span>

              <transition name="tech-pop">
                <div v-if="activeTech === tech.name" class="tech-pop" @click.stop>
                  <div class="tech-pop-head">
                    <span class="tech-pop-title">{{ tech.name }}</span>
                    <span class="tech-pop-level">{{ tech.level }}</span>
                  </div>
                  <p class="tech-pop-intro">{{ tech.intro }}</p>
                </div>
              </transition>
            </div>
          </div>
        </section>
      </div>

      <footer class="home-footer">
        <span>© 2026 职引未来</span>
      </footer>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { jobCategories, careerNames, countText, trendGlyph } from '@/models'
import type { JobItem } from '@/models'
import { services } from '@/services'
import type { DiscoveryLogItem } from '@/services'

const router = useRouter()

const floatingCareers = (() => {
  const items: any[] = []
  for (let r = 0; r < 3; r++) {
    for (const name of careerNames) {
      items.push({
        name,
        driftStyle: {
          top: `${Math.random() * 94 + 3}%`,
          animation: `${Math.random() > 0.5 ? 'drift-left' : 'drift-right'} ${30 + Math.random() * 40}s ${-(Math.random() * 40)}s linear infinite`
        },
        wordStyle: { fontSize: `${11 + Math.random() * 8}px`, opacity: 0.22 + Math.random() * 0.14 }
      })
    }
  }
  return items
})()

const top5Jobs = ref<JobItem[]>([])
const discoveries = ref<DiscoveryLogItem[]>([])
const activeTech = ref<string | null>(null)

const techStacks = [
  {
    name: 'Large Language Model',
    desc: 'GPT-4o / Claude / DeepSeek / Qwen 等大模型驱动的智能应用',
    level: '核心',
    intro: '以大规模预训练语言模型为底座，GPT-4o、Claude、DeepSeek、Qwen 等在文本生成、推理与代码等任务上表现突出。它是当前 AI 岗位最核心的能力方向，广泛用于智能客服、内容创作、代码助手与行业知识问答。',
  },
  {
    name: 'RAG 检索增强生成',
    desc: 'LangChain / LlamaIndex 搭配向量数据库实现知识增强',
    level: '核心',
    intro: '检索增强生成通过「先检索、后生成」把外部知识库接入大模型，显著降低幻觉并让回答可溯源。典型组合为 LangChain / LlamaIndex 编排 + 向量数据库，是企业落地大模型的主流范式。',
  },
  {
    name: 'LoRA / QLoRA 微调',
    desc: '低秩适配高效微调大模型，显著降低算力与存储成本',
    level: '热门',
    intro: '低秩适配在冻结基座模型的前提下仅训练少量参数，即可让通用模型适配垂直场景；QLoRA 再结合 4-bit 量化，大幅降低显存与成本，是中小团队做领域微调的主流手段。',
  },
  {
    name: 'AI Agent 智能体',
    desc: 'AutoGPT / CrewAI / Coze 等多代理协作与自主决策框架',
    level: '热门',
    intro: 'AI Agent 让大模型具备「规划—调用工具—反思」的自主行动能力，可完成多步骤复杂任务。AutoGPT、CrewAI、Coze 等框架支持多代理协作，是下一代 AI 应用的重要形态。',
  },
  {
    name: '向量数据库',
    desc: 'Milvus / Pinecone / Weaviate 支撑语义搜索与知识检索',
    level: '热门',
    intro: '向量数据库以高维向量相似度检索为核心，为大模型提供长时记忆与语义搜索能力，是 RAG 与推荐系统的关键基础设施。Milvus、Pinecone、Weaviate 等支撑海量向量的高性能存储与检索。',
  },
]

function getCategoryName(catId: string): string {
  return jobCategories.find(c => c.id === catId)?.name || ''
}

function goToJobDetail(job: JobItem) {
  router.push({ path: '/jobs', query: { highlight: job.id } })
}

function goToDiscovery(jobId?: string) {
  if (!jobId) return
  router.push({ path: '/jobs', query: { highlight: jobId } })
}

function toggleTech(name: string) {
  activeTech.value = activeTech.value === name ? null : name
}

function onDocClick(e: MouseEvent) {
  if (!(e.target as HTMLElement).closest('.tech-item')) {
    activeTech.value = null
  }
}

onMounted(async () => {
  document.addEventListener('click', onDocClick)
  try {
    const [hot, logs] = await Promise.all([services.getHotJobs(), services.getDiscoveryLog()])
    top5Jobs.value = hot.slice(0, 5)
    discoveries.value = logs
  } catch {
    /* 后端未就绪时保持空态，页面其余部分仍可浏览 */
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
.home-page {
  min-height: calc(100vh - 56px);
  position: relative;
  overflow: hidden;
}

/* ===== 浮动背景 ===== */
.careers-layer { position: fixed; inset: 0; overflow: hidden; z-index: 0; pointer-events: none; }
.career-drift { position: absolute; white-space: nowrap; will-change: transform; }
.career-word {
  display: inline-block;
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
  color: #1a1a1a;
  padding: 2px 6px;
}

.home-scroll {
  position: relative;
  z-index: 1;
  max-width: 1140px;
  margin: 0 auto;
  padding: 32px 24px 24px;
}

/* ================================================================
   1. 主卡片：轮播图 + TOP5
   ================================================================ */
.home-card {
  display: flex;
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
  animation: card-rise 0.6s cubic-bezier(0.22, 1, 0.36, 1) both;
  overflow: hidden;
}

.home-card::after {
  content: '';
  position: absolute; inset: 0;
  background: repeating-linear-gradient(0deg, transparent, transparent 36px, rgba(87,64,36,0.008) 36px, rgba(87,64,36,0.008) 37px);
  pointer-events: none; z-index: 0;
}

/* 左：轮播 */
.carousel-col {
  flex: 0 0 57%;
  min-width: 0;
  padding: 30px 26px 28px 30px;
  display: flex;
  position: relative; z-index: 1;
}

.home-carousel { flex: 1; min-width: 0; }
.home-carousel :deep(.el-carousel__container) { height: 100%; }
.home-carousel :deep(.el-carousel__arrow) {
  width: 28px; height: 28px;
  background: rgba(59,36,18,0.45);
}
.home-carousel :deep(.el-carousel__arrow:hover) { background: #3b2412; }
.home-carousel :deep(.el-carousel__indicators) { bottom: 10px; }
.home-carousel :deep(.el-carousel__button) {
  width: 22px; height: 3px;
  background: rgba(87,64,36,0.35);
}
.home-carousel :deep(.is-active .el-carousel__button) { background: #3b2412; }

.slide-surface {
  position: relative;
  width: 100%; height: 100%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  background:
    radial-gradient(ellipse 70px 50px at 0% 0%, rgba(120,80,30,0.12), transparent 70%),
    radial-gradient(ellipse 70px 50px at 100% 100%, rgba(120,80,30,0.12), transparent 70%),
    linear-gradient(140deg, #f8eed9 0%, #f3e6cb 100%);
  border: 1px solid rgba(87,64,36,0.26);
  box-shadow:
    inset 0 0 0 1px rgba(255,252,240,0.5),
    inset 0 0 0 4px rgba(251,243,226,0.9),
    inset 0 0 0 5px rgba(87,64,36,0.16);
  overflow: hidden;
}
.slide-surface::before {
  content: '';
  position: absolute; inset: 0;
  background:
    repeating-linear-gradient(0deg, rgba(87,64,36,0.012) 0 1px, transparent 1px 4px),
    repeating-linear-gradient(90deg, rgba(87,64,36,0.012) 0 1px, transparent 1px 4px);
  pointer-events: none;
}

.slide-art { width: 232px; height: auto; margin-bottom: 6px; position: relative; z-index: 1; }
.slide-eyebrow {
  font-family: 'Georgia', 'SimSun', serif;
  font-size: 9px; letter-spacing: 3.5px; color: rgba(87,64,36,0.55);
  text-transform: uppercase;
  position: relative; z-index: 4;
}
.slide-title {
  font-family: 'SimSun','Songti SC','STSong','Noto Serif SC',serif;
  font-size: 18px; font-weight: 700; letter-spacing: 4px; color: #2a1a0e;
  margin-top: 5px;
  position: relative; z-index: 4;
}
.slide-rule {
  position: relative; z-index: 4;
  width: 30px; height: 1px; margin: 8px 0 5px;
  background: linear-gradient(90deg, transparent, rgba(87,64,36,0.4), transparent);
}
.slide-rule::after {
  content: ''; position: absolute; left: 50%; top: 50%;
  width: 5px; height: 5px; transform: translate(-50%,-50%) rotate(45deg);
  background: rgba(87,64,36,0.4);
}
.slide-sub {
  font-family: 'SimSun','Songti SC',serif;
  font-size: 11px; letter-spacing: 1.8px; color: rgba(87,64,36,0.55);
  position: relative; z-index: 4;
}
.slide-frame {
  position: absolute; inset: 0; width: 100%; height: 100%;
  z-index: 2; pointer-events: none;
}
/* 分隔 */
.col-divider {
  width: 1px;
  background: linear-gradient(180deg, transparent 8%, rgba(87,64,36,0.1) 25%, rgba(87,64,36,0.1) 75%, transparent 92%);
  flex-shrink: 0;
}

/* 右：TOP5 */
.jobs-col {
  flex: 1 1 0; min-width: 0; padding: 30px 26px 28px;
  display: flex; flex-direction: column;
  position: relative; z-index: 1;
}
.jobs-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 18px;
}
.jobs-title {
  font-family: 'SimSun','Songti SC','STSong','Noto Serif SC',serif;
  font-size: 17px; font-weight: 700; color: #2a1a0e; letter-spacing: 3px; margin: 0;
}
.jobs-badge {
  font-family: 'Georgia',serif; font-size: 10px; letter-spacing: 2px; color: #3b2412;
  padding: 3px 9px; border: 1px solid rgba(87,64,36,0.32); background: rgba(243,230,203,0.4);
}
.jobs-list { flex: 1; }

.job-row {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 0; border-bottom: 1px solid rgba(87,64,36,0.14);
  cursor: pointer; transition: all 0.2s ease; position: relative;
}
.job-row:last-child { border-bottom: none; }
.job-row:hover { padding-left: 6px; background: rgba(87,64,36,0.015); }
.job-row::before {
  content: ''; position: absolute; left: -2px; top: 50%;
  transform: translateY(-50%); width: 0; height: 1px;
  background: #3b2412; transition: width 0.2s ease;
}
.job-row:hover::before { width: 12px; }

.job-rank {
  width: 22px; height: 22px; display: flex; align-items: center; justify-content: center;
  font-size: 10px; font-weight: 700; background: #e8e0d0; color: #5a3d28;
  border: 1px solid rgba(87,64,36,0.22); border-radius: 2px; flex-shrink: 0; font-family: 'Georgia',serif;
}
.job-rank.gold { background: #3b2412; color: #fbf3e2; border-color: #2a1a0e; }
.job-rank.silver { background: #6b5538; color: #fbf3e2; border-color: #4c3a26; }
.job-rank.bronze { background: #967a55; color: #fbf3e2; border-color: #6f5a3e; }

.job-left {
  flex: 1; min-width: 0;
  display: flex; align-items: baseline; gap: 8px;
}
.job-name {
  font-size: 14px; font-weight: 600; color: #1a1a1a;
  font-family: 'SimSun','Songti SC',serif; letter-spacing: 0.5px;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.job-cat {
  font-size: 11px; color: rgba(87,64,36,0.5);
  flex-shrink: 0; white-space: nowrap;
}
.job-trend { font-size: 12px; flex-shrink: 0; width: 16px; text-align: center; }
.job-trend.up { color: #10b981; }
.job-trend.down { color: #ef4444; }
.job-trend.stable { color: rgba(87,64,36,0.5); }
.job-hot {
  width: 30px; height: 20px; display: flex; align-items: center; justify-content: center;
  background: rgba(87,64,36,0.06); border: 1px solid rgba(87,64,36,0.18);
  font-size: 10px; font-weight: 700;
  color: #5a3d28; font-family: 'Georgia',serif; flex-shrink: 0;
}

.view-all {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 6px 14px; border: 1px solid rgba(87,64,36,0.32); background: rgba(243,230,203,0.4);
  font-family: 'SimSun','Songti SC',serif; font-size: 12px;
  color: #3b2412; letter-spacing: 1px; cursor: pointer;
  margin-top: 18px; transition: background 0.2s, color 0.2s, border-color 0.2s; align-self: flex-start;
  box-shadow: inset 0 0 0 1px rgba(255,252,240,0.4);
}
.view-all:hover { background: #3b2412; color: #fbf3e2; border-color: #2a1a0e; }
.va-arrow { transition: transform 0.2s; font-size: 11px; }
.view-all:hover .va-arrow { transform: translateX(3px); }

/* ================================================================
   通用 Section 样式
   ================================================================ */
.section-card {
  position: relative;
  display: flex;
  flex-direction: column;
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
  padding: 24px 28px;
  animation: card-rise 0.5s cubic-bezier(0.22,1,0.36,1) 0.15s both;
}
.section-card::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none; z-index: 0;
}

.section-head {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 14px;
}
.section-head-left { display: flex; align-items: center; gap: 8px; }
.section-icon { font-size: 16px; color: #3b2412; opacity: 0.7; }
.section-title {
  font-family: 'SimSun','Songti SC','STSong','Noto Serif SC',serif;
  font-size: 15px; font-weight: 700; color: #2a1a0e;
  letter-spacing: 2px; margin: 0;
}
.section-hint {
  font-size: 11px; color: rgba(87,64,36,0.55); font-family: 'SimSun','Songti SC',serif;
  letter-spacing: 0.5px;
}
.section-divider {
  height: 1px;
  background: linear-gradient(90deg, rgba(87,64,36,0.22), rgba(87,64,36,0.06), transparent);
  margin-bottom: 16px;
}

/* ================================================================
   2. 底部双栏：新岗位发现 + 新兴技术栈
   ================================================================ */
.bottom-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  margin-top: 24px;
  align-items: stretch;
}

/* 新岗位发现 */
.discovery-list {
  display: flex; flex-direction: column; gap: 12px;
  flex: 1; justify-content: space-between;
}

.discovery-item {
  padding: 10px 12px;
  border: 1px solid rgba(87,64,36,0.42);
  background: rgba(252,247,235,0.9);
  box-shadow: 0 2px 8px rgba(64,45,20,0.12), inset 0 0 0 1px rgba(255,252,240,0.5);
  transition: border-color 0.2s, background 0.2s;
  cursor: pointer;
}
.discovery-item:hover { border-color: rgba(87,64,36,0.55); background: rgba(248,240,222,0.92); }
.discovery-item:hover .disc-go { color: #3b2412; border-color: rgba(87,64,36,0.42); }

.disc-foot {
  display: flex; align-items: center; justify-content: space-between;
  margin-top: 2px;
}
.disc-go {
  font-size: 10px; color: rgba(87,64,36,0.55);
  border: 1px solid rgba(87,64,36,0.22);
  padding: 1px 6px; font-family: 'SimSun','Songti SC',serif;
  letter-spacing: 0.5px; transition: color 0.2s, border-color 0.2s;
}

.disc-head {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px;
}
.disc-name {
  font-size: 13px; font-weight: 600; color: #2a1a0e;
  font-family: 'SimSun','Songti SC',serif; letter-spacing: 0.5px;
}
.disc-conf {
  font-size: 11px; font-weight: 700; color: #10b981;
  font-family: 'Georgia',serif;
}
.disc-date {
  font-size: 10px; color: rgba(87,64,36,0.5);
}

/* 新兴技术栈 */
.tech-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex: 1; justify-content: space-between;
}

.tech-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 10px;
  border: 1px solid rgba(87,64,36,0.42);
  background: rgba(252,247,235,0.9);
  box-shadow: 0 2px 8px rgba(64,45,20,0.12), inset 0 0 0 1px rgba(255,252,240,0.5);
  transition: all 0.2s;
  cursor: pointer;
}
.tech-item:hover {
  border-color: rgba(87,64,36,0.55);
  background: rgba(248,240,222,0.92);
}
.tech-item.active {
  z-index: 30;
  border-color: rgba(87,64,36,0.6);
  background: rgba(248,240,222,0.92);
}

.tech-seal {
  flex-shrink: 0;
  width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Georgia', 'SimSun', serif;
  font-size: 13px; font-weight: 700; letter-spacing: 0.5px;
  color: #3b2412;
  border: 1px solid rgba(87, 64, 36, 0.5);
  background: linear-gradient(145deg, rgba(249,241,221,0.95), rgba(238,222,192,0.9));
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.55);
}

.tech-info {
  flex: 1;
  display: flex; flex-direction: column; gap: 2px;
  min-width: 0;
}

.tech-name {
  font-size: 12px; font-weight: 600; color: #2a1a0e;
  font-family: 'SimSun','Songti SC',serif; letter-spacing: 0.3px;
}

.tech-desc {
  font-size: 10px; color: rgba(87,64,36,0.55); line-height: 1.4;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

.tech-tag {
  font-size: 10px; padding: 2px 8px;
  border: 1px solid rgba(87,64,36,0.28);
  flex-shrink: 0; font-family: 'SimSun','Songti SC',serif;
  letter-spacing: 0.5px;
}

.tech-tag.核心 {
  border-color: rgba(59,36,18,0.32);
  background: rgba(59,36,18,0.06);
  color: #3b2412;
}

.tech-tag.热门 {
  border-color: rgba(194,65,12,0.28);
  background: rgba(194,65,12,0.05);
  color: #c2410c;
}

.tech-tag.关注 {
  border-color: rgba(87,64,36,0.28);
  background: rgba(243,230,203,0.4);
  color: #5a3d28;
}

/* 技术栈介绍弹出框（点击项上方，信纸质感） */
.tech-pop {
  position: absolute;
  left: 0;
  bottom: calc(100% + 12px);
  width: min(330px, 100%);
  padding: 14px 16px 13px;
  background:
    radial-gradient(ellipse 60px 40px at 0% 0%, rgba(120, 80, 30, 0.10), transparent 70%),
    radial-gradient(ellipse 60px 40px at 100% 100%, rgba(120, 80, 30, 0.10), transparent 70%),
    #fbf3e2;
  border: 1px solid rgba(87, 64, 36, 0.42);
  box-shadow:
    0 10px 26px rgba(64, 45, 20, 0.22),
    0 4px 10px rgba(64, 45, 20, 0.12),
    inset 0 0 0 1px rgba(255, 252, 240, 0.55);
  z-index: 1;
}
.tech-pop::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none;
}
.tech-pop::after {
  content: '';
  position: absolute;
  left: 24px; bottom: -6px;
  width: 11px; height: 11px;
  background: #fbf3e2;
  border-right: 1px solid rgba(87, 64, 36, 0.42);
  border-bottom: 1px solid rgba(87, 64, 36, 0.42);
  transform: rotate(45deg);
}
.tech-pop-head {
  position: relative; z-index: 1;
  display: flex; align-items: center; justify-content: space-between;
  gap: 10px; margin-bottom: 8px;
}
.tech-pop-title {
  font-family: 'SimSun', 'Songti SC', 'Noto Serif SC', serif;
  font-size: 13px; font-weight: 700; color: #2a1a0e; letter-spacing: 0.5px;
}
.tech-pop-level {
  flex-shrink: 0;
  font-size: 10px; padding: 2px 8px;
  border: 1px solid rgba(87, 64, 36, 0.28);
  font-family: 'SimSun', 'Songti SC', serif; letter-spacing: 0.5px;
  color: #3b2412; background: rgba(59, 36, 18, 0.06);
}
.tech-pop-intro {
  position: relative; z-index: 1;
  margin: 0;
  font-size: 12px; line-height: 1.75;
  color: rgba(62, 40, 22, 0.82);
  font-family: 'SimSun', 'Songti SC', serif;
}
.tech-pop-enter-active, .tech-pop-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.tech-pop-enter-from, .tech-pop-leave-to { opacity: 0; transform: translateY(6px); }

/* Footer */
.home-footer {
  text-align: center; padding: 28px 0 8px;
  font-family: 'SimSun','Songti SC',serif;
  font-size: 11px; color: rgba(87,64,36,0.3); letter-spacing: 1px;
}

/* ================================================================
   Responsive
   ================================================================ */
@media (max-width: 780px) {
  .home-card { flex-direction: column; }
  .carousel-col { flex: none; padding: 24px 24px 20px; }
  .home-carousel { flex: none; height: 210px; }
  .col-divider { width: auto; height: 1px; background: linear-gradient(90deg, transparent 8%, rgba(87,64,36,0.1) 25%, rgba(87,64,36,0.1) 75%, transparent 92%); }
  .jobs-col { padding: 20px 24px 22px; }
  .bottom-row { grid-template-columns: 1fr; }
}

@media (max-width: 480px) {
  .home-scroll { padding: 16px 10px 20px; }
  .brand-name { font-size: 18px; letter-spacing: 4px; }
}
</style>


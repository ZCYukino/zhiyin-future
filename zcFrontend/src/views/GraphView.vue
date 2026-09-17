<template>
  <div class="graph-page">
    <div class="graph-content">
      <!-- 标题 -->
      <section class="page-hero">
        <div class="hero-paper">
          <h1 class="hero-title">岗位图谱</h1>
          <p class="hero-desc">全部岗位按 9 大技术栈分组排列成卡片，一眼看清「每个方向有哪些岗位」；点击岗位卡片原地展开其技能点（初级/中级/高级 + 涨跌趋势）。关系图谱以「横向换岗」为主：选一个岗位，立刻看到它能平移到哪些岗位、以及相对当前岗位要求「已具备 / 所差」的技能点，垂直晋升作为辅助参考；能力演化视图追踪近两年技能的新增、淘汰与重要性变化。</p>
        </div>
      </section>

      <!-- 控制栏：视图 Tab + 全局筛选（技术栈 / 级别） -->
      <div class="graph-toolbar">
        <div class="toolbar-left">
          <span class="toolbar-label">视角：</span>
          <div class="view-toggle">
            <button :class="{ active: viewMode === 'panorama' }" @click="switchView('panorama')">全景图谱</button>
            <button :class="{ active: viewMode === 'relations' }" @click="switchView('relations')">关系图谱</button>
            <button :class="{ active: viewMode === 'evolution' }" @click="switchView('evolution')">能力演化</button>
          </div>
        </div>
        <div class="toolbar-right">
          <!-- 技术栈筛选（全景概览 / 关系总览共用） -->
          <div v-if="viewMode === 'panorama' || (viewMode === 'relations' && !relationsFocusNode)" class="chip-selector">
            <button class="chip-btn" :class="{ active: relStackFilter === 'all' }" @click="setStackFilter('all')">全部</button>
            <button v-for="ts in techStacksForGraph" :key="ts.id" class="chip-btn" :class="{ active: relStackFilter === ts.id }" @click="setStackFilter(ts.id)">{{ ts.name }}</button>
          </div>
          <!-- 级别筛选（全景聚焦某岗位后生效） -->
          <div v-if="viewMode === 'panorama' && focusJob" class="chip-selector">
            <button class="chip-btn" :class="{ active: activeLevel === 'all' }" @click="selectLevel('all')">全部级别</button>
            <button class="chip-btn" :class="{ active: activeLevel === 'junior' }" @click="selectLevel('junior')">初级</button>
            <button class="chip-btn" :class="{ active: activeLevel === 'mid' }" @click="selectLevel('mid')">中级</button>
            <button class="chip-btn" :class="{ active: activeLevel === 'senior' }" @click="selectLevel('senior')">高级</button>
          </div>
          <!-- 关系聚焦：返回岗位列表 -->
          <template v-if="viewMode === 'relations' && relationsFocusNode">
            <button class="tool-btn" @click="relationsBackToOverview"><IconEpRefresh class="tool-btn-icon" /> 返回岗位列表</button>
          </template>
        </div>
      </div>

      <!-- 聚焦指示（含层级面包屑） -->
      <div v-if="allJobs.length" class="focus-crumb">
        <span class="crumb-mode">{{ modeLabel }}</span>
        <span class="crumb-sep">·</span>
        <span class="crumb-focus">{{ focusLabel }}</span>
        <template v-if="viewMode === 'relations' && relationsFocusNode">
          <span class="crumb-sep">·</span>
          <button class="crumb-back" @click="relationsBackToOverview">← 返回岗位列表</button>
        </template>
      </div>

      <!-- 空态（后端无数据） -->
      <div v-if="!allJobs.length" class="graph-empty">
        图谱数据加载中，或后端服务未启动。
      </div>

      <!-- 主体两栏 -->
      <div v-if="allJobs.length" class="graph-main">
        <!-- 中：画布 / 演化 -->
        <div class="graph-center">
          <!-- 全景：分组岗位卡片（全部 / 按技术栈筛选） -->
          <div v-if="viewMode === 'panorama' && !focusJob" class="all-stacks">
            <section v-for="b in allStackBlocks" :key="b.ts.id" class="stack-card">
              <div class="stack-card-head">
                <span class="stack-name-dot" :style="{ background: techStackColors[b.ts.id] || '#5a3d28' }"></span>
                <span class="stack-name">{{ b.ts.name }}</span>
                <span class="stack-count">{{ b.jobs.length }} 个岗位</span>
                <button v-if="activeTechStack !== 'all'" class="stack-back" @click="selectTechStack('all')">返回全部</button>
              </div>
              <div class="stack-job-chips">
                <button v-for="j in b.jobs" :key="j.id" class="all-job-chip" :class="{ 'job-new': j.isNew }" @click="openJobAbility(j.id)">
                  <span class="chip-job-name">{{ j.label }}</span>
                  <span v-if="j.isNew" class="chip-job-new">新</span>
                </button>
              </div>
            </section>
            <p v-if="!allStackBlocks.length" class="all-stacks-empty">暂无岗位数据</p>
          </div>

          <!-- 关系图谱总览：按技术栈分组的岗位卡片（点岗位 → 看它的换岗邻域） -->
          <div v-if="viewMode === 'relations' && !relationsFocusNode" class="all-stacks">
            <p class="rels-hint">
              <span class="rels-hint-gap">绿色「<b>N 关系</b>」= 该岗位有横向换岗 / 垂直晋升，点击进入看邻域</span>
              <span class="rels-hint-sep">·</span>
              <span class="rels-hint-none">灰色「<b>无关联</b>」= 暂无关系，点击仅提示</span>
            </p>
            <section v-for="b in relationsStackBlocks" :key="'r' + b.ts.id" class="stack-card">
              <div class="stack-card-head">
                <span class="stack-name-dot" :style="{ background: techStackColors[b.ts.id] || '#5a3d28' }"></span>
                <span class="stack-name">{{ b.ts.name }}</span>
                <span class="stack-count">{{ b.jobs.length }} 个岗位</span>
              </div>
              <div class="stack-job-chips">
                <button v-for="j in b.jobs" :key="'r' + j.id" class="all-job-chip"
                  :class="{ 'job-new': j.isNew, 'no-rel': !relationJobIds.has(j.id), 'has-rel': relationJobIds.has(j.id) }"
                  :title="relationJobIds.has(j.id) ? relCountOf(j.id) + ' 个横向换岗 / 垂直晋升关系' : '该岗位暂无横向换岗 / 垂直晋升关系'"
                  @click="relationsJobClick(j.id)">
                  <span class="chip-job-name">{{ j.label }}</span>
                  <span v-if="j.isNew" class="chip-job-new">新</span>
                  <span v-if="relationJobIds.has(j.id)" class="chip-rel-count">{{ relCountOf(j.id) }} 关系</span>
                  <span v-else class="chip-rel-none">无关联</span>
                </button>
              </div>
            </section>
            <p v-if="!relationsStackBlocks.length" class="all-stacks-empty">暂无岗位数据</p>
          </div>

          <!-- 聚焦上下文条：岗位名 + 醒目返回（紧贴画布，用户一眼可见） -->
          <div v-if="viewMode === 'panorama' && focusJob" class="canvas-focus-bar">
            <div class="cfb-title">
              <span class="cfb-eyebrow">能力图谱</span>
              <span class="cfb-job">{{ focusJobNode?.label }}</span>
              <span class="cfb-count">{{ focusJobSkillTotal }} 项技能</span>
            </div>
            <button class="cfb-back" @click="backToOverview">
              <span class="cfb-back-arrow">←</span><span>返回全景</span>
            </button>
          </div>

          <!-- G6 画布：岗位聚焦时的技能点环绕 / 关系图谱换岗邻域 -->
          <div v-show="showCanvas" ref="graphContainer" class="graph-canvas"></div>

          <!-- 关系图谱空态：后端无关系数据 -->
          <div v-if="viewMode === 'relations' && !relationJobs.length" class="graph-empty">
            暂无岗位关系数据。请在后端重新生成知识库快照（ingest），以派生岗位晋升 / 换岗关系。
          </div>
          <!-- 关系图谱空态：聚焦的岗位没有任何关系 -->
          <div v-if="viewMode === 'relations' && relationsFocusNode && !relationsTransferTo.length && !relationsAdvanceTo.length && !relationsPromotedFrom.length" class="graph-empty">
            「{{ relationsFocusNode.label }}」暂无横向换岗 / 垂直晋升关系，试试点击其它岗位。
          </div>

          <!-- 演化视图 -->
          <div v-if="viewMode === 'evolution'" class="evolution-view">
            <!-- 市场总览 -->
            <section class="market-overview">
              <h3 class="market-title">市场总览 · 近两年技能动向</h3>
              <p class="market-sub">聚合全部岗位的演化记录，回答"该学什么、该弃什么"。</p>
              <div class="market-grid">
                <div class="market-card add">
                  <span class="market-card-head"><span class="mc-icon">＋</span>新增最多</span>
                  <div class="market-list">
                    <span v-for="([k, c]) in marketOverview.added" :key="'a' + k" class="market-tag add">{{ k }} <i>{{ c }}</i></span>
                  </div>
                </div>
                <div class="market-card remove">
                  <span class="market-card-head"><span class="mc-icon">－</span>淘汰最多</span>
                  <div class="market-list">
                    <span v-for="([k, c]) in marketOverview.removed" :key="'r' + k" class="market-tag remove">{{ k }} <i>{{ c }}</i></span>
                  </div>
                </div>
                <div class="market-card up">
                  <span class="market-card-head"><span class="mc-icon">↑</span>重要性上升</span>
                  <div class="market-list">
                    <span v-for="([k, c]) in marketOverview.up" :key="'u' + k" class="market-tag up">{{ k }} <i>{{ c }}</i></span>
                  </div>
                </div>
                <div class="market-card down">
                  <span class="market-card-head"><span class="mc-icon">↓</span>重要性下降</span>
                  <div class="market-list">
                    <span v-for="([k, c]) in marketOverview.down" :key="'d' + k" class="market-tag down">{{ k }} <i>{{ c }}</i></span>
                  </div>
                </div>
              </div>
            </section>

            <!-- 按岗位 -->
            <section v-if="selectedEvoChanges.length" class="evo-detail">
              <h3 class="evo-detail-title">{{ selectedEvoJobName }} — 能力动态演化</h3>
              <p class="evo-subtitle">该岗位近两年技能点的新增、淘汰与重要性变化。</p>
              <div class="evo-timeline">
                <div v-for="(item, idx) in selectedEvoChanges" :key="idx" class="evo-period-card">
                  <div class="evo-period-head"><span class="evo-period-tag">{{ item.period }}</span></div>
                  <div v-if="item.addedSkills.length" class="evo-change-group add">
                    <span class="evo-change-icon">＋</span><span class="evo-change-label">新增技能：</span>
                    <span v-for="sk in item.addedSkills" :key="sk" class="evo-skill-tag add">{{ sk }}</span>
                  </div>
                  <div v-if="item.removedSkills.length" class="evo-change-group remove">
                    <span class="evo-change-icon">－</span><span class="evo-change-label">技能淘汰：</span>
                    <span v-for="sk in item.removedSkills" :key="sk" class="evo-skill-tag remove">{{ sk }}</span>
                  </div>
                  <div v-if="item.importanceUp.length" class="evo-change-group up">
                    <span class="evo-change-icon">↑</span><span class="evo-change-label">重要性提升：</span>
                    <span v-for="sk in item.importanceUp" :key="sk" class="evo-skill-tag up">{{ sk }}</span>
                  </div>
                  <div v-if="item.importanceDown.length" class="evo-change-group down">
                    <span class="evo-change-icon">↓</span><span class="evo-change-label">重要性下降：</span>
                    <span v-for="sk in item.importanceDown" :key="sk" class="evo-skill-tag down">{{ sk }}</span>
                  </div>
                  <div class="evo-meta">
                    <span class="evo-meta-item"><span class="meta-label">更新说明</span>{{ changeReasonOf(item) }}</span>
                    <span class="evo-meta-item"><span class="meta-label">数据源</span>{{ capabilitySourceOf().join(' · ') }}</span>
                  </div>
                </div>
              </div>
            </section>
            <section v-else class="evo-empty">
              <p>请在右侧选择一个岗位查看其能力演化轨迹。</p>
            </section>
          </div>

          <!-- 图例（仅岗位聚焦技能点）：与真实药丸一致——级别=药丸底色，趋势=药丸内符号 -->
          <div v-if="viewMode === 'panorama' && focusJob" class="graph-legend">
            <span class="legend-title">图例</span>
            <span class="legend-group">
              <span class="legend-group-label">级别</span>
              <span class="legend-pill junior">初级</span>
              <span class="legend-pill mid">中级</span>
              <span class="legend-pill senior">高级</span>
            </span>
            <span class="legend-sep"></span>
            <span class="legend-group">
              <span class="legend-group-label">趋势</span>
              <span class="legend-item"><span class="legend-glyph up">▲</span>上升</span>
              <span class="legend-item"><span class="legend-glyph down">▼</span>下降</span>
              <span class="legend-item"><span class="legend-glyph stable">●</span>稳定</span>
            </span>
          </div>

          <!-- 图例（关系图谱，仅聚焦画布时）：横向换岗（实线·主）/ 垂直晋升（细虚线·辅助） -->
          <div v-if="viewMode === 'relations' && relationsFocusNode" class="graph-legend">
            <span class="legend-title">方位</span>
            <span class="legend-group">
              <span class="legend-item"><span class="rel-line horizontal"></span>横向换岗 · 在右侧</span>
              <span class="legend-item"><span class="rel-line vertical"></span>垂直晋升 · 在上方</span>
            </span>
          </div>
        </div>

        <!-- 右：常驻详情列 -->
        <aside class="graph-aside">
          <!-- 全景图谱 -->
          <template v-if="viewMode === 'panorama'">
            <!-- 聚焦某岗位 -->
            <template v-if="focusJob">
              <!-- 技能节点被选中 -->
              <div v-if="selectedNode && selectedNode.type === 'skill'" class="aside-paper">
                <h4 class="aside-title">
                  {{ selectedNode.label }}
                  <span class="aside-trend" :class="selectedSkillIntro?.trend">{{ trendLabel(selectedSkillIntro?.trend) }}</span>
                </h4>
                <p class="aside-sublabel">技能介绍 · {{ selectedSkillIntro?.levelWord }}</p>
                <div class="aside-section">
                  <p class="aside-section-label">在本岗位中的作用</p>
                  <p class="aside-skill-desc">{{ selectedSkillIntro?.desc || stackDescOf(selectedSkillIntro?.stack) || '该技能用于支撑本岗位相关任务，需持续积累实践。' }}</p>
                </div>
                <div class="aside-skill-meta">
                  <span class="skill-meta-chip" :class="'pri-' + selectedSkillIntro?.priority">{{ selectedSkillIntro?.priorityLabel }}</span>
                  <span class="skill-meta-chip">{{ selectedSkillIntro?.levelWord }}</span>
                  <span class="skill-meta-chip">{{ stackNameOf(selectedSkillIntro?.stack) }}</span>
                </div>
                <div class="aside-section">
                  <p class="aside-section-label">也需要该技能的岗位（{{ skillOtherJobs.length }}个）</p>
                  <div class="aside-chips">
                    <span v-for="x in skillOtherJobs" :key="x.job.id" class="aside-chip" @click="openJobAbility(x.job.id)">{{ x.job.label }}</span>
                  </div>
                  <div v-if="!skillOtherJobs.length" class="aside-hint">暂无其它岗位需要该技能。</div>
                </div>
                <p class="aside-hint">点击岗位名可跳转其能力图谱；点画布空白处返回。</p>
              </div>
              <!-- 默认：该岗位技能点 -->
              <template v-else>
                <div class="aside-paper">
                  <h4 class="aside-title">{{ focusJobNode?.label }}</h4>
                  <p class="aside-sublabel">所需技能（{{ focusJobSkillTotal }}项，按资历分级）</p>
                  <div v-for="grp in focusJobSkillGroups" :key="grp.label" class="skill-level-group">
                    <p class="level-head">{{ grp.label }}（{{ grp.items.length }}）</p>
                    <div class="aside-skill-list">
                      <div v-for="x in grp.items" :key="x.node.id" class="aside-skill-row">
                        <span class="aside-skill-name">{{ x.node.label }}</span>
                        <span class="aside-skill-rel">{{ x.edge ? x.edge.label : (x.level ? levelWord(x.level) : '必备') }}</span>
                        <span class="aside-trend mini" :class="x.trend">{{ trendGlyph(x.trend) }}</span>
                      </div>
                    </div>
                  </div>
                  <p class="aside-hint">三条臂 = 初/中/高级：药丸底色 绿=初级 · 琥珀=中级 · 墨红=高级，沿臂向外难度递增；技能名已内嵌于药丸，前导符号  ▲升 / ▼跌 / ●稳。每条臂按间距智能展示若干技能，其余见下方分组；点技能可查看哪些岗位也在用它。</p>
                </div>
              </template>
            </template>
            <!-- 全景总览引导（未聚焦岗位时） -->
            <div v-else class="aside-paper">
              <h4 class="aside-title">全景图谱</h4>
              <p class="aside-sublabel">共 {{ allJobs.length }} 个岗位 · {{ stackCount }} 个技术栈方向</p>
              <p class="aside-hint">左侧已按「技术栈」分组展示全部岗位，点击岗位卡片即可查看其能力图谱；顶部技术栈可筛选方向。</p>
            </div>
          </template>

          <!-- 关系图谱 -->
          <template v-else-if="viewMode === 'relations'">
            <!-- 总览：引导 + 晋升阶梯（辅助参考） -->
            <template v-if="!relationsFocusNode">
              <div class="aside-paper">
                <h4 class="aside-title">关系图谱</h4>
                <p class="aside-sublabel">{{ relationJobs.length }} 个岗位有关系 · 以横向换岗为主</p>
                <div class="aside-legend">
                  <span class="rel-legend-item"><span class="rel-line horizontal"></span>横向换岗 → 右侧</span>
                  <span class="rel-legend-item"><span class="rel-line vertical"></span>垂直晋升 → 上方</span>
                </div>
                <p class="aside-hint">在左侧列表点击一个岗位，即可看到它能「换岗」到哪些岗位，以及相对该岗位要求「✅ 已具备 / ➕ 所差」的技能点（按技能重合度排序）。岗位带「N 关系」角标表示存在晋升或换岗关系。</p>
              </div>
              <div class="aside-paper">
                <h4 class="aside-title aside-title-aux">晋升阶梯 · 辅助参考</h4>
                <p class="aside-sublabel">后端确认的垂直发展链路</p>
                <div class="ladder-list">
                  <div v-for="(chain, idx) in relationLadders" :key="idx" class="ladder-chain">
                    <button v-for="(n, i) in chain" :key="n.id" class="ladder-node" @click="focusRelationsJob(n.id)">
                      {{ n.label }}<span v-if="i < chain.length - 1" class="ladder-arrow">→</span>
                    </button>
                  </div>
                  <p v-if="!relationLadders.length" class="aside-hint">暂无晋升链路数据。</p>
                </div>
              </div>
            </template>
            <!-- 选中岗位：横向换岗技能对比（主） + 垂直晋升（辅助） -->
            <template v-else>
              <div class="aside-paper">
                <h4 class="aside-title">{{ relationsFocusNode.label }}</h4>
                <p class="aside-sublabel">横向换岗优先 · 技能相对本岗位要求对比</p>
                <div v-if="relationsTransferTo.length" class="aside-section">
                  <p class="aside-section-label">可换岗到（{{ relationsTransferTo.length }}）· 从本岗位横向换岗到这些岗位</p>
                  <div v-for="t in relationsTransferTo" :key="'rt' + t.job.id" class="pivot-block transfer-block" :class="{ hl: relationsHighlight === t.job.id }">
                    <div class="pivot-head">
                      <span class="pivot-name"><span class="pc-from">{{ relationsFocusNode.label }}</span><span class="pc-arrow">→</span><span class="pc-to">{{ t.job.label }}</span></span>
                      <span class="pivot-rel match">技能重合 {{ t.have.length }}/{{ t.have.length + t.diff.length }}</span>
                    </div>
                    <div v-if="t.have.length" class="skill-line">
                      <span class="skill-line-label have">✅ 你已具备目标岗位所需</span>
                      <span v-for="sk in t.have" :key="'h' + sk" class="diff-chip have">{{ sk }}</span>
                    </div>
                    <div v-if="t.diff.length" class="skill-line">
                      <span class="skill-line-label gap">➕ 目标岗位额外要求，你尚未掌握</span>
                      <span v-for="sk in t.diff" :key="'g' + sk" class="diff-chip gap">{{ sk }}</span>
                    </div>
                    <div v-else-if="t.have.length" class="skill-line">
                      <span class="skill-line-label have">✅ 技能已完全覆盖目标岗位要求</span>
                    </div>
                    <div v-if="!t.have.length && !t.diff.length" class="pivot-diff empty">暂无该岗位技能要求数据。</div>
                  </div>
                </div>
                <div v-else class="aside-hint">暂无横向换岗关系。✅ 已具备 = 两岗位共同要求的技能；➕ 所差 = 目标岗位额外要求、当前岗位未覆盖的技能。</div>
              </div>
              <div v-if="relationsAdvanceTo.length || relationsPromotedFrom.length" class="aside-paper">
                <h4 class="aside-title aside-title-aux">垂直晋升 · 辅助</h4>
                <div v-if="relationsAdvanceTo.length" class="aside-section">
                  <p class="aside-section-label">可晋升到（{{ relationsAdvanceTo.length }}）· 从本岗位向上晋升到这些岗位</p>
                  <div v-for="t in relationsAdvanceTo" :key="'a' + t.job.id" class="pivot-block aux">
                    <div class="pivot-head">
                      <span class="pivot-name"><span class="pc-from">{{ relationsFocusNode.label }}</span><span class="pc-arrow">→</span><span class="pc-to">{{ t.job.label }}</span></span>
                      <span v-if="t.edge.label" class="pivot-rel vertical">{{ t.edge.label }}</span>
                    </div>
                  </div>
                </div>
                <div v-if="relationsPromotedFrom.length" class="aside-section">
                  <p class="aside-section-label">由以下晋升而来（{{ relationsPromotedFrom.length }}）· 由这些岗位晋升到本岗位</p>
                  <div v-for="t in relationsPromotedFrom" :key="'b' + t.job.id" class="pivot-block aux">
                    <div class="pivot-head">
                      <span class="pivot-name"><span class="pc-from">{{ t.job.label }}</span><span class="pc-arrow">→</span><span class="pc-to">{{ relationsFocusNode.label }}</span></span>
                      <span v-if="t.edge.label" class="pivot-rel vertical">{{ t.edge.label }}</span>
                    </div>
                  </div>
                </div>
              </div>
              <p class="aside-hint">点画布其它岗位可跳转到它的换岗分析；点空白返回岗位列表。悬停换岗目标会点亮右侧对应技能条。</p>
            </template>
          </template>

          <!-- 能力演化 -->
          <template v-else>
            <div class="aside-paper">
              <h4 class="aside-title">选择岗位</h4>
              <p class="aside-sublabel">热门岗位方向 Top{{ evolvableJobs.length }} · 含能力演化轨迹</p>
              <div class="evo-job-list">
                <button v-for="j in evolvableJobs" :key="j.id" class="evo-job-item" :class="{ active: selectedEvoJob === j.id }" @click="selectedEvoJob = j.id">{{ j.label }}</button>
              </div>
            </div>
            <div class="aside-paper">
              <h4 class="aside-title">趋势图例</h4>
              <div class="aside-legend">
                <span class="aside-trend up">▲ 上升</span>
                <span class="aside-trend down">▼ 下降</span>
                <span class="aside-trend stable">● 稳定</span>
              </div>
            </div>
          </template>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Graph } from '@antv/g6'
import { techStacksForGraph, changeReasonOf, capabilitySourceOf, inferStackFromName, priorityOf } from '@/models'
import type { CapabilityChange, GraphEdge, GraphNode, JobItem, SkillProgression, SkillSpec, SkillStack } from '@/models'
import { services } from '@/services'
import { ElMessage } from 'element-plus'

type ViewMode = 'panorama' | 'relations' | 'evolution'
type Level = 'junior' | 'mid' | 'senior'
type Trend = 'up' | 'down' | 'stable'

const graphContainer = ref<HTMLElement>()
let graph: Graph | null = null
let currentNodes: GraphNode[] = []
let currentEdges: GraphEdge[] = []
/** 画布平移进行中：此时内容在指针下滑动，抑制悬停高亮重渲染，避免拖动「不跟手/断触」 */
let dragging = false

const viewMode = ref<ViewMode>('panorama')
// 聚焦的岗位（graph 节点 id）；null = 全景概览
const focusJob = ref<string | null>(null)
// 关系图谱聚焦的岗位 id；null = 关系总览
const relationsFocus = ref<string | null>(null)
// 关系画布当前悬停 / 选中的换岗目标（用于点亮右栏对应技能条）
const relationsHighlight = ref<string | null>(null)
const activeTechStack = ref<string>('all')
// 关系总览的技术栈筛选（与全景各自独立，避免切换视角残留）
const activeRelStack = ref<string>('all')
const activeLevel = ref<'all' | Level>('all')
const selectedNode = ref<GraphNode | null>(null)
const selectedEvoJob = ref<string>('')

// 能力图谱：岗位所需技能（图谱关系 ∪ 技能矩阵，并集）
interface CapSkill {
  node: GraphNode
  edge: GraphEdge | null
  source: 'graph' | 'progression'
  level: Level | null
  trend: Trend
}

// ===== 数据源：纯后端（无 mock） =====
const graphData = ref<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] })
const capabilityChanges = ref<CapabilityChange[]>([])
const jobItems = ref<JobItem[]>([])

const allJobs = computed(() => graphData.value.nodes.filter(n => n.type === 'job'))
const allSkills = computed(() => graphData.value.nodes.filter(n => n.type === 'skill'))
const stackCount = computed(() => new Set(allJobs.value.map(j => j.techStack).filter(Boolean)).size)

// ===== 关系图谱：job→job 的晋升（advanced）/ 换岗（transfer）边 =====
const relationEdges = computed(() =>
  graphData.value.edges.filter(e =>
    e.source.startsWith('job-') && e.target.startsWith('job-') &&
    (e.relation === 'advanced' || e.relation === 'transfer')
  )
)
const relationJobs = computed(() => {
  const ids = new Set<string>()
  relationEdges.value.forEach(e => { ids.add(e.source); ids.add(e.target) })
  return allJobs.value.filter(j => ids.has(j.id))
})
const relationsFocusNode = computed(() =>
  relationsFocus.value ? allJobs.value.find(j => j.id === relationsFocus.value) || null : null
)
// 晋升阶梯：从无上级（无 advanced 指向）的岗位出发，沿 advanced 边 DFS 枚举全部根→叶链路
const relationLadders = computed(() => {
  const adv = relationEdges.value.filter(e => e.relation === 'advanced')
  const children = new Map<string, string[]>()
  adv.forEach(e => {
    if (!children.has(e.source)) children.set(e.source, [])
    children.get(e.source)!.push(e.target)
  })
  const hasIn = new Set(adv.map(e => e.target))
  const byId = new Map(relationJobs.value.map(j => [j.id, j]))
  const roots = relationJobs.value.filter(j => !hasIn.has(j.id) && children.has(j.id))
  const chains: GraphNode[][] = []
  const walk = (id: string, path: GraphNode[]) => {
    const kids = children.get(id)
    if (!kids || !kids.length) { if (path.length > 1) chains.push(path); return }
    kids.forEach(k => {
      const n = byId.get(k)
      if (!n || path.some(p => p.id === k)) { if (path.length > 1) chains.push(path); return }
      walk(k, [...path, n])
    })
  }
  roots.forEach(r => walk(r.id, [r]))
  return chains
})

// 当前下钻的技术栈方向
const currentStack = computed(() => techStacksForGraph.find(t => t.id === activeTechStack.value))
const currentStackName = computed(() => currentStack.value?.name || '')
const currentStackJobs = computed(() => allJobs.value.filter(j => j.techStack === activeTechStack.value))

// 全景卡片：按技术栈分组（「全部」显示全部方向，或筛到单个方向）
const allStackBlocks = computed(() =>
  techStacksForGraph
    .filter(ts => allJobs.value.some(j => j.techStack === ts.id))
    .filter(ts => activeTechStack.value === 'all' || ts.id === activeTechStack.value)
    .map(ts => ({ ts, jobs: allJobs.value.filter(j => j.techStack === ts.id) }))
)

const techStackColors: Record<string, string> = {
  ai: '#3b2412', backend: '#5a3d28', frontend: '#8a6a50', data: '#2f5a4a',
  cloud: '#4a2a1a', security: '#7a2a22', embedded: '#4c3a1e', product: '#a0722f', qa: '#6b5a48',
}

// ===== 技能等级工具 =====
function levelWord(level?: Level | null): string {
  return level === 'junior' ? '初级' : level === 'mid' ? '中级' : level === 'senior' ? '高级' : ''
}
function levelSize(level: Level): number {
  return level === 'junior' ? 22 : level === 'mid' ? 26 : 30
}

// 三条臂颜色：初级(绿)/中级(琥珀)/高级(墨红) —— 让「一线一难度」一眼可辨
const LEVEL_COLORS: Record<Level, string> = {
  junior: '#2f6b46',
  mid: '#b45309',
  senior: '#7a2a22',
}

// 图岗位 → /jobs → 技能递进矩阵
function progressionOf(jobNode: GraphNode | null | undefined): SkillProgression | undefined {
  if (!jobNode?.jobId) return undefined
  return jobItems.value.find(x => x.id === jobNode.jobId)?.progression
}

// ===== 技能趋势：由能力演化记录聚合 =====
function findSkillId(changeStr: string): string | undefined {
  if (!changeStr) return undefined
  for (const s of allSkills.value) {
    if (s.label.includes(changeStr) || changeStr.includes(s.label)) return s.id
  }
  return undefined
}

const skillTrendMap = computed(() => {
  const map = new Map<string, Trend>()
  allSkills.value.forEach(s => map.set(s.id, 'stable'))
  const upSet = new Set<string>()
  const downSet = new Set<string>()
  capabilityChanges.value.forEach(c => {
    c.importanceUp.forEach(sk => { const id = findSkillId(sk); if (id) upSet.add(id) })
    c.addedSkills.forEach(sk => { const id = findSkillId(sk); if (id) upSet.add(id) })
    c.importanceDown.forEach(sk => { const id = findSkillId(sk); if (id) downSet.add(id) })
    c.removedSkills.forEach(sk => { const id = findSkillId(sk); if (id) downSet.add(id) })
  })
  allSkills.value.forEach(s => {
    const up = upSet.has(s.id), down = downSet.has(s.id)
    map.set(s.id, up && !down ? 'up' : down && !up ? 'down' : 'stable')
  })
  return map
})

// ===== 计算属性 =====
const focusJobNode = computed<GraphNode | null>(() => {
  if (!focusJob.value) return null
  return allJobs.value.find(j => j.id === focusJob.value) || null
})

// 岗位所需全部技能 = 该岗位技能矩阵（与岗位详情同一数据源，展示一致）；无矩阵时退回图谱关联技能
const focusJobAllSkills = computed<CapSkill[]>(() => {
  const jobNode = focusJobNode.value
  if (!jobNode) return []
  const jobId = jobNode.id

  const prog = progressionOf(jobNode)
  if (prog) {
    // 主源：技能矩阵（与岗位详情逐项对齐），复用图谱技能节点 id 以便跨岗位关联；避免同技能跨级重复
    const list: CapSkill[] = []
    const seen = new Set<string>()
    const levels: { key: Level; specs: SkillSpec[] }[] = [
      { key: 'junior', specs: prog.junior },
      { key: 'mid', specs: prog.mid },
      { key: 'senior', specs: prog.senior },
    ]
    levels.forEach(({ key, specs }) => {
      specs.forEach((spec, idx) => {
        // 复用图谱技能节点 id（保留趋势/跨岗位关联），但标签用矩阵名（与岗位详情一致）
        const gid = findSkillId(spec.name)
        const base = gid ? allSkills.value.find(s => s.id === gid) : undefined
        const node: GraphNode = base
          ? { ...base, label: spec.name }
          : { id: `prog-${jobId}-${key}-${idx}`, label: spec.name, type: 'skill', level: key === 'junior' ? 'entry' : key, size: levelSize(key) }
        // 把矩阵的用途/技术栈直接挂在节点上，点击药丸时无需再靠模糊匹配回找
        ;(node as any)._mName = spec.name
        ;(node as any)._mDesc = spec.desc
        ;(node as any)._mStack = spec.stack
        if (seen.has(node.id)) return
        seen.add(node.id)
        list.push({ node, edge: null, source: 'progression', level: key, trend: skillTrendMap.value.get(node.id) || 'stable' })
      })
    })
    return list
  }

  // 无矩阵的诚实降级：退回图谱关联技能（job→skill 边）
  return graphData.value.edges
    .filter(e => e.source === jobId && e.target.startsWith('skill-'))
    .map(e => {
      const skill = allSkills.value.find(s => s.id === e.target)
      if (!skill) return null
      return { node: skill, edge: e, source: 'graph' as const, level: null, trend: skillTrendMap.value.get(skill.id) || 'stable' }
    })
    .filter((x): x is CapSkill => !!x)
})

const focusJobSkillTotal = computed(() => focusJobAllSkills.value.length)
const focusJobHasProgression = computed(() => !!progressionOf(focusJobNode.value))

// 按资历分级分组（无技能矩阵时退回单组）
const focusJobSkillGroups = computed(() => {
  const groups: { label: string; items: CapSkill[] }[] = []
  if (!focusJobHasProgression.value) {
    groups.push({ label: '全部技能', items: focusJobAllSkills.value })
    return groups
  }
  const bucket: Record<Level, CapSkill[]> = { junior: [], mid: [], senior: [] }
  const misc: CapSkill[] = []
  focusJobAllSkills.value.forEach(x => {
    if (x.level && bucket[x.level]) bucket[x.level].push(x)
    else misc.push(x)
  })
  ;(['junior', 'mid', 'senior'] as const).forEach(k => {
    if (bucket[k].length) groups.push({ label: levelWord(k), items: bucket[k] })
  })
  if (misc.length) groups.push({ label: '其它要求', items: misc })
  return groups
})

const skillOtherJobs = computed(() => {
  if (!selectedNode.value || selectedNode.value.type !== 'skill') return []
  return graphData.value.edges
    .filter(e => e.target === selectedNode.value!.id && e.source.startsWith('job-'))
    .map(e => ({ job: allJobs.value.find(j => j.id === e.source)!, edge: e }))
    .filter(x => x.job)
})

// ===== 选中技能 → 技能介绍（类似岗位详情技能点：用途 desc + 级别/优先级/技术栈） =====
function skillDescOf(name: string): { desc?: string; stack?: SkillStack; level?: Level } {
  if (!name) return {}
  const prog = progressionOf(focusJobNode.value)
  if (!prog) return {}
  const levels: { key: Level; specs: SkillSpec[] }[] = [
    { key: 'junior', specs: prog.junior },
    { key: 'mid', specs: prog.mid },
    { key: 'senior', specs: prog.senior },
  ]
  const n = name.replace(/\s+/g, '').toLowerCase()
  for (const { key, specs } of levels) {
    const spec = specs.find(s => {
      const sn = s.name.replace(/\s+/g, '').toLowerCase()
      return sn === n || sn.includes(n) || n.includes(sn)
    })
    if (spec) return { desc: spec.desc, stack: spec.stack, level: key }
  }
  return {}
}
function stackNameOf(stack?: SkillStack | string): string {
  return techStacksForGraph.find(t => t.id === (stack as string))?.name || (stack ? String(stack) : '')
}
function stackDescOf(stack?: SkillStack | string): string {
  return techStacksForGraph.find(t => t.id === (stack as string))?.description || ''
}
const selectedSkillIntro = computed(() => {
  const sk = selectedNode.value
  if (!sk || sk.type !== 'skill') return null
  const trend = skillTrendMap.value.get(sk.id) || 'stable'
  const lvl = (sk as any)._lvl as Level | undefined
  // 矩阵药丸自带 _mName/_mDesc/_mStack（与岗位详情同源）；图谱降级技能才靠模糊匹配兜底
  const mName = (sk as any)._mName || sk.label
  const mDesc = (sk as any)._mDesc as string | undefined
  const mStack = (sk as any)._mStack as SkillStack | undefined
  const { desc, stack, level } = skillDescOf(mName)
  const effectiveLevel: Level = lvl || level || 'mid'
  return {
    name: mName,
    trend,
    level: effectiveLevel,
    levelWord: levelWord(effectiveLevel),
    priorityLabel: effectiveLevel === 'junior' ? '必备' : effectiveLevel === 'mid' ? '重要' : '加分',
    priority: priorityOf(effectiveLevel),
    stack: (mStack || stack || ((sk as any)?.techStack as SkillStack) || inferStackFromName(mName)) as SkillStack,
    desc: mDesc || desc || '',
  }
})

function skillsOfJob(jobId: string): Set<string> {
  // 与能力图谱同源：以技能矩阵为主（映射到图谱技能节点 id），保证换岗/晋升的「所差」与展示一致；
  // 无矩阵时退回图谱 job→skill 边。
  const jobNode = allJobs.value.find(j => j.id === jobId)
  const prog = jobNode ? progressionOf(jobNode) : undefined
  if (prog) {
    const ids = new Set<string>()
    ;[...prog.junior, ...prog.mid, ...prog.senior].forEach(spec => {
      const gid = findSkillId(spec.name)
      if (gid) ids.add(gid)
    })
    if (ids.size) return ids
  }
  return new Set(
    graphData.value.edges
      .filter(e => e.source === jobId && e.target.startsWith('skill-'))
      .map(e => e.target)
  )
}

// 关系图谱聚焦：晋升方向（可晋升到 / 由谁晋升而来）+ 横向换岗
const relationsAdvanceTo = computed(() =>
  relationEdges.value
    .filter(e => e.relation === 'advanced' && e.source === relationsFocus.value)
    .map(e => ({ job: allJobs.value.find(j => j.id === e.target)!, edge: e }))
    .filter(x => x.job)
)
const relationsPromotedFrom = computed(() =>
  relationEdges.value
    .filter(e => e.relation === 'advanced' && e.target === relationsFocus.value)
    .map(e => ({ job: allJobs.value.find(j => j.id === e.source)!, edge: e }))
    .filter(x => x.job)
)
const relationsTransferTo = computed(() => {
  const src = relationsFocus.value
  if (!src) return []
  const srcSkills = skillsOfJob(src)
  return relationEdges.value
    .filter(e => e.relation === 'transfer' && (e.source === src || e.target === src))
    .map(e => {
      const otherId = e.source === src ? e.target : e.source
      const other = allJobs.value.find(j => j.id === otherId)!
      const otherSkills = skillsOfJob(otherId)
      const labelOf = (sid: string) => allSkills.value.find(s => s.id === sid)?.label || sid
      // ✅ 已具备 = 目标岗位所需 ∩ 当前岗位已有；➕ 所差 = 目标岗位所需 − 当前岗位已有
      const have = [...otherSkills].filter(sid => srcSkills.has(sid)).map(labelOf)
      const diff = [...otherSkills].filter(sid => !srcSkills.has(sid)).map(labelOf)
      return { job: other, edge: e, have, diff }
    })
    .filter(x => x.job)
    // 按技能重合度降序：最接近、最容易横跳的岗位排最前
    .sort((a, b) => b.have.length - a.have.length || a.diff.length - b.diff.length)
})

// ===== 关系总览：按技术栈分组的岗位卡片（取代「全部岗位一屏画完」的密集画布） =====
const relationsStackBlocks = computed(() =>
  techStacksForGraph
    .filter(ts => allJobs.value.some(j => j.techStack === ts.id))
    .filter(ts => activeRelStack.value === 'all' || ts.id === activeRelStack.value)
    .map(ts => ({ ts, jobs: allJobs.value.filter(j => j.techStack === ts.id) }))
)
const relationJobIds = computed(() => new Set(relationJobs.value.map(j => j.id)))
function relCountOf(jobId: string): number {
  return relationEdges.value.filter(e => e.source === jobId || e.target === jobId).length
}

// 热门岗位方向 Top9：按 /jobs.hotScore 关联评分降序取前 9 个
// hotScore 可能为 null（后端未采集到）：此时退回图谱侧的新/热标记，再退回中性 50
const evolvableJobs = computed(() => {
  const fallbackOf = (j: GraphNode): number => (j.isHot ? 90 : j.isNew ? 80 : 50)
  const hotScore = (j: GraphNode): number => {
    const job = j.jobId ? jobItems.value.find(x => x.id === j.jobId) : undefined
    return job?.hotScore ?? fallbackOf(j)
  }
  return [...allJobs.value].sort((a, b) => hotScore(b) - hotScore(a)).slice(0, 9)
})

const selectedEvoJobId = computed(() => allJobs.value.find(j => j.id === selectedEvoJob.value)?.jobId || '')

const selectedEvoChanges = computed(() =>
  capabilityChanges.value
    .filter(c => c.jobId === selectedEvoJobId.value)
    .sort((a, b) => a.period.localeCompare(b.period))
)

const selectedEvoJobName = computed(() => allJobs.value.find(j => j.id === selectedEvoJob.value)?.label || '')

// 市场总览：聚合全部岗位的演化记录
const marketOverview = computed(() => {
  const added = new Map<string, number>()
  const removed = new Map<string, number>()
  const up = new Map<string, number>()
  const down = new Map<string, number>()
  capabilityChanges.value.forEach(c => {
    c.addedSkills.forEach(s => added.set(s, (added.get(s) || 0) + 1))
    c.removedSkills.forEach(s => removed.set(s, (removed.get(s) || 0) + 1))
    c.importanceUp.forEach(s => up.set(s, (up.get(s) || 0) + 1))
    c.importanceDown.forEach(s => down.set(s, (down.get(s) || 0) + 1))
  })
  const top = (m: Map<string, number>, n: number) =>
    [...m.entries()].sort((a, b) => b[1] - a[1]).slice(0, n)
  return {
    added: top(added, 6),
    removed: top(removed, 6),
    up: top(up, 6),
    down: top(down, 6),
  }
})

const modeLabel = computed(() =>
  viewMode.value === 'panorama' ? '全景图谱' : viewMode.value === 'relations' ? '关系图谱' : '能力演化'
)
const focusLabel = computed(() => {
  if (viewMode.value === 'panorama') {
    if (focusJob.value) {
      const lv = activeLevel.value === 'all' ? '全部级别' : levelWord(activeLevel.value)
      return `${focusJobNode.value?.label ?? ''} · ${focusJobSkillTotal.value} 项技能 · ${lv}`
    }
    if (activeTechStack.value === 'all') return `全部技术栈 · ${allJobs.value.length} 个岗位`
    return `${currentStackName.value} · ${currentStackJobs.value.length} 个岗位`
  }
  if (viewMode.value === 'relations') {
    if (relationsFocusNode.value) {
      return `${relationsFocusNode.value.label} · 可换岗 ${relationsTransferTo.value.length} · 晋升 ${relationsAdvanceTo.value.length + relationsPromotedFrom.value.length}`
    }
    return `横向换岗优先 · ${relationJobs.value.length} 个岗位有关系`
  }
  return selectedEvoJobName.value || '市场总览'
})

function trendLabel(t?: Trend): string { return t === 'up' ? '上升' : t === 'down' ? '下降' : '稳定' }
function trendGlyph(t?: Trend): string { return t === 'up' ? '▲' : t === 'down' ? '▼' : '●' }

// 是否显示 G6 画布：全景聚焦某岗位；关系图谱只在「聚焦某岗位」时画它的换岗邻域
const showCanvas = computed(() =>
  viewMode.value === 'relations'
    ? !!relationsFocusNode.value
    : viewMode.value === 'panorama' && !!focusJob.value
)

// ===== 视图切换 =====
function switchView(mode: ViewMode) {
  viewMode.value = mode
  selectedNode.value = null
  if (mode === 'evolution') {
    if (graph) { graph.destroy(); graph = null }
    if (!selectedEvoJob.value && evolvableJobs.value[0]) selectedEvoJob.value = evolvableJobs.value[0].id
  } else if (mode === 'relations') {
    // 关系模式默认回到「岗位列表」总览（HTML 卡片），不再一屏画全部关系
    relationsFocus.value = null
    relationsHighlight.value = null
    if (graph) { graph.destroy(); graph = null }
  } else {
    nextTick(() => initGraph())
  }
}

/** 关系图谱：聚焦某岗位 → 画它的「横向换岗邻域」 */
function focusRelationsJob(jobId: string) {
  relationsFocus.value = jobId
  relationsHighlight.value = null
  nextTick(() => initRelationsGraph())
}

/** 关系总览点击：无关系岗位不进空聚焦，直接弹提示，避免「点进去发现什么都没有」 */
function relationsJobClick(jobId: string) {
  if (!relationJobIds.value.has(jobId)) {
    const job = allJobs.value.find(j => j.id === jobId)
    ElMessage.info(`「${job?.label || '该岗位'}」暂无横向换岗 / 垂直晋升关系`)
    return
  }
  focusRelationsJob(jobId)
}

/** 关系图谱：回到岗位列表总览 */
function relationsBackToOverview() {
  relationsFocus.value = null
  relationsHighlight.value = null
  if (graph) { graph.destroy(); graph = null }
}

function backToOverview() {
  focusJob.value = null
  selectedNode.value = null
  nextTick(() => initGraph())
}

/** 聚焦某岗位：原地展开其技能点 */
function openJobAbility(jobId: string) {
  focusJob.value = jobId
  selectedNode.value = null
  if (viewMode.value === 'panorama') nextTick(() => initGraph())
}

function selectTechStack(id: string) {
  activeTechStack.value = id
  focusJob.value = null
  selectedNode.value = null
  if (viewMode.value === 'panorama') nextTick(() => initGraph())
}

// 顶栏技术栈筛选：全景 / 关系总览共用同一组 chip，按当前视角分发
const relStackFilter = computed(() => viewMode.value === 'relations' ? activeRelStack.value : activeTechStack.value)
function setStackFilter(id: string) {
  if (viewMode.value === 'relations') {
    activeRelStack.value = id
    relationsFocus.value = null
    relationsHighlight.value = null
    if (graph) { graph.destroy(); graph = null }
  } else {
    selectTechStack(id)
  }
}

function selectLevel(level: 'all' | Level) {
  activeLevel.value = level
  selectedNode.value = null
  if (viewMode.value === 'panorama' && focusJob.value) nextTick(() => initGraph())
}

// ===== 图谱初始化 =====
function nodeStyle(d: any): any {
  const node = d as GraphNode
  if (node.type === 'job') {
    // 中心岗位：墨色大圆 + 岗位名内嵌（聚焦焦点，文字已入圆中）
    const color = techStackColors[node.techStack || ''] || '#5a3d28'
    return {
      size: (node as any)._jobD || 72,
      fill: color,
      stroke: '#2a1a0e',
      lineWidth: 3,
      labelText: (node as any)._jobDisp || node.label,
      labelFontSize: 15,
      labelFontWeight: 700,
      labelFontFamily: 'SimSun, Songti SC, serif',
      labelFill: '#fbf3e2',
      labelPlacement: 'center',
      cursor: 'pointer',
      ...(node.isNew ? { stroke: '#c2410c' } : {}),
    }
  }
  // 技能节点：文字内嵌的「药丸」——按臂级别填色（初/中/高），内侧注趋势符号（▲升/▼跌/●稳）
  const lvlColor = (node as any)._lvlColor || '#5a3d28'
  const plw = (node as any)._plw || 60
  const plh = (node as any)._plh || 34
  const glyph = (node as any)._glyph || ''
  const name = (node as any)._disp || node.label
  return {
    size: [plw, plh],
    radius: plh / 2,
    fill: lvlColor,
    stroke: '#2a1a0e',
    lineWidth: 1.4,
    labelText: glyph + name,
    labelFontSize: 12,
    labelFontWeight: 700,
    labelFontFamily: 'SimSun, Songti SC, serif',
    labelFill: '#fbf3e2',
    labelPlacement: 'center',
    cursor: 'pointer',
  }
}

function edgeStyle(d: any): any {
  const edge = d as GraphEdge
  // 三臂三角形：每条臂是颜色一致的醒目实线（中心→首技能更粗，链式顺延）
  const stroke = (edge as any)._lvlColor || '#8a7560'
  return {
    stroke,
    lineWidth: Math.max(1.4, edge.weight || 1.5),
    lineDash: undefined,
    endArrow: false,
  }
}

// ===== 岗位聚焦：三臂三角布局 =====
// 岗位居中，向 120° 方向伸出的三条臂（初级/中级/高级）呈三角形；
// 每条臂上的同级别技能点沿臂链式排布，臂即连成一条醒目实线。
// 关键：超长技能名截断（防溢出）+ 画布高度随该岗位技能数自适应（防空/挤）。
function buildJobFocus(width: number, minH = 400): { nodes: GraphNode[]; edges: GraphEdge[]; height: number } {
  const job = focusJobNode.value
  if (!job) return { nodes: [], edges: [], height: 400 }
  const baseR = 134 // 首药丸距中心的半径——越过中心圆并留出间隙（防对角药丸撞入中心）
  const PER_ARM = 5 // 每条臂最多展示 5 个技能（其余见右侧分组）
  // 药丸高度随资历递增：初级/中级/高级
  const pillH = (l: Level) => (l === 'junior' ? 36 : l === 'mid' ? 40 : 44)
  // 超长技能名截断：>6 字则省略，完整名见侧栏
  const disp = (s: string) => (s.length > 6 ? s.slice(0, 5) + '…' : s)
  // 趋势符号：▲升 / ▼跌 / ●稳
  const glyphOf = (x: CapSkill): string => {
    const t = skillTrendMap.value.get(x.node.id) || 'stable'
    return t === 'up' ? '▲' : t === 'down' ? '▼' : '●'
  }
  // 药丸宽：按「符号+名字」实际字符数估算（中文≈12px, 坐标固定不缩放故字稍大更清晰），并限幅防超长撑破画布
  const pillWOf = (x: CapSkill, l: Level) => {
    const s = disp(x.node.label)
    const gl = glyphOf(x)
    return Math.min(140, Math.max(48, (s.length + gl.length) * 12 + 22))
  }
  // 中心岗位圆：直径随岗位名（截断后）撑开，粗体文字内嵌其中（字 14px, 直径上限 100 防过大）
  const jobDisp = job.label.length > 6 ? job.label.slice(0, 5) + '…' : job.label
  const jobD = Math.min(100, Math.max(62, (jobDisp.length + 1) * 14 + 10))
  const jobR = jobD / 2

  // 按资历分组；无级别的技能点按图谱关系回退到初/中/高
  const levelOf = (x: CapSkill): Level =>
    x.level || (x.edge?.relation === 'core' ? 'junior' : x.edge?.relation === 'required' ? 'mid' : 'senior')
  const buckets: Record<Level, CapSkill[]> = { junior: [], mid: [], senior: [] }
  const skills = activeLevel.value === 'all'
    ? focusJobAllSkills.value
    : focusJobAllSkills.value.filter(x => x.level === activeLevel.value)
  skills.forEach(x => buckets[levelOf(x)].push(x))

  // 手臂数量随「已填充级别数」自适应：1 臂朝上、2 臂上下对开、3 臂 120° 呈三角形
  const filledLevels = (['junior', 'mid', 'senior'] as Level[]).filter(l => buckets[l].length)
  const arms: { key: Level; angle: number }[] =
    filledLevels.length === 1
      ? [{ key: filledLevels[0], angle: 270 }]
      : filledLevels.length === 2
        ? [{ key: filledLevels[0], angle: 270 }, { key: filledLevels[1], angle: 90 }]
        : [
            { key: 'junior', angle: 270 }, // 上
            { key: 'mid', angle: 30 },     // 右下
            { key: 'senior', angle: 150 }, // 左下
          ]

  // 臂最长半径：按半画宽限幅，防对角线药丸冲出画布
  const Rmax = Math.max(baseR, Math.min(430, Math.floor((width / 2 - 142) / 0.866)))

  // 先算每条臂的可容纳技能数（竖直臂看高度、对角臂看宽度——相邻药丸不重叠），据此定长度与 cy。
  const plan = arms.map(arm => {
    const cos = Math.cos((arm.angle * Math.PI) / 180)
    const list = buckets[arm.key]
    const isVert = Math.abs(cos) < 0.1 // 竖直臂（270/90）：cos≈0
    const h = pillH(arm.key)
    let maxW = 46
    list.slice(0, PER_ARM).forEach(x => { maxW = Math.max(maxW, pillWOf(x, arm.key)) })
    // 对角臂需按「斜线±左右半宽」拉开，避免相邻药丸左右重叠；竖直臂按高度即可
    const step = isVert ? h + 12 : maxW / 0.866 + 10
    const n = Math.min(list.length, PER_ARM, 1 + Math.floor((Rmax - baseR) / step))
    const len = baseR + Math.max(0, n - 1) * step
    return { arm, n, step, len }
  }).filter(p => p.n > 0)

  const nodes: GraphNode[] = []
  const edges: GraphEdge[] = []
  // 先以「中心岗位」为原点放置节点，再按整簇真实边界整体平移 → 画布内精确居中
  job.x = 0
  job.y = 0
  ;(job as any)._jobD = jobD
  ;(job as any)._jobDisp = jobDisp
  nodes.push(job)

  for (const p of plan) {
    const { arm, n, step } = p
    const rad = (arm.angle * Math.PI) / 180
    const cos = Math.cos(rad)
    const sin = Math.sin(rad)
    const color = LEVEL_COLORS[arm.key]
    const list = buckets[arm.key].slice(0, n)
    let prev: GraphNode = job
    list.forEach((x, k) => {
      const r = baseR + k * step
      const node: GraphNode = { ...x.node, x: cos * r, y: sin * r }
      ;(node as any)._lvl = arm.key
      ;(node as any)._lvlColor = color
      ;(node as any)._disp = disp(x.node.label)
      ;(node as any)._glyph = glyphOf(x)
      ;(node as any)._plw = pillWOf(x, arm.key)
      ;(node as any)._plh = pillH(arm.key)
      nodes.push(node)
      const edgeId = `${prev.id}->${node.id}`
      const edge: GraphEdge = {
        source: prev.id,
        target: node.id,
        relation: 'level',
        weight: prev.id === job.id ? 3.0 : 2.1,
      }
      ;(edge as any).id = edgeId
      ;(edge as any)._lvlColor = color
      ;(node as any)._edgeIn = edgeId
      edges.push(edge)
      prev = node
    })
  }

  // 整簇边界：中心圆 ±jobR；技能药丸按宽/高半值（悬停/选中仅加描边不改尺寸，留 1.02 供描边不裁）
  const halfPad = 1.02
  let minX = -jobR
  let maxX = jobR
  let minY = -jobR
  let maxY = jobR
  nodes.forEach(n => {
    const isJob = n.type === 'job'
    const hw = ((isJob ? (n as any)._jobD : (n as any)._plw) / 2) * halfPad
    const hh = ((isJob ? (n as any)._jobD : (n as any)._plh) / 2) * halfPad
    minX = Math.min(minX, n.x - hw)
    maxX = Math.max(maxX, n.x + hw)
    minY = Math.min(minY, n.y - hh)
    maxY = Math.max(maxY, n.y + hh)
  })

  // 以整簇中心为基准换算画布尺寸与整体平移量：簇中心精确落到画布中心
  const cX = (minX + maxX) / 2
  const cY = (minY + maxY) / 2
  const pad = 70
  const contentH = maxY - minY
  const height = Math.max(minH, contentH + 2 * pad)
  const cx = width / 2 - cX
  const cy = height / 2 - cY
  nodes.forEach(n => { n.x += cx; n.y += cy })

  return { nodes, edges, height }
}

/** 画布最小高度：填满 .graph-center 面板可见奶油区（去掉顶部聚焦条占高），
 *  否则 G6 视口(高度=内容高)比面板矮，拖动时内容会在面板内提前被裁切（“没到边就消失”）。 */
function canvasMinHeight(): number {
  const panel = graphContainer.value?.parentElement as HTMLElement | null
  if (!panel) return 560
  const bar = panel.querySelector('.canvas-focus-bar') as HTMLElement | null
  const barH = bar ? bar.offsetHeight + 12 : 0
  return Math.max(430, (panel.clientHeight || 560) - barH)
}

function initGraph() {
  if (!graphContainer.value) return
  // 全景卡片模式（未聚焦岗位）无需 G6 画布
  if (!focusJob.value) {
    if (graph) { graph.destroy(); graph = null }
    return
  }
  if (graph) { graph.destroy(); graph = null }

  const container = graphContainer.value
  const width = container.clientWidth || 1000

  const { nodes, edges, height } = buildJobFocus(width, canvasMinHeight())
  container.style.height = height + 'px'

  currentNodes = nodes
  currentEdges = edges

  const opts: any = {
    container,
    width,
    height,
    animation: true,
    // 坐标均预计算，不跑布局
    layout: undefined,
    // 中心 job → circle，技能药丸 → rect（文字内嵌）
    node: {
      type: (d: any) => (d.type === 'job' ? 'circle' : 'rect'),
      style: (d: any) => nodeStyle(d),
      state: {
        // active（悬停）：仅加橙环 + 文字轻微加粗，取消任何尺寸放大/扩散，杜绝「光晕」感。
        // 注意：G6 默认主题的 active/selected 会带 halo:true（大光圈），必须显式 halo:false 关掉，否则光标移到药丸/选中后
        // 会在节点周围渲染一圈低透明度的「光圈」扩散（正是用户反馈的「光晕」）。
        active: (d: any) => ({ halo: false, opacity: 1, lineWidth: 3.5, stroke: '#c2410c', labelFontSize: d.type === 'job' ? 15 : 12 }),
        // selected（单击选中）：不绘制任何环/光晕，仅保持不淡出；其余技能靠 dimmed 淡出形成对比。
        // 同样必须 halo:false，并把 lineWidth/stroke 复位为基调，避免继承主题 selected 的加粗黑边框。
        selected: (d: any) => ({ halo: false, opacity: 1, lineWidth: d.type === 'job' ? 3 : 1.4, stroke: '#2a1a0e' }),
        // dimmed（选中某技能后，其余技能淡出，突出当前选中，形成强「确认感」）
        dimmed: (d: any) => ({ halo: false, opacity: 0.32 }),
      },
    },
    edge: {
      style: (d: any) => edgeStyle(d),
      state: {
        active: { opacity: 1, lineWidth: 3, stroke: '#c2410c' },
        selected: { opacity: 1, lineWidth: 3.4, stroke: '#2a1a0e' },
        dimmed: { opacity: 0.18 },
      },
    },
    // 固定布局：禁止缩放（滚轮/双击放大），仅保留背景平移。移除 drag-element（节点由布局算法定位，
    // 拖动无意义）与 hover-activate（degree:1 会把 1 度邻接一并点亮→「一团乱亮」）。悬停为自定义逻辑。
    behaviors: [{ type: 'drag-canvas', enable: () => true }],
    autoFit: false,
    padding: [24, 24, 24, 24],
  }

  graph = new Graph(opts)
  graph.setData({
    nodes: nodes.map(n => ({ ...n, style: { x: n.x, y: n.y, z: 0 } })),
    edges,
  } as any)
  graph.render()

  // 悬停：技能橙环、入边高亮；单击：技能选中（其余技能/边淡出，选中技能不再加环）
  let hoverTargets: string[] = []
  let selectedId: string | null = null

  const nodeById = (id: string) => currentNodes.find(n => n.id === id)

  // 合并节点当前应具备的状态。
  // 关键：一旦某技能被选中，选中技能本身只保留「selected」（不叠加任何悬停环/光晕），
  // 剩余技能一律「dimmed」淡出——彻底杜绝「点击后鼠标移开仍有光圈扩散」。
  function statesForNode(id: string): string[] {
    const nd = nodeById(id)
    if (!nd) return []
    if (selectedId && nd.type === 'skill') {
      return id === selectedId ? ['selected'] : ['dimmed']
    }
    // 未选中状态：仅悬停的节点亮橙环
    const s: string[] = []
    if (hoverTargets.includes(id)) s.push('active')
    return s
  }

  // 边状态：关联其目标技能——悬停高亮橙、选中高亮墨、选中时其它边淡出
  function edgeStates(edge: GraphEdge): string[] {
    const s: string[] = []
    if (nodeById(edge.target)?.type !== 'skill') return s
    const skillId = edge.target
    if (selectedId === skillId) s.push('selected')
    else if (hoverTargets.includes(skillId)) s.push('active')
    else if (selectedId) s.push('dimmed')
    return s
  }

  function applyEdgeStates() {
    currentEdges.forEach(e => graph!.setElementState((e as any).id, edgeStates(e)))
  }

  function setActive(id: string, on: boolean) {
    const nd = nodeById(id)
    if (!nd || !graph) return
    // 只高亮当前悬停节点本身，不再联动中心岗位（root 根节点）
    const targets = [id]
    if (on) {
      targets.forEach(t => { if (!hoverTargets.includes(t)) hoverTargets.push(t) })
    } else {
      hoverTargets = hoverTargets.filter(t => !targets.includes(t))
    }
    targets.forEach(t => graph!.setElementState(t, statesForNode(t)))
    applyEdgeStates()
  }

  function setSelected(id: string | null) {
    selectedId = id
    // 选中变化会影响「其它技能淡出」与所有边，整体刷新一次
    currentNodes.forEach(n => graph!.setElementState(n.id, statesForNode(n.id)))
    applyEdgeStates()
  }

  graph.on('node:pointerenter', (evt: any) => { const id = evt.target?.id; if (id && !dragging) setActive(id, true) })
  graph.on('node:pointerleave', (evt: any) => { const id = evt.target?.id; if (id && !dragging) setActive(id, false) })
  // 指针离开整个画布时，清掉可能残留的悬停环（防止「移开仍有光圈」）
  graph.on('canvas:pointerleave', () => { if (!dragging && hoverTargets.length) setActive(hoverTargets[0], false) })
  // 拖拽画布期间抑制悬停高亮，并在拖拽开始清掉残留高亮，防止内容平移后高亮错位/卡顿
  graph.on('dragstart', () => { dragging = true; hoverTargets = []; setSelected(selectedId) })
  graph.on('dragend', () => { dragging = false })

  graph.on('node:click', (evt: any) => {
    const id = evt.target?.id
    if (!id) return
    const nd = nodeById(id)
    if (!nd) return
    if (nd.type === 'job') {
      // 点击中心岗位 → 取消技能选中，回到该岗位全览
      selectedNode.value = null
      setSelected(null)
      return
    }
    // 技能节点 → 侧栏显示关联岗位 + 持久选中（入边加粗 + 其余淡出，选中技能自身不加环/光晕）；
    // 清空悬停集，确保选中的药丸上不留任何残留光圈。
    selectedNode.value = { ...nd }
    hoverTargets = []
    setSelected(id)
  })
  graph.on('canvas:click', () => {
    // 点空白只取消技能选中，不再返回全景（返回由画布上方醒目「返回全景」按钮承担）
    selectedNode.value = null
    setSelected(null)
  })
}

// ===== 关系图谱：按技术栈分列 + 晋升阶梯自上而下排布 =====
function jobPillW(j: GraphNode): number {
  return Math.min(150, Math.max(96, j.label.length * 13 + 32))
}

// _relKind：center=居中当前岗位 / transfer=横向换岗目标（主角）/ advance=垂直晋升（辅助，弱化）
function relationsNodeStyle(d: any): any {
  const node = d as GraphNode
  const kind = (node as any)._relKind || 'transfer'
  const w = (node as any)._relW || 120
  const stackColor = techStackColors[(node.techStack || node.category || '') as string] || '#5a3d28'
  if (kind === 'center') {
    return {
      size: [w, 48], radius: 24, fill: '#2a1a0e', stroke: '#c2410c', lineWidth: 2.5,
      labelText: node.label, labelFontSize: 15, labelFontWeight: 700,
      labelFontFamily: 'SimSun, Songti SC, serif', labelFill: '#fbf3e2', labelPlacement: 'center',
    }
  }
  if (kind === 'advance') {
    return {
      size: [w, 32], radius: 16, fill: 'rgba(138,117,96,0.55)', stroke: 'rgba(90,61,40,0.5)', lineWidth: 1,
      labelText: node.label, labelFontSize: 11, labelFontFamily: 'SimSun, Songti SC, serif',
      labelFill: '#fbf3e2', labelPlacement: 'center', opacity: 0.85,
    }
  }
  // 横向换岗目标：技术栈着色，突出
  return {
    size: [w, 40], radius: 20, fill: stackColor, stroke: '#2a1a0e', lineWidth: 1.6,
    labelText: node.label, labelFontSize: 13, labelFontWeight: 700,
    labelFontFamily: 'SimSun, Songti SC, serif', labelFill: '#fbf3e2', labelPlacement: 'center',
  }
}

// 换岗=主角（实线、粗、深色）；晋升=辅助（细虚线、弱化）
function relationsEdgeStyle(d: any): any {
  const edge = d as GraphEdge
  const isTransfer = edge.relation === 'transfer'
  return {
    stroke: isTransfer ? '#3b2412' : 'rgba(138,117,96,0.75)',
    lineWidth: isTransfer ? 2.2 : 1.2,
    lineDash: isTransfer ? undefined : [5, 4],
    // 方向箭头：换岗→右（横向），晋升→上（垂直），让「从什么到什么」一眼可见
    endArrow: true,
    labelText: edge.label || (isTransfer ? '换岗' : '晋升'),
    labelFontSize: isTransfer ? 11 : 9,
    labelFill: isTransfer ? '#3b2412' : 'rgba(138,117,96,0.9)',
    labelFontFamily: 'SimSun, Songti SC, serif',
    labelBackground: true,
    labelBackgroundFill: 'rgba(251,243,226,0.92)',
    labelBackgroundOpacity: 1,
    labelBackgroundPadding: [2, 4, 2, 4],
    opacity: isTransfer ? 0.95 : 0.6,
  }
}

// 聚焦单岗位的「岗位关系」布局：统一的方位逻辑（当前岗位居中锚点）
//   · 上方 = 可晋升到（垂直向上，更高层级）
//   · 下方 = 由以下晋升而来（垂直向下，更低层级）
//   · 右侧 = 横向换岗（同级，全部排在同一列）
// 以中心岗位为原点摆放，最后按整簇包围盒整体居中，保证任何数据下都居中、方位一致。
function buildRelationsFocusLayout(width: number, minH = 320): { nodes: GraphNode[]; edges: GraphEdge[]; height: number } {
  const src = relationsFocusNode.value!
  const transfers = relationsTransferTo.value
  const upList = relationsAdvanceTo.value
  const downList = relationsPromotedFrom.value

  const nodes: GraphNode[] = []
  const edges: GraphEdge[] = []

  const rowGap = 88   // 右侧换岗列纵向间距
  const armX = 260    // 右侧换岗列距中心岗位的水平距离
  const upY = 168     // 上方可晋升排距中心的垂直距离
  const downY = 168   // 下方晋升来源排距中心的垂直距离
  const colGap = 40   // 上/下晋升排内水平间距

  // 右侧换岗列总跨距（纵向），用于让换岗目标相对中心岗位呈上下扇形
  const armSpan = Math.max(0, transfers.length - 1) * rowGap
  const hwOf = (n: GraphNode) => ((n as any)._relW || 120) / 2
  const rowW = (list: typeof transfers) => list.reduce((s, t) => s + jobPillW(t.job), 0) + colGap * Math.max(0, list.length - 1)

  // 中心岗位（原点）
  nodes.push({ ...src, x: 0, y: 0, _relW: jobPillW(src) + 24, _relKind: 'center' } as any)

  // 右侧换岗列：全部在右侧，按技能重合度降序，最匹配的靠上
  transfers.forEach((t, i) => {
    const y = -armSpan / 2 + i * rowGap
    nodes.push({ ...t.job, x: armX, y, _relW: jobPillW(t.job), _relKind: 'transfer' } as any)
    edges.push({ source: src.id, target: t.job.id, label: t.edge.label || '换岗', weight: 1, relation: 'transfer' })
  })

  // 上方：可晋升到（以中心岗位为中心水平铺开）
  if (upList.length) {
    let x = -rowW(upList) / 2
    upList.forEach(t => {
      const w = jobPillW(t.job)
      nodes.push({ ...t.job, x: x + w / 2, y: -upY, _relW: w, _relKind: 'advance' } as any)
      edges.push({ source: src.id, target: t.job.id, label: t.edge.label, weight: 2, relation: 'advanced' })
      x += w + colGap
    })
  }
  // 下方：由以下晋升而来（以中心岗位为中心水平铺开）
  if (downList.length) {
    let x = -rowW(downList) / 2
    downList.forEach(t => {
      const w = jobPillW(t.job)
      nodes.push({ ...t.job, x: x + w / 2, y: downY, _relW: w, _relKind: 'advance' } as any)
      edges.push({ source: t.job.id, target: src.id, label: t.edge.label, weight: 2, relation: 'advanced' })
      x += w + colGap
    })
  }

  // 定位：以「中心岗位」为锚——水平置于画布中心（换岗朝其右侧展开），垂直按整簇包围盒居中；
  // 并用边界夹紧，确保任何数据下图谱不越出画布。
  let height = 320
  if (nodes.length) {
    const halfOf = (n: GraphNode) => {
      const kind = (n as any)._relKind || 'transfer'
      const hw = hwOf(n)
      const hh = kind === 'center' ? 24 : kind === 'advance' ? 16 : 20
      return { hw, hh }
    }
    let minX = 1e9, maxX = -1e9, minY = 1e9, maxY = -1e9
    nodes.forEach(n => { const { hw, hh } = halfOf(n); minX = Math.min(minX, n.x - hw); maxX = Math.max(maxX, n.x + hw); minY = Math.min(minY, n.y - hh); maxY = Math.max(maxY, n.y + hh) })
    const cY = (minY + maxY) / 2
    const pad = 40
    const contentH = maxY - minY
    height = Math.max(minH, contentH + 2 * pad)
    // 水平：岗位(原点)放到画布中心；若换岗/晋升内容超出边界则夹紧
    let dx = width / 2
    dx = Math.min(dx, width - pad - maxX)
    dx = Math.max(dx, pad - minX)
    const dy = height / 2 - cY
    nodes.forEach(n => { n.x += dx; n.y += dy })
  }

  return { nodes, edges, height }
}

function initRelationsGraph() {
  if (!graphContainer.value) return
  // 只在聚焦某岗位、且该岗位确有关系时渲染；否则回到 HTML 总览
  const focus = relationsFocusNode.value
  if (!focus) {
    if (graph) { graph.destroy(); graph = null }
    return
  }
  const hasRel = relationsTransferTo.value.length || relationsAdvanceTo.value.length || relationsPromotedFrom.value.length
  if (!hasRel) {
    if (graph) { graph.destroy(); graph = null }
    return
  }
  if (graph) { graph.destroy(); graph = null }

  const container = graphContainer.value
  const width = container.clientWidth || 1000
  // 画布高至少填满面板可见奶油区，消除“视口矮于面板 → 拖动提前裁切”的问题
  const { nodes, edges, height } = buildRelationsFocusLayout(width, canvasMinHeight())
  container.style.height = height + 'px'

  currentNodes = nodes

  const opts: any = {
    container,
    width,
    height,
    animation: true,
    layout: undefined,
    node: {
      type: () => 'rect',
      style: (d: any) => relationsNodeStyle(d),
      state: {
        active: (d: any) => ({ lineWidth: 3, stroke: '#c2410c' }),
      },
    },
    edge: {
      style: (d: any) => relationsEdgeStyle(d),
      state: { active: { opacity: 1, lineWidth: 2.8, stroke: '#c2410c' } },
    },
    behaviors: [{ type: 'drag-canvas', enable: () => true }],
    // 不缩放：节点保持真实像素尺寸（与全景图谱一致），仅靠 cx=width/2 的布局天然居中。
    // 之前用 autoFit view 会把小簇（2-3 个节点）放大到铺满画布 → 图谱「巨大无比」。
  }

  graph = new Graph(opts)
  graph.setData({
    nodes: nodes.map(n => ({ ...n, style: { x: n.x, y: n.y, z: 0 } })),
    edges,
  } as any)
  graph.render()

  const centerId = focus.id
  // 悬停：只点亮当前指向的岗位本身，不再联动中心/根节点
  function setActive(id: string, on: boolean) {
    if (!graph) return
    const targets = new Set<string>([id])
    targets.forEach(t => {
      if (currentNodes.some(n => n.id === t)) graph!.setElementState(t, on ? ['active'] : [])
    })
  }
  graph.on('node:pointerenter', (evt: any) => {
    if (dragging) return
    const id = evt.target?.id
    if (!id) return
    setActive(id, true)
    if (id !== centerId) relationsHighlight.value = id
  })
  graph.on('node:pointerleave', (evt: any) => {
    if (dragging) return
    const id = evt.target?.id
    if (!id) return
    setActive(id, false)
    relationsHighlight.value = null
  })
  // 拖拽画布期间抑制悬停高亮；拖拽开始清掉残留高亮，结束后恢复
  graph.on('dragstart', () => {
    dragging = true
    const cur = relationsHighlight.value
    if (cur) setActive(cur, false)
    relationsHighlight.value = null
  })
  graph.on('dragend', () => { dragging = false })

  // 点击邻居岗位 → 下钻到它的换岗分析；点击空白只取消高亮，不返回（返回由顶部醒目按钮承担）
  graph.on('node:click', (evt: any) => {
    const id = evt.target?.id
    if (!id) return
    const nd = currentNodes.find(n => n.id === id)
    if (nd?.type === 'job' && id !== centerId) focusRelationsJob(id)
  })
  graph.on('canvas:click', () => { relationsHighlight.value = null })
}

onMounted(async () => {
  try {
    const [g, cc, jobs] = await Promise.all([
      services.getGraph(),
      services.getCapabilityChanges(),
      services.getJobs(),
    ])
    if (g?.nodes?.length) graphData.value = g
    if (cc?.length) capabilityChanges.value = cc
    if (jobs?.length) jobItems.value = jobs
  } catch { /* 后端异常时数据保持为空 */ }
  if (allJobs.value.length) nextTick(() => initGraph())
})

onUnmounted(() => {
  if (graph) { graph.destroy(); graph = null }
})
</script>

<style scoped>
.graph-page {
  min-height: calc(100vh - 56px);
}

.graph-content {
  max-width: 1240px;
  margin: 0 auto;
  padding: 28px 24px 40px;
}

/* ===== Hero ===== */
.page-hero { margin-bottom: 20px; }

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
  padding: 22px 30px;
  font-family: 'SimSun', 'Songti SC', 'STSong', 'Noto Serif SC', serif;
}

.hero-title {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 6px;
  color: #2a1a0e;
  margin: 0;
}

.hero-desc {
  font-size: 13px;
  line-height: 1.8;
  color: rgba(58, 38, 20, 0.88);
  margin: 10px 0 0;
}

/* ===== Toolbar ===== */
.graph-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  margin-bottom: 12px;
  background:
    radial-gradient(ellipse 80px 60px at 0% 0%, rgba(120, 80, 30, 0.12), transparent 70%),
    radial-gradient(ellipse 90px 70px at 100% 100%, rgba(120, 80, 30, 0.10), transparent 70%),
    #fbf3e2;
  border: 1px solid rgba(87, 64, 36, 0.34);
  box-shadow:
    0 24px 50px rgba(64, 45, 20, 0.18),
    0 10px 20px rgba(64, 45, 20, 0.10),
    inset 0 0 0 1px rgba(255, 252, 240, 0.55),
    inset 0 0 0 5px rgba(251, 243, 226, 1),
    inset 0 0 0 6px rgba(87, 64, 36, 0.28);
  flex-wrap: wrap;
  gap: 10px;
  position: relative;
}
.graph-toolbar::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none; z-index: 0;
}

.toolbar-left { display: flex; align-items: center; gap: 12px; }

.toolbar-label {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 14px; color: #5a3d28; letter-spacing: 1px; white-space: nowrap;
}

.view-toggle {
  display: flex; gap: 0;
  border: 1px solid rgba(87, 64, 36, 0.42);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.1), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.view-toggle button {
  padding: 6px 16px; border: none; border-right: 1px solid rgba(87, 64, 36, 0.18);
  background: transparent; font-family: 'SimSun', 'Songti SC', serif;
  font-size: 14px; color: #5a3d28; letter-spacing: 0.5px; cursor: pointer; transition: all 0.2s;
}
.view-toggle button:last-child { border-right: none; }
.view-toggle button:hover { background: rgba(243, 230, 203, 0.6); color: #3b2412; }
.view-toggle button.active { background: #3b2412; color: #fbf3e2; font-weight: 600; }

.toolbar-right { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }

/* 通用筛选 chips（技术栈 / 级别） */
.chip-selector {
  display: flex; gap: 3px; border: 1px solid rgba(87, 64, 36, 0.42); padding: 3px;
  background: rgba(252, 247, 235, 0.9); flex-wrap: wrap;
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.1), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.chip-btn {
  padding: 4px 10px; border: 1px solid transparent; background: transparent;
  font-family: 'SimSun', 'Songti SC', serif; font-size: 13px; color: #5a3d28;
  cursor: pointer; transition: all 0.2s; letter-spacing: 0.5px; white-space: nowrap;
}
.chip-btn:hover { color: #3b2412; background: rgba(243, 230, 203, 0.6); }
.chip-btn.active { color: #fbf3e2; background: #3b2412; border-color: #2a1a0e; font-weight: 600; }

.tool-btn {
  display: inline-flex; align-items: center; gap: 4px; padding: 6px 12px;
  border: 1px solid rgba(87, 64, 36, 0.42); background: rgba(250, 242, 222, 0.9);
  font-family: 'SimSun', 'Songti SC', serif; font-size: 12px; color: #5a3d28;
  letter-spacing: 0.5px; cursor: pointer; transition: all 0.2s;
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.1), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.tool-btn:hover { background: rgba(87, 64, 36, 0.08); color: #3b2412; border-color: rgba(87, 64, 36, 0.42); }
.tool-btn-icon { font-size: 14px; }

/* ===== 聚焦指示 ===== */
.focus-crumb {
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px; color: rgba(87, 64, 36, 0.8);
  letter-spacing: 1px;
  margin: 0 0 12px 4px;
  display: flex; align-items: center; flex-wrap: wrap; gap: 0;
}
.crumb-mode { color: #3b2412; font-weight: 600; }
.crumb-sep { margin: 0 6px; color: rgba(87, 64, 36, 0.8); }
.crumb-back {
  border: 1px solid rgba(87, 64, 36, 0.42); background: rgba(250, 242, 222, 0.9); cursor: pointer;
  font-family: 'SimSun', 'Songti SC', serif; font-size: 12px;
  color: #3b2412; letter-spacing: 0.5px; padding: 3px 10px;
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.1), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
  transition: all 0.2s;
}
.crumb-back:hover { background: #3b2412; color: #fbf3e2; border-color: #2a1a0e; text-decoration: none; }

.graph-empty {
  padding: 80px 24px;
  text-align: center;
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 14px;
  color: #6f5438;
  border: 1px dashed rgba(87, 64, 36, 0.42);
  background: rgba(252, 247, 235, 0.85);
}

/* ===== 主体两栏 ===== */
.graph-main {
  display: flex;
  gap: 16px;
  align-items: flex-start;
}

.graph-center {
  position: relative;
  flex: 1;
  min-width: 0;
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
  min-height: 560px;
}
.graph-center::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none; z-index: 0;
}
.graph-center > * { position: relative; z-index: 1; }

/* 画布聚焦上下文条：墨色底 + 奶油返回按钮，与奶油画布形成强对比，一眼锁定「当前聚焦状态」 */
.canvas-focus-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  margin-bottom: 12px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent), #3b2412;
  border: 1px solid #2a1a0e;
  box-shadow: 0 4px 14px rgba(42, 26, 14, 0.22), inset 0 0 0 1px rgba(255, 252, 240, 0.12);
}
.cfb-title { display: flex; align-items: baseline; gap: 10px; min-width: 0; flex-wrap: wrap; }
.cfb-eyebrow {
  font-family: 'Georgia', serif; font-size: 9px; letter-spacing: 2px;
  color: rgba(251, 243, 226, 0.58); text-transform: uppercase;
}
.cfb-job {
  font-family: 'SimSun', 'Songti SC', serif; font-size: 15px; font-weight: 700;
  color: #fbf3e2; letter-spacing: 1px;
}
.cfb-count {
  font-family: 'Georgia', serif; font-size: 11px; color: rgba(251, 243, 226, 0.62);
}
.cfb-back {
  display: inline-flex; align-items: center; gap: 6px; flex-shrink: 0;
  padding: 7px 16px;
  background: #fbf3e2; color: #3b2412;
  border: 1px solid #2a1a0e;
  font-family: 'SimSun', 'Songti SC', serif; font-size: 13px; font-weight: 700; letter-spacing: 1px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.28), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
  transition: all 0.2s;
}
.cfb-back:hover {
  background: #f4e9d6; color: #2a1a0e; border-color: #2a1a0e;
  transform: translateX(-2px);
}
.cfb-back-arrow { font-family: 'Georgia', serif; font-size: 15px; font-weight: 700; }

.graph-canvas { width: 100%; height: 560px; }

/* ===== 全景分组岗位卡片 ===== */
.all-stacks {
  display: flex; flex-direction: column; gap: 18px;
  padding: 20px 22px; min-height: 560px;
}
.stack-card {
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
  padding: 14px 18px 16px;
  position: relative;
}
.stack-card::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none; z-index: 0;
}
.stack-card-head {
  display: flex; align-items: center; gap: 9px; margin-bottom: 12px;
  padding-bottom: 10px; border-bottom: 1px dashed rgba(87, 64, 36, 0.22);
}
.stack-name-dot {
  width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0;
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.stack-name {
  font-family: 'SimSun', 'Songti SC', serif; font-size: 15px; font-weight: 700;
  color: #2a1a0e; letter-spacing: 1px;
}
.stack-count {
  font-family: 'Georgia', serif; font-size: 11px; color: #6b5335; padding: 1px 8px;
  border: 1px solid rgba(87, 64, 36, 0.32); background: rgba(250, 242, 222, 0.9); letter-spacing: 0.5px;
}
.stack-back {
  margin-left: auto; border: 1px solid rgba(87, 64, 36, 0.38); background: rgba(250, 242, 222, 0.9);
  font-family: 'SimSun', 'Songti SC', serif; font-size: 11px; color: #c2410c;
  padding: 3px 10px; cursor: pointer; transition: all 0.2s; letter-spacing: 0.5px;
}
.stack-back:hover { background: #3b2412; color: #fbf3e2; border-color: #2a1a0e; }

.stack-job-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.all-job-chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 7px 13px; cursor: pointer; transition: all 0.18s;
  border: 1px solid rgba(87, 64, 36, 0.44); background: rgba(252, 247, 235, 0.92);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.12), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
  font-family: 'SimSun', 'Songti SC', serif; font-size: 13px; color: #3b2412; letter-spacing: 0.5px;
}
.all-job-chip:hover {
  background: #3b2412; color: #fbf3e2; border-color: #2a1a0e;
  transform: translateY(-1px); box-shadow: 0 4px 10px rgba(64, 45, 20, 0.14);
}
.chip-job-name { white-space: nowrap; }
.chip-job-new {
  font-size: 10px; color: #c2410c; font-weight: 700; letter-spacing: 1px;
  border: 1px solid rgba(194, 65, 12, 0.4); padding: 0 4px; line-height: 1.3;
  background: rgba(194, 65, 12, 0.05); border-radius: 2px;
}
.all-job-chip:hover .chip-job-new { color: #fbf3e2; border-color: rgba(251, 243, 226, 0.6); }
.all-stacks-empty {
  color: #6f5438; font-family: 'SimSun', 'Songti SC', serif; font-size: 13px;
}

/* 右栏 */
.graph-aside {
  width: 300px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.aside-paper {
  position: relative;
  background:
    radial-gradient(ellipse 70px 55px at 0% 0%, rgba(120, 80, 30, 0.14), transparent 70%),
    radial-gradient(ellipse 70px 55px at 100% 0%, rgba(120, 80, 30, 0.12), transparent 70%),
    radial-gradient(ellipse 80px 60px at 0% 100%, rgba(120, 80, 30, 0.16), transparent 70%),
    radial-gradient(ellipse 80px 60px at 100% 100%, rgba(120, 80, 30, 0.14), transparent 70%),
    #fbf3e2;
  border: 1px solid rgba(87, 64, 36, 0.34);
  box-shadow:
    0 24px 50px rgba(64, 45, 20, 0.18),
    0 10px 20px rgba(64, 45, 20, 0.10),
    inset 0 0 0 1px rgba(255, 252, 240, 0.55),
    inset 0 0 0 5px rgba(251, 243, 226, 1),
    inset 0 0 0 6px rgba(87, 64, 36, 0.28);
  padding: 16px 18px;
  font-family: 'SimSun', 'Songti SC', serif;
}
.aside-paper::before {
  content: '';
  position: absolute; inset: 0;
  background-image:
    repeating-linear-gradient(0deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px),
    repeating-linear-gradient(90deg, rgba(87, 64, 36, 0.018) 0 1px, transparent 1px 3px);
  pointer-events: none; z-index: 0;
}
.aside-paper > * { position: relative; z-index: 1; }

.aside-title {
  font-size: 15px; font-weight: 700; color: #2a1a0e;
  letter-spacing: 1px; margin: 0 0 4px;
  display: flex; align-items: center; gap: 6px; flex-wrap: wrap;
}
.aside-sublabel {
  font-size: 13px; color: rgba(87, 64, 36, 0.85) !important;
  margin: 0 0 12px; letter-spacing: 0.5px;
}
.aside-section { margin-top: 4px; }
.aside-section-label {
  font-size: 11px; color: rgba(87, 64, 36, 0.8);
  margin: 0 0 8px; letter-spacing: 0.5px;
}
.aside-hint {
  font-size: 13px; color: rgba(87, 64, 36, 0.8);
  line-height: 1.75; margin: 10px 0 0;
}

.aside-skill-list { display: flex; flex-direction: column; gap: 5px; }
.skill-level-group { margin-bottom: 12px; }
.skill-level-group:last-child { margin-bottom: 0; }
.level-head {
  font-size: 11px; color: #3b2412; font-weight: 600;
  margin: 0 0 6px; letter-spacing: 0.5px;
  padding-bottom: 3px; border-bottom: 1px dashed rgba(87, 64, 36, 0.22);
}
.aside-skill-row {
  display: flex; align-items: center; gap: 8px;
  padding: 5px 8px; border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.aside-skill-name { flex: 1; font-size: 12px; color: #2a1a0e; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.aside-skill-rel {
  font-size: 10px; color: #5a3d28; padding: 1px 6px;
  border: 1px solid rgba(87, 64, 36, 0.3); background: rgba(250, 242, 222, 0.85);
  flex-shrink: 0;
}

.aside-chips { display: flex; flex-wrap: wrap; gap: 5px; }
.aside-chip {
  font-size: 11px; color: #3b2412; padding: 3px 9px;
  border: 1px solid rgba(87, 64, 36, 0.4); background: rgba(252, 247, 235, 0.9);
  cursor: pointer; transition: all 0.2s; letter-spacing: 0.3px;
  box-shadow: 0 2px 5px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.aside-chip:hover { background: #3b2412; color: #fbf3e2; border-color: #2a1a0e; }

/* 趋势徽标 */
.aside-trend {
  font-size: 10px; padding: 1px 6px; border: 1px solid;
  font-family: 'Georgia', serif; letter-spacing: 0.5px; font-weight: 700;
}
.aside-trend.up { color: #059669; border-color: rgba(5, 150, 105, 0.4); background: rgba(5, 150, 105, 0.06); }
.aside-trend.down { color: #dc2626; border-color: rgba(220, 38, 38, 0.4); background: rgba(220, 38, 38, 0.06); }
.aside-trend.stable { color: #64748b; border-color: rgba(100, 116, 139, 0.4); background: rgba(100, 116, 139, 0.06); }
.aside-trend.mini { padding: 0 4px; font-size: 11px; }

/* 技能介绍：用途说明 + 元信息 chips */
.aside-skill-desc {
  font-size: 12px; line-height: 1.7; color: #3b2412; margin: 0;
}
.aside-skill-meta { display: flex; flex-wrap: wrap; gap: 6px; margin: 6px 0 12px; }
.skill-meta-chip {
  font-size: 11px; padding: 2px 8px; border: 1px solid rgba(87, 64, 36, 0.28);
  border-radius: 999px; color: #5a3d28; background: rgba(251, 243, 226, 0.6);
}
.skill-meta-chip.pri-must { color: #7a2a22; border-color: rgba(122, 42, 34, 0.4); background: rgba(122, 42, 34, 0.08); }
.skill-meta-chip.pri-important { color: #b45309; border-color: rgba(180, 83, 9, 0.4); background: rgba(180, 83, 9, 0.08); }
.skill-meta-chip.pri-bonus { color: #6f5438; border-color: rgba(138, 117, 96, 0.4); background: rgba(138, 117, 96, 0.08); }

/* 转岗分析 */
.pivot-block {
  padding: 10px 12px; margin-bottom: 8px;
  border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.pivot-block:last-child { margin-bottom: 0; }
.pivot-head { display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; margin-bottom: 6px; gap: 6px; }
.pivot-name { font-size: 13px; font-weight: 600; color: #2a1a0e; }
/* 晋升方向「来源 → 目标」：来源弱化灰、目标加粗墨、箭头橙，一眼看清从什么到什么 */
.pc-from { color: rgba(90, 61, 40, 0.85); font-weight: 500; }
.pc-arrow { margin: 0 5px; color: #c2410c; font-weight: 700; font-family: Georgia, serif; }
.pc-to { color: #2a1a0e; font-weight: 700; }
.pivot-rel { font-size: 10px; padding: 1px 6px; border: 1px solid; }
.pivot-rel.vertical { color: #3b2412; border-color: rgba(59, 36, 18, 0.35); background: rgba(59, 36, 18, 0.05); }
.pivot-diff { font-size: 11px; color: rgba(87, 64, 36, 0.85); display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
.diff-chip {
  font-size: 10px; color: #c2410c; padding: 1px 6px;
  border: 1px solid rgba(194, 65, 12, 0.28); background: rgba(194, 65, 12, 0.04);
}
.pivot-diff.empty { color: rgba(87, 64, 36, 0.8); }

/* ===== 关系图谱（换岗优先）专用 ===== */
.aside-title-aux { font-size: 13px; color: #6b5a48; }
/* 换岗技能行：✅已具备（绿）/ ➕所差（琥珀） */
.skill-line { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; margin-top: 5px; }
.skill-line-label { font-size: 10px; letter-spacing: 0.3px; margin-right: 2px; white-space: nowrap; }
.skill-line-label.have { color: #2f6b46; }
.skill-line-label.gap { color: #b45309; }
.diff-chip.have { color: #2f6b46; border-color: rgba(47, 107, 70, 0.32); background: rgba(47, 107, 70, 0.06); }
.diff-chip.gap { color: #b45309; border-color: rgba(180, 83, 9, 0.3); background: rgba(180, 83, 9, 0.05); }
/* 重合度徽章 */
.pivot-rel.match { color: #2f6b46; border-color: rgba(47, 107, 70, 0.35); background: rgba(47, 107, 70, 0.07); font-weight: 600; }
/* 换岗目标块：悬停画布节点时点亮 */
.pivot-block.transfer-block { transition: border-color 0.15s, box-shadow 0.15s; }
.pivot-block.transfer-block.hl {
  border-color: #c2410c;
  box-shadow: 0 0 0 2px rgba(194, 65, 12, 0.28), 0 2px 6px rgba(64, 45, 20, 0.08);
}
/* 晋升辅助块：弱化 */
.pivot-block.aux { background: rgba(252, 247, 235, 0.55); border-color: rgba(87, 64, 36, 0.28); }
/* 总览岗位卡：有关系（绿·突出可点）/ 无关系（灰·弱化+虚线，点击仅提示） */
.chip-rel-count {
  font-size: 10px; color: #2f6b46; border: 1px solid rgba(47, 107, 70, 0.38);
  background: rgba(47, 107, 70, 0.1); padding: 0 5px; border-radius: 2px; margin-left: 6px;
  font-family: Georgia, serif; font-weight: 600;
}
.chip-rel-none {
  font-size: 10px; color: #6f5438;
  border: 1px dashed rgba(138, 117, 96, 0.5); background: rgba(138, 117, 96, 0.05);
  padding: 0 5px; border-radius: 2px; margin-left: 6px; font-family: Georgia, serif; font-weight: 600;
}
/* 有关系的岗位卡：绿色微强调，示意「可点进邻域」 */
.all-job-chip.has-rel { border-color: rgba(47, 107, 70, 0.42); box-shadow: 0 1px 4px rgba(47, 107, 70, 0.08); }
/* 无关系的岗位卡：弱化 + 虚线边框 + 灰字，一眼区分 */
.all-job-chip.no-rel {
  opacity: 0.58; border-style: dashed; border-color: rgba(87, 64, 36, 0.22);
  background: rgba(252, 247, 235, 0.45);
}
.all-job-chip.no-rel:hover {
  opacity: 0.82; background: rgba(252, 247, 235, 0.7);
  color: rgba(90, 61, 40, 0.85); border-color: rgba(87, 64, 36, 0.28);
  transform: none;
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.12), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.all-job-chip.no-rel .chip-job-name { color: rgba(90, 61, 40, 0.8); }

/* 关系总览顶部提示图例 */
.rels-hint {
  display: flex; flex-wrap: wrap; gap: 4px 10px; align-items: baseline;
  font-size: 11.5px; letter-spacing: 0.2px; color: rgba(87, 64, 36, 0.8);
  padding: 8px 12px; margin: 0 0 14px;
  background: rgba(252, 247, 235, 0.9); border: 1px solid rgba(87, 64, 36, 0.28);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.rels-hint b { font-family: Georgia, serif; }
.rels-hint-sep { color: rgba(87, 64, 36, 0.8); }
.rels-hint-gap b { color: #2f6b46; }
.rels-hint-none b { color: #6f5438; }

/* 关系图谱图例：横向换岗（实线·主）/ 垂直晋升（细虚线·辅助） */
.rel-legend-item { display: inline-flex; align-items: center; gap: 6px; font-size: 11px; color: #5a3d28; }
.rel-line {
  display: inline-block; width: 26px; height: 0; flex-shrink: 0; position: relative;
}
/* 横向换岗 = 实线深色（主角） */
.rel-line.horizontal { border-top: 2.2px solid #3b2412; }
/* 垂直晋升 = 细虚线弱化（辅助） */
.rel-line.vertical { border-top: 1.2px dashed rgba(138, 117, 96, 0.8); }

/* 晋升阶梯链 */
.ladder-list { display: flex; flex-direction: column; gap: 8px; }
.ladder-chain { display: flex; flex-wrap: wrap; align-items: center; gap: 2px; }
.ladder-node {
  border: none; background: transparent; padding: 2px 1px;
  font-family: 'SimSun', 'Songti SC', serif; font-size: 12px; color: #3b2412;
  cursor: pointer; letter-spacing: 0.3px; transition: color 0.2s;
}
.ladder-node:hover { color: #c2410c; text-decoration: underline; }
.ladder-arrow { color: rgba(87, 64, 36, 0.8); margin: 0 2px; font-size: 11px; }

/* 演化右栏 */
.evo-job-list { display: flex; flex-direction: column; gap: 4px; }
.evo-job-item {
  text-align: left; padding: 5px 10px; border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9); font-family: 'SimSun', 'Songti SC', serif;
  font-size: 12px; color: #5a3d28; cursor: pointer; transition: all 0.2s; letter-spacing: 0.5px;
  box-shadow: 0 2px 5px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.evo-job-item:hover { background: rgba(243, 230, 203, 0.6); color: #3b2412; }
.evo-job-item.active { background: #3b2412; color: #fbf3e2; font-weight: 600; border-color: #2a1a0e; }

.aside-legend { display: flex; flex-direction: column; gap: 6px; }
.aside-legend .aside-trend { font-size: 11px; padding: 2px 8px; align-self: flex-start; }

/* ===== 演化视图（中栏） ===== */
.evolution-view { padding: 20px 24px; min-height: 560px; }

.market-overview { margin-bottom: 24px; }
.market-title {
  font-family: 'SimSun', 'Songti SC', serif; font-size: 16px; font-weight: 700;
  color: #2a1a0e; letter-spacing: 1px; margin: 0 0 4px;
}
.market-sub { font-size: 12px; color: #6f5438; margin: 0 0 14px; }
.market-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 12px;
}
.market-card {
  padding: 12px 14px; border: 1px solid rgba(87, 64, 36, 0.4);
  background: rgba(252, 247, 235, 0.9);
  box-shadow: 0 2px 6px rgba(64, 45, 20, 0.08), inset 0 0 0 1px rgba(255, 252, 240, 0.5);
}
.market-card-head {
  display: flex; align-items: center; gap: 6px;
  font-family: 'SimSun', 'Songti SC', serif; font-size: 12px; font-weight: 600;
  color: #2a1a0e; letter-spacing: 0.5px; margin-bottom: 8px;
}
.mc-icon { font-size: 13px; }
.market-card.add .mc-icon { color: #10b981; }
.market-card.remove .mc-icon { color: #ef4444; }
.market-card.up .mc-icon { color: #f59e0b; }
.market-card.down .mc-icon { color: #94a3b8; }
.market-list { display: flex; flex-wrap: wrap; gap: 5px; }
.market-tag {
  font-size: 11px; padding: 2px 8px; border: 1px solid;
  font-family: 'SimSun', 'Songti SC', serif; letter-spacing: 0.3px;
  display: inline-flex; align-items: center; gap: 4px;
}
.market-tag i { font-style: normal; font-family: 'Georgia', serif; font-size: 10px; opacity: 0.6; }
.market-tag.add { border-color: rgba(16, 185, 129, 0.2); background: rgba(16, 185, 129, 0.06); color: #059669; }
.market-tag.remove { border-color: rgba(239, 68, 68, 0.15); background: rgba(239, 68, 68, 0.04); color: #dc2626; text-decoration: line-through; }
.market-tag.up { border-color: rgba(245, 158, 11, 0.2); background: rgba(245, 158, 11, 0.06); color: #d97706; }
.market-tag.down { border-color: rgba(148, 163, 184, 0.2); background: rgba(148, 163, 184, 0.04); color: #64748b; }

/* 按岗位时间线 */
.evo-detail { margin-top: 8px; }
.evo-detail-title {
  font-family: 'SimSun', 'Songti SC', serif; font-size: 16px; font-weight: 700;
  color: #2a1a0e; letter-spacing: 1px; margin: 0 0 4px;
}
.evo-subtitle { font-size: 12px; color: #6f5438; margin: 0 0 16px; }
.evo-timeline { display: flex; flex-direction: column; gap: 14px; }
.evo-period-card {
  padding: 14px 18px; border-left: 3px solid #3b2412;
  background: rgba(251, 243, 226, 0.5);
  border-top: 1px solid rgba(87, 64, 36, 0.18);
  border-right: 1px solid rgba(87, 64, 36, 0.18);
  border-bottom: 1px solid rgba(87, 64, 36, 0.18);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
}
.evo-period-head { margin-bottom: 10px; }
.evo-period-tag {
  font-family: 'Georgia', serif; font-size: 14px; font-weight: 700;
  color: #3b2412; letter-spacing: 1px;
}
.evo-change-group { display: flex; align-items: center; gap: 6px; margin-bottom: 6px; flex-wrap: wrap; }
.evo-change-group:last-child { margin-bottom: 0; }
.evo-change-icon { font-size: 14px; font-weight: 700; width: 20px; text-align: center; flex-shrink: 0; }
.evo-change-group.add .evo-change-icon { color: #10b981; }
.evo-change-group.remove .evo-change-icon { color: #ef4444; }
.evo-change-group.up .evo-change-icon { color: #f59e0b; }
.evo-change-group.down .evo-change-icon { color: #94a3b8; }
.evo-change-label { font-size: 12px; color: #5a3d28; flex-shrink: 0; }
.evo-skill-tag { font-size: 11px; padding: 2px 8px; font-family: 'SimSun', 'Songti SC', serif; letter-spacing: 0.3px; }
.evo-skill-tag.add { border: 1px solid rgba(16, 185, 129, 0.2); background: rgba(16, 185, 129, 0.06); color: #059669; }
.evo-skill-tag.remove { border: 1px solid rgba(239, 68, 68, 0.15); background: rgba(239, 68, 68, 0.04); color: #dc2626; text-decoration: line-through; }
.evo-skill-tag.up { border: 1px solid rgba(245, 158, 11, 0.2); background: rgba(245, 158, 11, 0.06); color: #d97706; }
.evo-skill-tag.down { border: 1px solid rgba(148, 163, 184, 0.2); background: rgba(148, 163, 184, 0.04); color: #64748b; }

/* 演化 meta（更新说明 + 数据源） */
.evo-meta {
  display: flex; flex-direction: column; gap: 4px;
  margin-top: 12px; padding-top: 10px;
  border-top: 1px dashed rgba(87, 64, 36, 0.22);
  font-size: 11px; color: rgba(87, 64, 36, 0.85);
}
.evo-meta-item { display: flex; gap: 6px; align-items: baseline; flex-wrap: wrap; }
.meta-label {
  flex-shrink: 0; font-size: 10px; color: #6f5438;
  padding: 1px 6px; border: 1px solid rgba(87, 64, 36, 0.2); background: rgba(243, 230, 203, 0.4);
}

.evo-empty {
  display: flex; align-items: center; justify-content: center;
  height: 160px; font-family: 'SimSun', 'Songti SC', serif;
  font-size: 13px; color: #6f5438;
}

/* ===== 图例 ===== */
.graph-legend {
  position: absolute; bottom: 14px; left: 14px;
  display: flex; gap: 14px; padding: 8px 14px;
  background: rgba(251, 243, 226, 0.92);
  border: 1px solid rgba(87, 64, 36, 0.28);
  box-shadow: inset 0 0 0 1px rgba(255, 252, 240, 0.4);
  font-family: 'SimSun', 'Songti SC', serif;
  font-size: 11px; color: #5a3d28; flex-wrap: wrap; align-items: center;
}
.legend-title { font-weight: 700; color: #3b2412; margin-right: 2px; }
.legend-group { display: flex; align-items: center; gap: 8px; }
.legend-group-label { font-size: 10px; color: #6f5438; margin-right: 2px; }
.legend-sep { width: 1px; height: 18px; background: rgba(87, 64, 36, 0.28); }
.legend-item { display: flex; align-items: center; gap: 6px; }
/* 级别：迷你药丸（底色=级别，奶油文字内嵌）——与真实技能药丸同一造型 */
.legend-pill {
  display: inline-flex; align-items: center; justify-content: center;
  width: 42px; height: 22px; border-radius: 11px; color: #fbf3e2;
  font-size: 11px; font-weight: 700; font-family: 'SimSun', 'Songti SC', serif;
  border: 1px solid #2a1a0e;
}
.legend-pill.junior { background: #2f6b46; }
.legend-pill.mid { background: #b45309; }
.legend-pill.senior { background: #7a2a22; }
/* 趋势：深色迷你胶囊 + 奶油符号（▲/▼/●）——与技能药丸内嵌符号一致 */
.legend-glyph {
  display: inline-flex; align-items: center; justify-content: center;
  width: 20px; height: 20px; border-radius: 10px; background: #3b2412; color: #fbf3e2;
  font-size: 11px; line-height: 1; border: 1px solid #2a1a0e;
}

/* ===== Responsive ===== */
@media (max-width: 900px) {
  .graph-toolbar { flex-direction: column; gap: 10px; align-items: flex-start; }
  .view-toggle button { padding: 5px 10px; font-size: 12px; }
  .graph-main { flex-direction: column; }
  .graph-canvas { height: 450px; }
  .graph-center { min-height: 450px; }
  .graph-aside { width: 100%; }
  .market-grid { grid-template-columns: 1fr; }
}
</style>

<template>
	<div class="apikey-page">
		<div class="apikey-inner">
			<header class="apikey-head">
				<div class="head-title">
					<span class="head-kicker">API KEY MANAGEMENT</span>
					<h1 class="head-h1">API Key 管理</h1>
					<p class="head-sub">配置 DeepSeek 大模型 Key，解锁能力画像与匹配报告中的个性化学习路径</p>
				</div>
			</header>

			<section class="paper-card">
				<div class="card-head">
					<span class="card-index">01</span>
					<span class="card-title">DeepSeek 配置</span>
				</div>
				<ApiKeyPanel
					provider="deepseek"
					context="该 Key 仅用于你自己的能力画像与学习路径生成；清除后相关功能恢复为未配置状态。"
				/>
			</section>
		</div>
	</div>
</template>

<script setup lang="ts">
import ApiKeyPanel from '@/components/ApiKeyPanel.vue'
</script>

<style scoped>
.apikey-page {
  min-height: calc(100vh - 56px);
  padding: 36px 24px 48px;
  background: #f4e9d6;
}
.apikey-inner {
  max-width: 860px;
  margin: 0 auto;
}
.apikey-head {
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
</style>

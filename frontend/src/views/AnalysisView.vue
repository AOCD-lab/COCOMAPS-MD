<template>
  <div class="analysis-view">
    <!-- Main Content -->
    <div class="main-content">
      <div class="container" v-if="systemsStore.isLoading">Loading analysis...</div>
      <div class="container" v-else-if="systemsStore.error" role="alert">{{ systemsStore.error }}</div>
      <div class="container" v-else>
        <h1 v-if="systemsStore.currentSystem">{{ systemsStore.currentSystem.name }}</h1>
        <h1 v-else>Select a System</h1>
        <p class="subtitle" v-if="systemsStore.currentSystem">
          Chain {{ systemsStore.currentSystem.chain1 || 'A' }} ↔ Chain {{ systemsStore.currentSystem.chain2 || 'B' }} Residue Interactions Across {{ systemsStore.currentSystem.frames }} Frames
        </p>
        <p class="subtitle" v-else>
          Open a completed job from the Jobs page to view its analysis
        </p>

        <ChartSelector />
        <div class="analysis-card">
          <ChartContainer />
          <ControlsPanel />
        </div>
        <StatsPanel v-if="systemsStore.currentSystem" />
        <ConservationAnalysis v-if="systemsStore.currentSystem" />
      </div>
    </div>

    <UploadModal ref="uploadModal" />

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSystemsStore } from '../stores/systemsStore'
import { useChartUiStore } from '../stores/chartUiStore'
import { useChartUrlSync } from '../composables/useChartUrlSync'
import ChartSelector from '../components/analysis/ChartSelector.vue'
import ControlsPanel from '../components/analysis/ControlsPanel.vue'
import ChartContainer from '../components/analysis/ChartContainer.vue'
import StatsPanel from '../components/analysis/StatsPanel.vue'
import ConservationAnalysis from '../components/analysis/ConservationAnalysis.vue'
import UploadModal from '../components/analysis/UploadModal.vue'
import AppFooter from '../components/layout/AppFooter.vue'

const systemsStore = useSystemsStore()
const chartUiStore = useChartUiStore()
const route = useRoute()
const router = useRouter()
const uploadModal = ref(null)

useChartUrlSync({ route, router, chartUiStore })

// The URL is the source of truth, including when Vue reuses this view.
watch(() => route.params.jobId, (jobId) => {
  if (jobId) systemsStore.loadAnalysisByJobId(jobId)
}, { immediate: true })

</script>

<style scoped>
.analysis-view {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

/* Main Content */
.main-content {
  flex: 1;
}

.container {
  max-width: 1600px;
  margin: 0 auto;
  padding: 40px;
}

h1 {
  font-size: 48px;
  line-height: 1.1;
  font-weight: 600;
  letter-spacing: -0.02em;
  text-align: center;
  margin-bottom: 12px;
  color: #1d1d1f;
}

.subtitle {
  font-size: 20px;
  line-height: 1.4;
  font-weight: 400;
  text-align: center;
  color: #6e6e73;
  margin-bottom: 40px;
}

.analysis-card {
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 2px 16px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  margin-bottom: 32px;
}

@media (max-width: 768px) {
  h1 {
    font-size: 32px;
  }

  .container {
    padding: 24px;
  }
}
</style>

<template>
  <div class="interface-patches-wrapper">
    <MolStarViewer
      v-if="systemsStore.currentSystem?.id"
      :system-id="systemsStore.currentSystem.id"
      :job-id="systemsStore.currentSystem.jobId"
      :selected-residues="selectedResiduesForViewer"
      highlight-mode="ball-and-stick"
      class="structure-viewer"
    />
    <div class="viz-controls">
      <h3 class="panel-title">3D Visualization</h3>
      <p class="panel-subtitle">Highlight residues in the structure by choosing a mode below.</p>
      <div class="mode-cards" role="tablist" aria-label="Highlight mode">
        <button
          type="button"
          role="tab"
          :aria-selected="viewMode === 'interfacePatches'"
          :class="['mode-card', { active: viewMode === 'interfacePatches' }]"
          @click="viewMode = 'interfacePatches'"
        >
          <span class="mode-card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="3"/>
              <circle cx="6" cy="6" r="2"/>
              <circle cx="18" cy="6" r="2"/>
              <circle cx="6" cy="18" r="2"/>
              <circle cx="18" cy="18" r="2"/>
              <line x1="7.5" y1="7.5" x2="10" y2="10"/>
              <line x1="16.5" y1="7.5" x2="14" y2="10"/>
              <line x1="7.5" y1="16.5" x2="10" y2="14"/>
              <line x1="16.5" y1="16.5" x2="14" y2="14"/>
            </svg>
          </span>
          <span class="mode-card-text">
            <span class="mode-card-title">Interface Patches</span>
            <span class="mode-card-desc">Connected residue components across interacting chains</span>
          </span>
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="viewMode === 'pairs'"
          :class="['mode-card', { active: viewMode === 'pairs' }]"
          @click="viewMode = 'pairs'"
        >
          <span class="mode-card-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="8" cy="12" r="4"/>
              <circle cx="16" cy="12" r="4"/>
              <line x1="12" y1="12" x2="12" y2="12"/>
              <path d="M11 10l2 2-2 2"/>
            </svg>
          </span>
          <span class="mode-card-text">
            <span class="mode-card-title">Most Conserved Residue Pairs</span>
            <span class="mode-card-desc">Individual residue pairs ranked by conservation</span>
          </span>
        </button>
      </div>
    </div>

    <template v-if="viewMode === 'interfacePatches'">
      <div v-if="analysisStore.loading.interfacePatches" class="loading-state">
        <div class="loading-spinner"></div>
        <p>Loading interface patches...</p>
      </div>
      <div v-else-if="analysisStore.errors.interfacePatches" class="error-state">
        <p>{{ analysisStore.errors.interfacePatches }}</p>
        <p class="hint">Run the pipeline to generate interface patch data.</p>
      </div>
      <div v-else>
        <div class="slider-section interface-patch-slider">
          <label for="interface-patch-conservation-slider" class="slider-label">Interface Patch Conservation Threshold</label>
          <div class="slider-container">
            <div class="slider-control">
              <input
                id="interface-patch-conservation-slider"
                type="range"
                min="0.5"
                max="1"
                step="0.1"
                :value="chartUiStore.interfacePatchThreshold"
                @input="updateInterfacePatchThreshold"
              />
              <div class="slider-ticks">
                <span
                  v-for="tick in interfacePatchConservationTicks"
                  :key="tick.value"
                  class="slider-tick"
                >
                  <span class="slider-tick-label">{{ tick.label }}</span>
                </span>
              </div>
            </div>
            <div class="slider-value-input">
              <input
                type="number"
                :value="interfacePatchThresholdPercent"
                @input="updateInterfacePatchThresholdFromInput"
                @blur="validateInterfacePatchThresholdInput"
                min="50"
                max="100"
                step="10"
                class="value-input"
              />
              <span class="percent-symbol">%</span>
            </div>
          </div>
          <p class="slider-description">
            Build patches from residue pairs present in at least {{ interfacePatchThresholdPercent }}% of frames
          </p>
        </div>

        <div v-if="interfacePatches.length === 0" class="empty-state">
          <p>No interface patches meet the {{ interfacePatchThresholdPercent }}% conservation threshold.</p>
          <p class="hint">Lower the interface patch threshold to include less persistent residue connections.</p>
        </div>
        <div v-else class="interface-patches-content">
        <p class="selection-hint">
          <span class="radio-icon" aria-hidden="true">◉</span>
          The largest interface patch is highlighted by default. Equal-size leaders are highlighted together.
        </p>
        <div class="interface-patches-list" role="listbox" aria-label="Interface patches" aria-multiselectable="true">
        <div
          v-for="interfacePatch in visibleInterfacePatches"
          :key="interfacePatch.signature"
          class="interface-patch-card"
          :class="{ selected: isInterfacePatchActive(interfacePatch.id) }"
          role="option"
          :aria-selected="isInterfacePatchActive(interfacePatch.id)"
          tabindex="0"
          @click="selectInterfacePatch(interfacePatch.id)"
          @keydown.enter.prevent="selectInterfacePatch(interfacePatch.id)"
          @keydown.space.prevent="selectInterfacePatch(interfacePatch.id)"
        >
          <div class="interface-patch-header">
            <span class="interface-patch-radio" :class="{ checked: isInterfacePatchActive(interfacePatch.id) }" aria-hidden="true" />
            <span class="interface-patch-id">Interface Patch {{ interfacePatch.id }}</span>
            <span class="interface-patch-size">{{ interfacePatch.size }} residues</span>
            <span class="interface-patch-chains">Chains: {{ interfacePatch.chains?.join(', ') || '—' }}</span>
            <div class="view-toggle" @click.stop>
              <button
                type="button"
                class="view-toggle-btn"
                :class="{ active: getInterfacePatchViewMode(interfacePatch.id) === 'graph' }"
                @click="setInterfacePatchViewMode(interfacePatch.id, 'graph')"
              >
                Graph
              </button>
              <button
                type="button"
                class="view-toggle-btn"
                :class="{ active: getInterfacePatchViewMode(interfacePatch.id) === 'table' }"
                @click="setInterfacePatchViewMode(interfacePatch.id, 'table')"
              >
                Table
              </button>
            </div>
          </div>
          <div class="interface-patch-body">
            <div
              v-if="getInterfacePatchViewMode(interfacePatch.id) === 'graph'"
              class="graph-wrapper"
            >
              <InterfacePatchGraph
                :interfacePatch="interfacePatch"
                :expanded="expandedInterfacePatchId === interfacePatch.id"
              />
              <button
                type="button"
                class="expand-btn graph-expand-btn"
                :class="{ expanded: expandedInterfacePatchId === interfacePatch.id }"
                @click.stop="toggleExpandedInterfacePatch(interfacePatch.id)"
                aria-label="Expand or collapse graph height"
              >
                <span v-if="expandedInterfacePatchId === interfacePatch.id">▴</span>
                <span v-else>▾</span>
              </button>
            </div>
            <div v-else class="residues-table-wrap">
              <table class="residues-table">
                <thead>
                  <tr>
                    <th>Residue</th>
                    <th>Connected to (in patch)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(res, idx) in interfacePatch.residues" :key="`${res.chain}-${res.resNum}-${idx}`">
                    <td>{{ formatInterfacePatchResidue(res) }}</td>
                    <td class="connected-cell">
                      <span v-if="!res.connectedTo || res.connectedTo.length === 0" class="muted">—</span>
                      <span v-else class="connected-list">
                        <span
                          v-for="(conn, i) in res.connectedTo"
                          :key="`${conn.chain}-${conn.resNum}-${i}`"
                          class="connected-tag"
                        >
                          {{ formatInterfacePatchResidue(conn) }}
                        </span>
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
        </div>
        <div v-if="hasHiddenInterfacePatches" class="interface-patches-footer">
          <button
            type="button"
            class="view-more-patches-btn"
            :aria-expanded="showAllInterfacePatches"
            @click="toggleInterfacePatchVisibility"
          >
            <span class="view-more-patches-copy">
              <span class="view-more-patches-label">{{ viewMoreInterfacePatchesLabel }}</span>
              <span class="view-more-patches-meta">{{ interfacePatchesSummary }}</span>
            </span>
            <span class="view-more-patches-icon" :class="{ expanded: showAllInterfacePatches }" aria-hidden="true">
              <svg viewBox="0 0 20 20" fill="none">
                <path d="M5 8l5 5 5-5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </span>
          </button>
        </div>
        </div>
      </div>
    </template>
    <template v-else-if="viewMode === 'pairs'">
    <div class="pairs-content">
      <div v-if="!mostConservedList || mostConservedList.length === 0" class="empty-state">
        <p>No conserved pairs for this system yet.</p>
        <p class="hint">Run the pipeline and ensure you have interaction data. Conservation thresholds apply from the Conservation Analysis panel.</p>
      </div>
      <div v-else>
        <p class="selection-hint">
          <span class="check-icon" aria-hidden="true">☑</span>
          All pairs are selected by default. Click a row or its checkbox to show only the pairs you want in the 3D viewer.
        </p>

        <!-- Pair Conservation Threshold Slider -->
        <div class="slider-section">
          <label for="pairs-conservation-slider" class="slider-label">Residue Pair Conservation Threshold</label>
          <div class="slider-container">
            <div class="slider-control">
              <input
                id="pairs-conservation-slider"
                type="range"
                min="0"
                max="1"
                step="0.1"
                :value="chartUiStore.currentThreshold"
                @input="updateThreshold"
              />
              <div class="slider-ticks">
                <span
                  v-for="tick in conservationTicks"
                  :key="tick.value"
                  class="slider-tick"
                >
                  <span class="slider-tick-label">{{ tick.label }}</span>
                </span>
              </div>
            </div>
            <div class="slider-value-input">
              <input
                type="number"
                :value="thresholdPercent"
                @input="updateThresholdFromInput"
                @blur="validateThresholdInput"
                min="0"
                max="100"
                step="1"
                class="value-input"
              />
              <span class="percent-symbol">%</span>
            </div>
          </div>
          <p class="slider-description">Show pairs with conservation ≥ {{ thresholdPercent }}%</p>
        </div>

        <!-- Toolbar: search + select/deselect (immediately above table) -->
        <div class="pairs-toolbar">
          <div class="search-box">
            <svg class="search-icon" viewBox="0 0 20 20" width="16" height="16"><circle cx="8.5" cy="8.5" r="5.5" fill="none" stroke="currentColor" stroke-width="2"/><line x1="12.5" y1="12.5" x2="17" y2="17" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            <input
              type="text"
              v-model="searchQuery"
              placeholder="Search residues…"
              class="search-input"
            />
            <button v-if="searchQuery" type="button" class="search-clear" @click="searchQuery = ''">✕</button>
          </div>
          <button type="button" class="toolbar-btn" @click="selectAllPairs">Select all</button>
          <button type="button" class="toolbar-btn" @click="deselectAllPairs">Deselect all</button>
          <span class="pairs-count">{{ selectedPairKeys.length }} / {{ filteredPairsList.length }} selected</span>
        </div>

        <div class="pairs-table-wrap">
          <table class="pairs-table">
            <thead>
              <tr>
                <th class="col-check">
                  <input
                    type="checkbox"
                    :checked="allFilteredSelected"
                    :indeterminate="someFilteredSelected && !allFilteredSelected"
                    @change="toggleAllFiltered"
                    aria-label="Select all visible pairs"
                  />
                </th>
                <th class="col-pair sortable" @click="toggleSort('pair')">
                  Residue Pair
                  <span class="sort-arrow" :class="sortIndicatorClass('pair')"></span>
                </th>
                <th class="col-conservation sortable" @click="toggleSort('conservation')">
                  Conservation
                  <span class="sort-arrow" :class="sortIndicatorClass('conservation')"></span>
                </th>
                <th class="col-frames sortable" @click="toggleSort('frames')">
                  Frames
                  <span class="sort-arrow" :class="sortIndicatorClass('frames')"></span>
                </th>
              </tr>
            </thead>
            <tbody>
              <template v-for="item in filteredPairsList" :key="item.pair">
                <tr
                  class="pair-data-row"
                  :class="{ selected: isPairSelected(item.pair) }"
                  @click="togglePair(item.pair)"
                >
                  <td class="col-check">
                    <input
                      type="checkbox"
                      :checked="isPairSelected(item.pair)"
                      @click.stop
                      @change="togglePair(item.pair)"
                      :aria-label="`Toggle ${item.pair} in 3D view`"
                    />
                  </td>
                  <td class="col-pair">
                    <span class="pair-name">{{ item.pair }}</span>
                  </td>
                  <td class="col-conservation">
                    <div class="conservation-cell">
                      <div class="conservation-bar-track">
                        <div
                          class="conservation-bar-fill"
                          :style="{ width: conservationPercent(item) + '%', backgroundColor: conservationColor(item) }"
                        ></div>
                      </div>
                      <span class="conservation-value">{{ conservationPercent(item) }}%</span>
                    </div>
                  </td>
                  <td class="col-frames">
                    <span class="frames-value">{{ item.frameCount }}</span>
                    <span class="frames-total"> / {{ systemsStore.totalFrames }}</span>
                  </td>
                </tr>
              </template>
              <tr v-if="filteredPairsList.length === 0" class="no-results-row">
                <td colspan="4">
                  <div class="no-results">No pairs match "{{ searchQuery }}"</div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAnalysisStore } from '../../stores/analysisStore'
import { useChartUiStore } from '../../stores/chartUiStore'
import { useSystemsStore } from '../../stores/systemsStore'
import { useConservationStatistics } from '../../composables/useConservationStatistics'
import { parseResidueId, formatResidueId, getInteractionBaseColor, getTextColorForBg } from '../../utils/chartHelpers'
import {
  buildInterfacePatchCache,
  INTERFACE_PATCH_THRESHOLDS,
  normalizeInterfacePatchThreshold
} from '../../utils/interfacePatches'
import MolStarViewer from '../analysis/MolStarViewer.vue'
import InterfacePatchGraph from './InterfacePatchGraph.vue'

const analysisStore = useAnalysisStore()
const chartUiStore = useChartUiStore()
const systemsStore = useSystemsStore()
const { statistics } = useConservationStatistics()

const viewMode = ref('interfacePatches')
const selectedInterfacePatchId = ref(null)
const hasManualInterfacePatchSelection = ref(false)
const interfacePatchViewMode = ref({})
const expandedInterfacePatchId = ref(null)
const selectedPairKeys = ref([])
const showAllInterfacePatches = ref(false)
const initialVisibleInterfacePatchCount = 2

// --- New state for table features ---
const searchQuery = ref('')
const sortColumn = ref('conservation') // 'pair' | 'conservation' | 'frames' | 'types'
const sortDirection = ref('desc')       // 'asc' | 'desc'

const mostConservedList = computed(() => statistics.value?.residue?.mostConservedList ?? [])

const interfacePatchCache = computed(() => buildInterfacePatchCache(
  analysisStore.interfacePatchEdges,
  analysisStore.interfacePatchTotalFrames || systemsStore.totalFrames,
  analysisStore.interfacePatchMinimumSize
))

const interfacePatches = computed(() => {
  const threshold = normalizeInterfacePatchThreshold(chartUiStore.interfacePatchThreshold)
  return interfacePatchCache.value.get(threshold) ?? []
})

const sortedInterfacePatches = computed(() => {
  return [...interfacePatches.value]
    .map((interfacePatch, index) => ({ interfacePatch, index }))
    .sort((a, b) => {
      const sizeDelta = (Number(b.interfacePatch.size) || 0) - (Number(a.interfacePatch.size) || 0)
      return sizeDelta || a.index - b.index
    })
    .map(({ interfacePatch }) => interfacePatch)
})

const hiddenInterfacePatchCount = computed(() => {
  return Math.max(sortedInterfacePatches.value.length - initialVisibleInterfacePatchCount, 0)
})

const hasHiddenInterfacePatches = computed(() => hiddenInterfacePatchCount.value > 0)

const visibleInterfacePatches = computed(() => {
  if (showAllInterfacePatches.value || !hasHiddenInterfacePatches.value) {
    return sortedInterfacePatches.value
  }
  return sortedInterfacePatches.value.slice(0, initialVisibleInterfacePatchCount)
})

const defaultInterfacePatchIds = computed(() => {
  const largestPatch = sortedInterfacePatches.value[0]
  if (!largestPatch) return []

  const largestSize = Number(largestPatch.size) || 0
  return sortedInterfacePatches.value
    .filter((interfacePatch) => (Number(interfacePatch.size) || 0) === largestSize)
    .map((interfacePatch) => interfacePatch.id)
})

const activeInterfacePatchIds = computed(() => {
  if (!hasManualInterfacePatchSelection.value) {
    return defaultInterfacePatchIds.value
  }

  return selectedInterfacePatchId.value === null ? [] : [selectedInterfacePatchId.value]
})

const activeInterfacePatchIdSet = computed(() => new Set(activeInterfacePatchIds.value))

const viewMoreInterfacePatchesLabel = computed(() => {
  if (showAllInterfacePatches.value) {
    return `Show first ${initialVisibleInterfacePatchCount} interface patches`
  }
  const suffix = hiddenInterfacePatchCount.value === 1 ? 'patch' : 'patches'
  return `View ${hiddenInterfacePatchCount.value} more interface ${suffix}`
})

const interfacePatchesSummary = computed(() => {
  const total = sortedInterfacePatches.value.length
  const visible = visibleInterfacePatches.value.length
  return `Showing ${visible} of ${total}, largest first`
})

// --- Search + Sort ---
const filteredPairsList = computed(() => {
  let list = [...mostConservedList.value]

  // Search filter
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.trim().toLowerCase()
    list = list.filter(item => item.pair.toLowerCase().includes(q))
  }

  // Sort
  list.sort((a, b) => {
    let cmp = 0
    switch (sortColumn.value) {
      case 'pair':
        cmp = a.pair.localeCompare(b.pair)
        break
      case 'conservation':
        cmp = (a.frameCount / (systemsStore.totalFrames || 1)) - (b.frameCount / (systemsStore.totalFrames || 1))
        break
      case 'frames':
        cmp = a.frameCount - b.frameCount
        break
    }
    return sortDirection.value === 'asc' ? cmp : -cmp
  })

  return list
})

function toggleSort(col) {
  if (sortColumn.value === col) {
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortColumn.value = col
    sortDirection.value = col === 'pair' ? 'asc' : 'desc'
  }
}

function sortIndicatorClass(col) {
  if (sortColumn.value !== col) return 'inactive'
  return sortDirection.value === 'asc' ? 'asc' : 'desc'
}

// --- Conservation display helpers ---
function conservationPercent(item) {
  const totalFrames = systemsStore.totalFrames || 1
  return Math.round((item.frameCount / totalFrames) * 100)
}

function conservationColor(item) {
  const pct = conservationPercent(item) / 100
  // Gradient: light blue → deep blue
  if (pct >= 0.9) return '#0D47A1'
  if (pct >= 0.7) return '#1E88E5'
  if (pct >= 0.5) return '#42A5F5'
  if (pct >= 0.3) return '#90CAF9'
  return '#BBDEFB'
}

function formatInterfacePatchResidue(residue) {
  if (!residue) return '—'
  const formatted = formatResidueId(residue.resName, residue.resNum, residue.chain)
  if (formatted) return formatted
  if (residue.resNum !== undefined && residue.resNum !== null && residue.chain) {
    return `${residue.resNum}_${residue.chain}`
  }
  return '—'
}

// --- Header checkbox (select/deselect all filtered) ---
const allFilteredSelected = computed(() => {
  if (filteredPairsList.value.length === 0) return false
  return filteredPairsList.value.every(item => isPairSelected(item.pair))
})
const someFilteredSelected = computed(() => {
  return filteredPairsList.value.some(item => isPairSelected(item.pair))
})
function toggleAllFiltered() {
  if (allFilteredSelected.value) {
    // Deselect all filtered
    const filteredKeys = new Set(filteredPairsList.value.map(p => p.pair))
    selectedPairKeys.value = selectedPairKeys.value.filter(k => !filteredKeys.has(k))
  } else {
    // Select all filtered (keep existing selections too)
    const existing = new Set(selectedPairKeys.value)
    filteredPairsList.value.forEach(item => existing.add(item.pair))
    selectedPairKeys.value = Array.from(existing)
  }
}

// --- Pair selection ---
watch(
  [viewMode, mostConservedList],
  () => {
    if (viewMode.value === 'pairs' && mostConservedList.value.length > 0 && selectedPairKeys.value.length === 0) {
      selectedPairKeys.value = mostConservedList.value.map((p) => p.pair)
    }
  },
  { immediate: true }
)

watch(mostConservedList, (list) => {
  if (list.length > 0 && viewMode.value === 'pairs') {
    selectedPairKeys.value = list.map((p) => p.pair)
  }
}, { deep: true })

// --- Interface patch helpers ---
function selectInterfacePatch(id) {
  if (hasManualInterfacePatchSelection.value && selectedInterfacePatchId.value === id) {
    selectedInterfacePatchId.value = null
  } else {
    selectedInterfacePatchId.value = id
  }
  hasManualInterfacePatchSelection.value = true
}
function isInterfacePatchActive(id) {
  return activeInterfacePatchIdSet.value.has(id)
}
function getInterfacePatchViewMode(id) {
  const current = interfacePatchViewMode.value[id]
  return current === 'table' ? 'table' : 'graph'
}
function setInterfacePatchViewMode(id, mode) {
  interfacePatchViewMode.value = { ...interfacePatchViewMode.value, [id]: mode }
}
function toggleExpandedInterfacePatch(id) {
  expandedInterfacePatchId.value = expandedInterfacePatchId.value === id ? null : id
}

function toggleInterfacePatchVisibility() {
  const nextValue = !showAllInterfacePatches.value
  showAllInterfacePatches.value = nextValue

  if (!nextValue) {
    const visibleIds = new Set(visibleInterfacePatches.value.map((interfacePatch) => interfacePatch.id))
    if (hasManualInterfacePatchSelection.value && selectedInterfacePatchId.value !== null && !visibleIds.has(selectedInterfacePatchId.value)) {
      selectedInterfacePatchId.value = null
    }
    if (expandedInterfacePatchId.value !== null && !visibleIds.has(expandedInterfacePatchId.value)) {
      expandedInterfacePatchId.value = null
    }
  }
}

function pairStringToResidues(pairStr) {
  if (!pairStr || typeof pairStr !== 'string') return []
  const parts = pairStr.split(/\s*↔\s*/).map((s) => s.trim()).filter(Boolean)
  if (parts.length !== 2) return []
  const r1 = parseResidueId(parts[0])
  const r2 = parseResidueId(parts[1])
  const out = []
  if (r1) out.push({ chain: r1.chain, resNum: Number(r1.resNum), resName: r1.resName })
  if (r2) out.push({ chain: r2.chain, resNum: Number(r2.resNum), resName: r2.resName })
  return out
}

function isPairSelected(pairKey) {
  return selectedPairKeys.value.includes(pairKey)
}
function togglePair(pairKey) {
  if (isPairSelected(pairKey)) {
    selectedPairKeys.value = selectedPairKeys.value.filter((k) => k !== pairKey)
  } else {
    selectedPairKeys.value = [...selectedPairKeys.value, pairKey]
  }
}
function selectAllPairs() {
  selectedPairKeys.value = filteredPairsList.value.map((p) => p.pair)
}
function deselectAllPairs() {
  selectedPairKeys.value = []
}

const selectedInterfacePatchResidues = computed(() => {
  if (interfacePatches.value.length === 0 || activeInterfacePatchIdSet.value.size === 0) return null

  const seen = new Set()
  const residues = []

  sortedInterfacePatches.value.forEach((interfacePatch) => {
    if (!activeInterfacePatchIdSet.value.has(interfacePatch.id)) return

    const interfacePatchResidues = interfacePatch.residues ?? []
    interfacePatchResidues.forEach((res) => {
      const key = `${res.chain}-${res.resNum}`
      if (!seen.has(key)) {
        seen.add(key)
        residues.push(res)
      }
    })
  })

  return residues.length ? residues : null
})

const selectedPairsResidues = computed(() => {
  if (viewMode.value !== 'pairs' || selectedPairKeys.value.length === 0) return null
  const seen = new Set()
  const list = []
  selectedPairKeys.value.forEach((pairKey) => {
    pairStringToResidues(pairKey).forEach((r) => {
      const key = `${r.chain}-${r.resNum}`
      if (!seen.has(key)) {
        seen.add(key)
        list.push(r)
      }
    })
  })
  return list.length ? list : null
})

const selectedResiduesForViewer = computed(() => {
  if (viewMode.value === 'interfacePatches') return selectedInterfacePatchResidues.value
  return selectedPairsResidues.value
})

watch([
  () => analysisStore.interfacePatchEdges,
  () => chartUiStore.interfacePatchThreshold
], () => {
  showAllInterfacePatches.value = false
  selectedInterfacePatchId.value = null
  hasManualInterfacePatchSelection.value = false
  expandedInterfacePatchId.value = null
})

// --- Interface Patch Conservation Threshold slider ---
const interfacePatchThresholdPercent = computed(() => (
  Math.round(normalizeInterfacePatchThreshold(chartUiStore.interfacePatchThreshold) * 100)
))

const interfacePatchConservationTicks = INTERFACE_PATCH_THRESHOLDS.map((value) => ({
  value,
  label: Math.round(value * 100)
}))

const setInterfacePatchThreshold = (value) => {
  chartUiStore.setInterfacePatchThreshold(normalizeInterfacePatchThreshold(value))
}

const updateInterfacePatchThreshold = (event) => {
  setInterfacePatchThreshold(parseFloat(event.target.value))
}

const updateInterfacePatchThresholdFromInput = (event) => {
  const value = parseFloat(event.target.value)
  if (!Number.isNaN(value) && value >= 50 && value <= 100) {
    setInterfacePatchThreshold(value / 100)
  }
}

const validateInterfacePatchThresholdInput = (event) => {
  const value = parseFloat(event.target.value)
  if (Number.isNaN(value)) {
    event.target.value = interfacePatchThresholdPercent.value
    return
  }
  setInterfacePatchThreshold(value / 100)
  event.target.value = interfacePatchThresholdPercent.value
}

// --- Pair Conservation Threshold slider ---
const thresholdPercent = computed(() => Math.round(chartUiStore.currentThreshold * 100))

const conservationTicks = computed(() => {
  const ticks = []
  for (let value = 0; value <= 1.0 + 0.0001; value += 0.1) {
    ticks.push({
      value: parseFloat(value.toFixed(2)),
      label: Math.round(value * 100)
    })
  }
  return ticks
})

const updateThreshold = (event) => {
  chartUiStore.setThreshold(parseFloat(event.target.value))
}

const updateThresholdFromInput = (event) => {
  const value = parseFloat(event.target.value)
  if (!isNaN(value) && value >= 0 && value <= 100) {
    chartUiStore.setThreshold(value / 100)
  }
}

const validateThresholdInput = (event) => {
  let value = parseFloat(event.target.value)
  if (isNaN(value)) {
    event.target.value = thresholdPercent.value
    return
  }
  value = Math.max(0, Math.min(100, value))
  event.target.value = value
  chartUiStore.setThreshold(value / 100)
}
</script>

<style scoped>
.interface-patches-wrapper {
  min-height: 400px;
  padding: 8px 0;
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.structure-viewer {
  flex-shrink: 0;
}

.loading-state,
.error-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  text-align: center;
  color: #6e6e73;
  font-size: 17px;
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #d2d2d7;
  border-top-color: #1d1d1f;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-state p,
.empty-state p {
  margin: 0 0 8px 0;
}

.hint {
  font-size: 14px;
  color: #86868b;
  margin-top: 8px;
}

.hint code {
  background: #f5f5f7;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
}

.panel-title {
  font-size: 22px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 4px 0;
}

.panel-subtitle {
  font-size: 15px;
  color: #6e6e73;
  margin: 0 0 16px 0;
}

.viz-controls {
  margin-bottom: 20px;
}

.mode-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.mode-card {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px 18px;
  background: #f5f5f7;
  border: 2px solid #e8e8ed;
  border-radius: 14px;
  cursor: pointer;
  text-align: left;
  font-family: inherit;
  transition: all 0.2s ease;
}

.mode-card:hover {
  border-color: #d2d2d7;
  background: #f0f0f2;
}

.mode-card.active {
  background: #ffffff;
  border-color: #007aff;
  box-shadow: 0 2px 10px rgba(0, 122, 255, 0.12);
}

.mode-card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  background: #e8e8ed;
  border-radius: 10px;
  color: #6e6e73;
  transition: all 0.2s ease;
}

.mode-card.active .mode-card-icon {
  background: rgba(0, 122, 255, 0.1);
  color: #007aff;
}

.mode-card-icon svg {
  width: 20px;
  height: 20px;
}

.mode-card-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.mode-card-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  line-height: 1.3;
}

.mode-card-desc {
  font-size: 12px;
  font-weight: 400;
  color: #86868b;
  line-height: 1.4;
}

.mode-card.active .mode-card-title {
  color: #007aff;
}

.selection-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: #86868b;
  margin: 0 0 16px 0;
}

.radio-icon,
.check-icon {
  color: #007aff;
  font-size: 16px;
}

.pairs-content .empty-state {
  margin-top: 0;
}

.pairs-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.toolbar-btn {
  padding: 8px 14px;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: #ffffff;
  color: #1d1d1f;
  transition: background 0.15s, border-color 0.15s;
}

.toolbar-btn:hover {
  background: #f5f5f7;
  border-color: #c7c7cc;
}

.pairs-count {
  font-size: 13px;
  color: #6e6e73;
  font-weight: 500;
}

/* =================== Search Box =================== */
.search-box {
  position: relative;
  display: flex;
  align-items: center;
  flex: 1;
  max-width: 300px;
}
.search-icon {
  position: absolute;
  left: 12px;
  color: #86868b;
  pointer-events: none;
}
.search-input {
  width: 100%;
  padding: 8px 32px 8px 34px;
  font-size: 14px;
  border: 2px solid #d2d2d7;
  border-radius: 10px;
  background: #ffffff;
  color: #1d1d1f;
  font-family: inherit;
  transition: border-color 0.15s;
}
.search-input:focus {
  outline: none;
  border-color: #1d1d1f;
  box-shadow: 0 0 0 3px rgba(29, 29, 31, 0.08);
}
.search-input::placeholder {
  color: #a1a1a6;
}
.search-clear {
  position: absolute;
  right: 8px;
  background: none;
  border: none;
  font-size: 14px;
  color: #86868b;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 50%;
}
.search-clear:hover {
  color: #1d1d1f;
  background: #e8e8ed;
}

/* =================== Sortable Table =================== */
.pairs-table-wrap {
  overflow-x: auto;
  border: 1px solid #e8e8ed;
  border-radius: 12px;
  background: #ffffff;
}

.pairs-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.pairs-table thead th {
  text-align: left;
  padding: 12px 16px;
  background: #f5f5f7;
  color: #6e6e73;
  font-weight: 600;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  border-bottom: 1px solid #e8e8ed;
  white-space: nowrap;
  user-select: none;
}

.pairs-table thead th.sortable {
  cursor: pointer;
  transition: color 0.15s;
}
.pairs-table thead th.sortable:hover {
  color: #1d1d1f;
}

.col-check {
  width: 40px;
  text-align: center;
}
.col-check input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #007aff;
}
.col-pair { min-width: 180px; }
.col-conservation { min-width: 160px; }
.col-frames { min-width: 90px; }
.col-types { min-width: 100px; }

/* Sort arrows */
.sort-arrow {
  display: inline-block;
  width: 0;
  height: 0;
  margin-left: 6px;
  vertical-align: middle;
}
.sort-arrow.inactive::after {
  content: '⇅';
  font-size: 11px;
  opacity: 0.4;
}
.sort-arrow.asc::after {
  content: '↑';
  font-size: 13px;
  font-weight: 700;
  color: #1d1d1f;
}
.sort-arrow.desc::after {
  content: '↓';
  font-size: 13px;
  font-weight: 700;
  color: #1d1d1f;
}

/* Data rows */
.pair-data-row {
  cursor: pointer;
  transition: background 0.12s;
}
.pair-data-row td {
  padding: 10px 16px;
  border-bottom: 1px solid #f0f0f2;
  vertical-align: middle;
}
.pair-data-row:hover {
  background: #fafafa;
}
.pair-data-row.selected {
  background: #f0f7ff;
}

.pair-name {
  font-size: 13px;
  font-weight: 600;
  color: #1d1d1f;
  font-family: 'SF Mono', 'Monaco', 'Menlo', monospace;
}

/* Conservation bar */
.conservation-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}
.conservation-bar-track {
  flex: 1;
  height: 8px;
  background: #e8e8ed;
  border-radius: 4px;
  overflow: hidden;
  min-width: 60px;
}
.conservation-bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.3s ease;
}
.conservation-value {
  font-size: 13px;
  font-weight: 700;
  color: #1d1d1f;
  font-variant-numeric: tabular-nums;
  min-width: 36px;
  text-align: right;
}

/* Frames column */
.frames-value {
  font-weight: 600;
  color: #1d1d1f;
  font-variant-numeric: tabular-nums;
}
.frames-total {
  color: #86868b;
  font-size: 12px;
}

/* Type dots (compact) */
.col-types > div,
.col-types {
  display: flex;
  align-items: center;
  gap: 6px;
}
.type-dots {
  display: flex;
  gap: 3px;
  align-items: center;
}
.type-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.type-dot-more {
  font-size: 11px;
  font-weight: 600;
  color: #86868b;
}
.types-count {
  font-size: 12px;
  font-weight: 600;
  color: #6e6e73;
  margin-left: 2px;
}


/* No results */
.no-results-row td {
  border-bottom: none;
}
.no-results {
  padding: 40px 20px;
  text-align: center;
  color: #86868b;
  font-size: 15px;
}

.interface-patches-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.interface-patches-footer {
  display: flex;
  justify-content: center;
  margin-top: 18px;
}

.view-more-patches-btn {
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  min-width: min(100%, 420px);
  padding: 13px 16px 13px 18px;
  border: 1px solid #d2d2d7;
  border-radius: 12px;
  background: #ffffff;
  color: #1d1d1f;
  cursor: pointer;
  font-family: inherit;
  text-align: left;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: border-color 0.15s ease, box-shadow 0.15s ease, transform 0.15s ease;
}

.view-more-patches-btn:hover {
  border-color: #007aff;
  box-shadow: 0 5px 18px rgba(0, 122, 255, 0.12);
  transform: translateY(-1px);
}

.view-more-patches-btn:focus-visible {
  outline: none;
  border-color: #007aff;
  box-shadow: 0 0 0 3px rgba(0, 122, 255, 0.16);
}

.view-more-patches-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.view-more-patches-label {
  font-size: 14px;
  font-weight: 700;
  color: #1d1d1f;
}

.view-more-patches-meta {
  font-size: 12px;
  font-weight: 500;
  color: #6e6e73;
}

.view-more-patches-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 50%;
  background: #f0f7ff;
  color: #007aff;
  transition: transform 0.18s ease, background 0.18s ease;
}

.view-more-patches-icon.expanded {
  transform: rotate(180deg);
}

.view-more-patches-icon svg {
  width: 18px;
  height: 18px;
}

.interface-patch-card {
  background: #f5f5f7;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid #e8e8ed;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.interface-patch-card:hover {
  border-color: #c7c7cc;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.interface-patch-card.selected {
  border-color: #007aff;
  box-shadow: 0 0 0 1px #007aff;
}

.interface-patch-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 20px;
  background: #ffffff;
  border-bottom: 1px solid #e8e8ed;
  font-size: 15px;
}

.interface-patch-radio {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border: 2px solid #c7c7cc;
  border-radius: 50%;
  background: #fff;
  transition: border-color 0.2s, background 0.2s;
}

.interface-patch-radio.checked {
  border-color: #007aff;
  background: #007aff;
  box-shadow: inset 0 0 0 3px #fff;
}

.interface-patch-id {
  font-weight: 600;
  color: #1d1d1f;
}

.interface-patch-size {
  color: #6e6e73;
}

.interface-patch-chains {
  color: #1d1d1f;
  font-weight: 500;
}

.interface-patch-body {
  background: #f5f5f7;
}

.view-toggle {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}

.view-toggle-btn {
  border: none;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  cursor: pointer;
  background: #f5f5f7;
  color: #6e6e73;
  transition: background 0.15s ease, color 0.15s ease;
}

.view-toggle-btn.active {
  background: #007aff;
  color: #ffffff;
}

.graph-wrapper {
  position: relative;
}

.graph-expand-btn {
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  border: none;
  width: 36px;
  height: 36px;
  padding: 0;
  border-radius: 50%;
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  background: #ffffff;
  color: #6e6e73;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
  transition: background 0.15s ease, color 0.15s ease, box-shadow 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.graph-expand-btn:hover {
  background: #f5f5f7;
  color: #1d1d1f;
}

.graph-expand-btn.expanded {
  background: #e5e5ea;
  color: #1d1d1f;
}

.residues-table-wrap {
  max-height: 280px;
  overflow-y: auto;
  padding: 8px 20px 20px;
}

.residues-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.residues-table th {
  text-align: left;
  padding: 10px 16px;
  background: #ebebed;
  color: #6e6e73;
  font-weight: 600;
  position: sticky;
  top: 0;
}

.residues-table td {
  padding: 8px 16px;
  border-bottom: 1px solid #e8e8ed;
  color: #1d1d1f;
}

.residues-table tbody tr:last-child td {
  border-bottom: none;
}

.residues-table tbody tr:hover {
  background: #fafafa;
}

.connected-cell {
  max-width: 280px;
}

.muted {
  color: #86868b;
}

.connected-list {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 6px;
}

.connected-tag {
  display: inline-block;
  font-size: 12px;
  padding: 2px 8px;
  background: #e8f4fc;
  color: #1d1d1f;
  border-radius: 6px;
  white-space: nowrap;
}

/* Slider styles (matching ControlsPanel / DistanceDistribution) */
.slider-section {
  margin-bottom: 20px;
  padding: 16px 0;
  border-top: 1px solid #e8e8ed;
}

.slider-label {
  display: block;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 12px;
  letter-spacing: -0.022em;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 12px;
}

.slider-control {
  position: relative;
  flex: 1;
}

.slider-ticks {
  position: absolute;
  left: 14px;
  right: 14px;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  justify-content: space-between;
  pointer-events: none;
}

.slider-tick {
  position: relative;
  width: 2px;
  height: 16px;
  background: #b4b4bb;
  opacity: 0.7;
}

.slider-tick-label {
  position: absolute;
  top: -24px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  font-weight: 600;
  color: #6e6e73;
}

input[type="range"] {
  -webkit-appearance: none;
  appearance: none;
  position: relative;
  z-index: 2;
  width: 100%;
  height: 4px;
  border-radius: 2px;
  background: #d2d2d7;
  outline: none;
  flex: 1;
}

input[type="range"]::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all 0.15s ease;
}

input[type="range"]::-webkit-slider-thumb:hover {
  background: #000000;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.4);
  transform: scale(1.05);
}

.slider-value-input {
  display: flex;
  align-items: center;
  gap: 2px;
  min-width: 80px;
}

.value-input {
  width: 60px;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  text-align: right;
  border: 2px solid #d2d2d7;
  border-radius: 8px;
  padding: 6px 8px;
  background: #ffffff;
  font-variant-numeric: tabular-nums;
  transition: all 0.15s ease;
  font-family: inherit;
}

.value-input:focus {
  outline: none;
  border-color: #1d1d1f;
  box-shadow: 0 0 0 3px rgba(29, 29, 31, 0.1);
}

.value-input::-webkit-inner-spin-button,
.value-input::-webkit-outer-spin-button {
  opacity: 1;
  cursor: pointer;
}

.percent-symbol {
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
}

.slider-description {
  font-size: 14px;
  color: #6e6e73;
  margin-top: 8px;
  margin-bottom: 0;
}
</style>

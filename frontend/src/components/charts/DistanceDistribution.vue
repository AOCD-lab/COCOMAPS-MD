<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-container"></div>
    <p v-if="distributionCaption" class="distribution-caption">{{ distributionCaption }}</p>
    <div class="chart-toolbar">
      <!-- Interaction Type Chips -->
      <div class="control-group">
        <label>Select Interaction Type</label>
        <div class="interaction-chips">
          <button
            v-for="type in availableInteractionTypes"
            :key="type"
            :aria-pressed="selectedInteractionType === type"
            type="button"
            :class="['interaction-chip', { active: selectedInteractionType === type }]"
            @click="selectInteractionType(type)"
          >
            <span class="chip-color-dot" :style="{ backgroundColor: getInteractionBaseColor(type) }"></span>
            {{ type }}
          </button>
        </div>
        <p v-if="availableInteractionTypes.length === 0" class="no-types-message">
          No interaction types available. Adjust filters to see more types.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, computed, onBeforeUnmount } from 'vue'
import Plotly from 'plotly.js-dist-min'
import { useAnalysisStore } from '../../stores/analysisStore'
import { useChartUiStore } from '../../stores/chartUiStore'
import { useSystemsStore } from '../../stores/systemsStore'
import { getInteractionBaseColor, formatResiduePairFromParts, matchesSelectedTypes } from '../../utils/chartHelpers'
import { INTERACTION_TYPES } from '../../utils/constants'
import api from '../../services/api'

const analysisStore = useAnalysisStore()
const chartUiStore = useChartUiStore()
const systemsStore = useSystemsStore()
const chartContainer = ref(null)
const selectedInteractionType = ref('')
const distanceData = ref(null)
const loading = ref(false)
const distributionCaption = ref('')
const MAX_DISPLAYED_PAIRS = 50

// Threshold percent (derived from store)
const thresholdPercent = computed(() => Math.round(chartUiStore.currentThreshold * 100))

const canonicalPairKey = (id1, id2) => [id1, id2]
  .filter(Boolean)
  .sort()
  .join('::')

const interactionByPair = computed(() => new Map(
  analysisStore.interactions.map(interaction => [
    canonicalPairKey(interaction.id1, interaction.id2),
    interaction
  ])
))

// Get all unique interaction types from filtered data
const availableInteractionTypes = computed(() => {
  const typesSet = new Set()
  analysisStore.filteredInteractions.forEach(interaction => {
    if (interaction.typesArray && Array.isArray(interaction.typesArray)) {
      interaction.typesArray.forEach(type => {
        if (!matchesSelectedTypes(type, chartUiStore.selectedInteractionTypes, INTERACTION_TYPES)) {
          return
        }
        const persistence = interaction.typePersistence?.[type] ?? interaction.consistency ?? 0
        if (persistence >= chartUiStore.typeConservationThreshold) {
          typesSet.add(type)
        }
      })
    }
  })
  return Array.from(typesSet).sort()
})

const selectInteractionType = (type) => {
  selectedInteractionType.value = type
  loadDistanceData()
}

const loadDistanceData = async () => {
  if (!selectedInteractionType.value || !systemsStore.currentSystem) {
    updateChart()
    return
  }

  loading.value = true
  
  try {
    const response = await api.getDistanceDistributions(
      systemsStore.currentSystem,
      [selectedInteractionType.value]
    )
    distanceData.value = response.pairs || []
  } catch (error) {
    console.error('Failed to load distance data:', error)
    distanceData.value = []
  } finally {
    loading.value = false
    updateChart()
  }
}

const selectFirstTypeWithData = async () => {
  if (!systemsStore.currentSystem || availableInteractionTypes.value.length === 0) {
    updateChart()
    return
  }

  loading.value = true
  updateChart()

  const threshold = chartUiStore.currentThreshold

  for (const type of availableInteractionTypes.value) {
    try {
      const response = await api.getDistanceDistributions(
        systemsStore.currentSystem,
        [type]
      )
      const pairs = response.pairs || []
      if (pairs.some(p => p.consistency >= threshold)) {
        selectedInteractionType.value = type
        distanceData.value = pairs
        loading.value = false
        updateChart()
        return
      }
    } catch {
      // skip this type, try next
    }
  }

  selectedInteractionType.value = availableInteractionTypes.value[0]
  distanceData.value = []
  loading.value = false
  updateChart()
}

const updateChart = () => {
  if (!chartContainer.value) return

  if (!selectedInteractionType.value) {
    distributionCaption.value = ''
    Plotly.purge(chartContainer.value)
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">Please select an interaction type to view the distance distribution.</div>'
    return
  }

  if (loading.value) {
    distributionCaption.value = ''
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">Loading distance data...</div>'
    return
  }

  if (!distanceData.value || distanceData.value.length === 0) {
    distributionCaption.value = ''
    Plotly.purge(chartContainer.value)
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No distance data available for the selected interaction type.</div>'
    return
  }

  // Filter by conservation threshold (from shared store)
  const filteredPairs = distanceData.value.filter(pair => {
    const interaction = interactionByPair.value.get(canonicalPairKey(pair.id1, pair.id2))
    const pairConsistency = interaction?.consistency ?? pair.consistency ?? 0
    const typeConsistency = interaction?.typePersistence?.[selectedInteractionType.value]
      ?? pair.consistency
      ?? 0

    return pairConsistency >= chartUiStore.currentThreshold
      && typeConsistency >= chartUiStore.typeConservationThreshold
  })

  if (filteredPairs.length === 0) {
    distributionCaption.value = ''
    Plotly.purge(chartContainer.value)
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No pairs found with conservation ≥ ' + thresholdPercent.value + '%</div>'
    return
  }

  // Limit visible violins for performance and readability; disclose this in the caption.
  const topPairs = filteredPairs.slice(0, MAX_DISPLAYED_PAIRS)
  distributionCaption.value = topPairs.length < filteredPairs.length
    ? `Showing top ${topPairs.length} of ${filteredPairs.length} residue pairs by conservation after ≥${thresholdPercent.value}% pair-conservation filtering.`
    : `Showing all ${filteredPairs.length} residue pairs after ≥${thresholdPercent.value}% pair-conservation filtering.`
  
  // Calculate global mean across all pairs
  const allDistances = topPairs.flatMap(pair => pair.distances)
  const globalMean = allDistances.reduce((a, b) => a + b, 0) / allDistances.length
  
  // Get interaction color
  const interactionColor = getInteractionBaseColor(selectedInteractionType.value)
  
  // Prepare data for Plotly violin plot
  const pairLabels = topPairs.map(pair => formatResiduePairFromParts(
    { resName: pair.resName1, resNum: pair.resNum1, chain: pair.chain1 },
    { resName: pair.resName2, resNum: pair.resNum2, chain: pair.chain2 }
  ))

  const traces = topPairs.map((pair, index) => {
    const pairLabel = pairLabels[index]
    
    // Calculate statistics for hover info
    const sorted = [...pair.distances].sort((a, b) => a - b)
    const mean = pair.distances.reduce((a, b) => a + b, 0) / pair.distances.length
    const median = sorted[Math.floor(sorted.length / 2)]
    const min = sorted[0]
    const max = sorted[sorted.length - 1]
    const range = (max - min).toFixed(2)
    
    const conservationPercent = (pair.consistency * 100).toFixed(1)
    
    // Calculate frequency (count) at each distance point for hover
    const distanceCounts = {}
    pair.distances.forEach(d => {
      const rounded = d.toFixed(1) // Group by 0.1 Å bins
      distanceCounts[rounded] = (distanceCounts[rounded] || 0) + 1
    })
    
    // Total measurements (may be more than frames if multiple atom pairs)
    const totalMeasurements = pair.totalMeasurements || pair.distances.length
    const uniqueFrames = pair.frameCount
    
    return {
      type: 'violin',
      y: pair.distances,
      x: Array(pair.distances.length).fill(pairLabel),
      name: pairLabel,
      box: {
        visible: false
      },
      meanline: {
        visible: false  // We'll add custom short dashes instead
      },
      fillcolor: interactionColor.replace('rgb(', 'rgba(').replace(')', ', 0.22)'),
      opacity: 1,
      line: { color: interactionColor, width: 1.5 },
      points: 'all',
      pointpos: 0,
      jitter: 0.3,  // Fixed jitter value
      marker: {
        size: 4,  // Match the lighter markers used by the other charts
        color: interactionColor,  // Match interaction type color
        opacity: 1.0,  // Fully opaque for prominence
        line: {
          width: 0.5,
          color: '#ffffff'
        }
      },
      bandwidth: null, // Auto bandwidth
      scalemode: 'width',
      width: 0.9,
      showlegend: false,
      hoverinfo: 'text',
      text: pair.distances.map((d, i) => {
        const rounded = d.toFixed(1)
        const countAtDistance = distanceCounts[rounded]
        const frequencyPercent = ((countAtDistance / totalMeasurements) * 100).toFixed(1)
        
        return `<b>${pairLabel}</b><br>` +
          `Distance: ${d.toFixed(2)} Å<br>` +
          `<b>Frequency at ~${rounded} Å: ${countAtDistance} (${frequencyPercent}%)</b><br>` +
          `<br>Statistics:<br>` +
          `Total measurements: ${totalMeasurements}<br>` +
          `Frames with interaction: ${uniqueFrames}/${systemsStore.totalFrames}<br>` +
          `Mean: ${mean.toFixed(2)} Å<br>` +
          `Median: ${median.toFixed(2)} Å<br>` +
          `Range: ${min.toFixed(2)} - ${max.toFixed(2)} Å<br>` +
          `Conservation: ${conservationPercent}%`
      }),
      hoveron: 'points+kde'
    }
  })
  
  // Collect mean positions for annotations
  const meanAnnotations = topPairs.map((pair, index) => {
    const mean = pair.distances.reduce((a, b) => a + b, 0) / pair.distances.length
    return {
      mean,
      x: pairLabels[index],
      pairLabel: pairLabels[index]
    }
  })
  
  // Add invisible trace for legend entry (global mean)
  traces.push({
    type: 'scatter',
    mode: 'lines',
    x: [null],  // Invisible trace, just for legend
    y: [null],
    line: {
      color: '#1d1d1f',  // Black for global mean
      width: 2.5,
      dash: 'dash'
    },
    name: `Global Mean: ${globalMean.toFixed(2)} Å`,
    showlegend: true,
    hoverinfo: 'skip'
  })

  // Add overlay markers for local means (horizontal line marker)
  traces.push({
    type: 'scatter',
    mode: 'markers',
    x: meanAnnotations.map(item => item.x),
    y: meanAnnotations.map(item => item.mean),
    marker: {
      symbol: 'line-ew',
      size: 18,
      color: interactionColor,
      line: {
        width: 2.5,
        color: interactionColor
      }
    },
    hoverinfo: 'skip',
    showlegend: false
  })

  const layout = {
    title: {
      text: `${systemsStore.currentSystem?.name || 'System'} - Distance Distribution: ${selectedInteractionType.value}`,
      x: 0.5,
      xanchor: 'center',
      yanchor: 'top',
      automargin: true,
      font: {
        size: 24,
        weight: 600,
        family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        color: '#1d1d1f'
      }
    },
    annotations: [],
    shapes: [
      // Global mean line - rendered on top of all violins
      {
        type: 'line',
        x0: 0,
        x1: 1,
        xref: 'paper',
        y0: globalMean,
        y1: globalMean,
        yref: 'y',
        line: {
          color: '#1d1d1f',  // Black for global mean
          width: 2.5,
          dash: 'dash'
        },
        layer: 'above'
      }
    ],
    xaxis: {
      title: {
        text: 'Residue Pairs',
        font: {
          size: 15,
          family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          color: '#1d1d1f',
          weight: 700
        }
      },
      tickangle: -45,
      type: 'category',
      categoryorder: 'array',
      categoryarray: pairLabels,
      tickmode: 'array',
      tickvals: pairLabels,
      ticktext: pairLabels,
      tickfont: {
        size: 12,
        color: '#1d1d1f',
        weight: 700
      },
      automargin: true,
      showline: true,
      linecolor: '#ccd6eb',
      showgrid: false
    },
    yaxis: {
      title: {
        text: 'Distance (Å)',
        font: {
          size: 15,
          family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
          color: '#1d1d1f',
          weight: 700
        }
      },
      tickfont: {
        size: 12,
        color: '#1d1d1f',
        weight: 700
      },
      automargin: true,
      gridcolor: '#e6e6e6',
      gridwidth: 1,
      zeroline: false
    },
    plot_bgcolor: 'rgba(0,0,0,0)',
    paper_bgcolor: 'rgba(0,0,0,0)',
    margin: {
      l: 80,
      r: 24,
      t: 110,
      b: 130
    },
    height: 650,
    hovermode: 'closest',
    hoverlabel: {
      bgcolor: '#ffffff',
      bordercolor: '#d2d2d7',
      font: { size: 14, color: '#1d1d1f' },
      align: 'left'
    },
    violinmode: 'group',
    legend: {
      orientation: 'h',
      x: 0.5,
      y: 1.04,
      xanchor: 'center',
      yanchor: 'bottom',
      bgcolor: 'rgba(0,0,0,0)',
      borderwidth: 0,
      font: {
        size: 14,
        family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
        color: '#1d1d1f'
      }
    },
    font: {
      size: 12,
      color: '#1d1d1f',
      family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'
    }
  }

  const config = {
    responsive: true,
    displayModeBar: true,
    displaylogo: false,
    modeBarButtonsToRemove: ['pan2d', 'lasso2d', 'select2d'],
    toImageButtonOptions: {
      format: 'png',
      filename: `violin_${selectedInteractionType.value}_${systemsStore.currentSystem?.id}`,
      height: layout.height,
      width: 1400,
      scale: 2
    }
  }

  // Clear any previous content before rendering
  chartContainer.value.innerHTML = ''
  Plotly.newPlot(chartContainer.value, traces, layout, config)
}

onMounted(() => {
  if (availableInteractionTypes.value.length > 0 && !selectedInteractionType.value) {
    selectFirstTypeWithData()
  } else {
    updateChart()
  }
})

onBeforeUnmount(() => {
  if (chartContainer.value) {
    Plotly.purge(chartContainer.value)
  }
})

watch([
  () => chartUiStore.currentChartType,
  () => systemsStore.currentSystem?.id,
  () => chartUiStore.currentThreshold,
  () => chartUiStore.typeConservationThreshold,
  () => availableInteractionTypes.value
], () => {
  if (chartUiStore.currentChartType === 'violinPlot') {
    if (selectedInteractionType.value && !availableInteractionTypes.value.includes(selectedInteractionType.value)) {
      if (availableInteractionTypes.value.length > 0) {
        selectFirstTypeWithData()
      } else {
        selectedInteractionType.value = ''
        distanceData.value = null
        updateChart()
      }
    } else if (selectedInteractionType.value && systemsStore.currentSystem?.id) {
      loadDistanceData()
    } else {
      updateChart()
    }
  }
}, { deep: true })
</script>

<style scoped>
.chart-wrapper {
  width: 100%;
  height: 100%;
}

.distribution-caption {
  margin: 8px 32px 0;
  color: #6e6e73;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  text-align: center;
}

.chart-toolbar {
  padding: 24px 32px 0;
  margin-top: 8px;
  border-top: 1px solid #e8e8ed;
}

.control-group {
  margin-bottom: 24px;
}

.control-group:last-child {
  margin-bottom: 0;
}

.control-group > label {
  display: block;
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 12px;
  letter-spacing: -0.022em;
}

/* Interaction Type Chips */
.interaction-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.interaction-chip {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 14px;
  font-size: 14px;
  font-weight: 500;
  color: #1d1d1f;
  background: #f5f5f7;
  border: 2px solid transparent;
  border-radius: 980px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.interaction-chip:hover {
  background: #e8e8ed;
}

.interaction-chip.active {
  background: #1d1d1f;
  color: #ffffff;
  border-color: #1d1d1f;
}

.chip-color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.interaction-chip.active .chip-color-dot {
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.4);
}

.no-types-message {
  font-size: 14px;
  color: #6e6e73;
  font-style: italic;
  margin: 0;
}

/* Slider styles matching ControlsPanel */
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
  font-size: 15px;
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
  font-size: 15px;
  font-weight: 600;
  color: #1d1d1f;
}

.slider-description {
  font-size: 14px;
  color: #6e6e73;
  margin-top: 8px;
  margin-bottom: 0;
}

.chart-container {
  width: 100%;
  min-height: 650px;
}

.interaction-chip:focus-visible {
  outline: 2px solid #3B6EF5;
  outline-offset: 3px;
}

.chart-container :deep(.modebar) {
  background: #ffffff !important;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  padding: 3px;
}

.chart-container :deep(.modebar-btn path) {
  fill: #6e6e73;
}

.chart-container :deep(.modebar-btn:hover path),
.chart-container :deep(.modebar-btn.active path) {
  fill: #1d1d1f;
}
</style>

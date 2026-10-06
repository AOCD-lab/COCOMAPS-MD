<template>
  <div class="chart-wrapper">
    <div ref="chartContainer" class="chart-container"></div>
    <section v-if="tableRows.length" class="trend-summary" aria-labelledby="trend-summary-title">
      <div class="summary-heading">
        <div>
          <h3 id="trend-summary-title">Interaction type summary</h3>
          <p>Mean and sample standard deviation per interaction type</p>
        </div>
        <button type="button" class="download-button" @click="downloadSummary">Download CSV</button>
      </div>
      <div class="table-scroll">
        <table>
          <thead><tr>
            <th scope="col">Interaction type</th>
            <th scope="col" :aria-sort="sortKey === 'mean' ? sortDirection : 'none'">
              <button type="button" class="sort-button" @click="sortBy('mean')">Mean <span aria-hidden="true">{{ sortIndicator('mean') }}</span></button>
            </th>
            <th scope="col" :aria-sort="sortKey === 'standardDeviation' ? sortDirection : 'none'">
              <button type="button" class="sort-button" @click="sortBy('standardDeviation')">Standard deviation <span aria-hidden="true">{{ sortIndicator('standardDeviation') }}</span></button>
            </th>
          </tr></thead>
          <tbody>
            <tr v-for="row in sortedTableRows" :key="row.name">
              <th scope="row"><span class="color-swatch" :style="{ backgroundColor: row.color }" aria-hidden="true"></span>{{ row.name }}</th>
              <td>{{ row.mean.toFixed(2) }}</td><td>{{ row.standardDeviation.toFixed(2) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onBeforeUnmount, watch } from 'vue'
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import { useAnalysisStore } from '../../stores/analysisStore'
import { useChartUiStore } from '../../stores/chartUiStore'
import { useSystemsStore } from '../../stores/systemsStore'
import { INTERACTION_TYPES } from '../../utils/constants'
import { getInteractionBaseColor, sortInteractionLegendSeries } from '../../utils/chartHelpers'
import { buildConservationFilteredTrends, sumInteractionTrends, summarizeInteractionTrend } from '../../utils/interactionTrends'

const analysisStore = useAnalysisStore()
const chartUiStore = useChartUiStore()
const systemsStore = useSystemsStore()
const chartContainer = ref(null)
const tableRows = ref([])
const summaryFrameCount = ref(0)
const sortKey = ref(null)
const sortDirection = ref('descending')
const sortedTableRows = computed(() => {
  if (!sortKey.value) return tableRows.value
  const direction = sortDirection.value === 'ascending' ? 1 : -1
  return [...tableRows.value].sort((a, b) =>
    direction * (a[sortKey.value] - b[sortKey.value]) || a.name.localeCompare(b.name)
  )
})
const sortBy = key => {
  if (sortKey.value === key) {
    sortDirection.value = sortDirection.value === 'descending' ? 'ascending' : 'descending'
  } else {
    sortKey.value = key
    sortDirection.value = 'descending'
  }
}
const sortIndicator = key => sortKey.value !== key ? '↕' : sortDirection.value === 'ascending' ? '↑' : '↓'
let chart = null
let lastHoveredSeriesName = null

const buildSeries = (frameNumbers) => {
  const useLogScale = chartUiStore.useLogScale
  const filteredTrends = buildConservationFilteredTrends({
    interactions: analysisStore.interactions,
    frameNumbers,
    pairThreshold: chartUiStore.currentThreshold,
    typeThreshold: chartUiStore.typeConservationThreshold,
    interactionTypes: INTERACTION_TYPES
  })
  
  const series = INTERACTION_TYPES.map((type) => {
    const isDeselected = !chartUiStore.selectedInteractionTypes.has(type.id)
    const trendData = filteredTrends[type.id] || Array(frameNumbers.length).fill(0)
    const hasNonZero = trendData.some(value => value > 0)
    const meetsThreshold = !isDeselected && hasNonZero
    const plottedData = useLogScale
      ? trendData.map(value => value === 0 ? null : value)
      : trendData

    const baseColor = getInteractionBaseColor(type.label)

    return {
      name: type.label,
      data: meetsThreshold ? plottedData : [],
      color: isDeselected ? 'rgba(156, 163, 175, 0.14)' : baseColor,
      lineWidth: 2,
      marker: {
        enabled: meetsThreshold,
        radius: 2.5,
        lineWidth: 1,
        lineColor: '#ffffff'
      },
      enableMouseTracking: meetsThreshold,
      showInLegend: true,
      _hasData: meetsThreshold,
      _isDeselected: isDeselected,
      _isAnnotation: false,
      point: {
        events: {
          mouseOver: function() {
            lastHoveredSeriesName = this.series.name
          }
        }
      }
    }
  })

  const totals = sumInteractionTrends(
    filteredTrends, chartUiStore.selectedInteractionTypes, frameNumbers.length
  )
  const totalSeries = {
    id: 'total-interactions',
    name: 'Total Interactions',
    data: useLogScale ? totals.map(value => value === 0 ? null : value) : totals,
    color: '#1d1d1f',
    lineWidth: 3,
    dashStyle: 'ShortDash',
    zIndex: 3,
    marker: { enabled: false },
    showInLegend: true,
    _hasData: !useLogScale || totals.some(value => value > 0),
    _isDeselected: false,
    point: {
      events: {
        mouseOver: function() {
          lastHoveredSeriesName = this.series.name
        }
      }
    }
  }

  return [totalSeries, ...sortInteractionLegendSeries(series)]
}

const updateChart = () => {
  if (!chartContainer.value) return
  lastHoveredSeriesName = null

  // Use actual frame numbers from backend if available
  const frameNumbers = analysisStore.trendFrameNumbers || []
  const trendValues = Object.values(analysisStore.trends || {})
  const maxTrendLength = trendValues.reduce((max, series) => {
    if (Array.isArray(series)) {
      return Math.max(max, series.length)
    }
    return max
  }, 0)
  
  // Determine frame count and categories
  let frameCount, categories, dataFrameNumbers
  if (frameNumbers.length > 0) {
    // Use actual frame numbers from backend
    frameCount = frameNumbers.length
    dataFrameNumbers = frameNumbers.map(Number)
    categories = frameNumbers.map(n => `${n}`)
  } else {
    // Fallback to sequential numbering
    frameCount = Math.max(systemsStore.totalFrames || 0, maxTrendLength)
    dataFrameNumbers = Array.from({ length: frameCount }, (_, i) => i + 1)
    categories = dataFrameNumbers.map(n => `${n}`)
  }
  
  if (frameCount === 0) {
    tableRows.value = []
    summaryFrameCount.value = 0
    if (chart) { chart.destroy(); chart = null }
    return
  }

  const series = buildSeries(dataFrameNumbers)
  summaryFrameCount.value = frameCount
  const summaryRows = series
    .filter(item => item.id !== 'total-interactions' && item._hasData)
    .map(item => ({
      name: item.name,
      color: item.color,
      ...summarizeInteractionTrend(item.data)
    }))
  tableRows.value = summaryRows

  if (chart) {
    chart.destroy()
  }

  const chartOptions = {
    chart: {
      type: 'line',
      backgroundColor: 'transparent',
      height: 650
    },
    title: {
      text: `${systemsStore.currentSystem?.name || 'System'} - Interaction Type Trends Across Frames`,
      style: {
        fontSize: '24px',
        fontWeight: '600',
        color: '#1d1d1f'
      }
    },
    subtitle: {
      text: null
    },
    credits: {
      enabled: false
    },
    xAxis: {
      categories: categories,
      title: {
        text: chartUiStore.timeUnit ? `Time (${chartUiStore.timeUnit})` : 'Frame',
        style: {
          fontSize: '16px',
          fontWeight: '700',
          color: '#1d1d1f'
        }
      },
      labels: {
        style: {
          fontSize: '13px',
          fontWeight: '700',
          color: '#1d1d1f'
        }
      }
    },
    yAxis: {
      type: chartUiStore.useLogScale ? 'logarithmic' : 'linear',
      title: {
        text: `Number of Conserved Residue-Pair Interactions${chartUiStore.useLogScale ? ' - Log Scale' : ''}`,
        style: {
          fontSize: '16px',
          fontWeight: '700',
          color: '#1d1d1f'
        }
      },
      labels: {
        style: {
          fontSize: '13px',
          fontWeight: '700',
          color: '#1d1d1f'
        }
      },
      min: chartUiStore.useLogScale ? 0.1 : 0,
      // Ensure proper handling of small values in log scale
      allowDecimals: true
    },
    legend: {
      align: 'right',
      verticalAlign: 'middle',
      layout: 'vertical',
      useHTML: true,
      labelFormatter: function() {
        const hasData = this.options._hasData
        if (this.options._isDeselected) {
          return `<span title="Deselected from the Interaction Type Filter." style="color: #8e8e93; font-weight: 400; font-size: 13px; text-decoration: line-through;">${this.name}</span>`
        } else if (!this.visible) {
          return `<span title="Hidden from the chart using this legend." style="color: #9ca3af; font-weight: 500; font-size: 13px;">${this.name}</span>`
        } else if (hasData) {
          return `<span style="font-weight: 700; font-size: 13px;">${this.name}</span>`
        } else {
          return `<span style="color: #9ca3af; font-weight: 400; font-size: 13px;">${this.name}</span>`
        }
      },
      itemStyle: {
        fontSize: '13px',
        fontWeight: '500',
        color: '#1d1d1f'
      }
    },
    plotOptions: {
      series: {
        events: {
          hide: function() {
            tableRows.value = summaryRows.filter(row =>
              this.chart.series.some(item => item.name === row.name && item.visible)
            )
          },
          show: function() {
            tableRows.value = summaryRows.filter(row =>
              this.chart.series.some(item => item.name === row.name && item.visible)
            )
          }
        }
      },
      line: {
        lineWidth: 2,
        events: {
          legendItemClick: function() {
            return !this.options._isDeselected && this.options._hasData
          }
        },
        states: {
          hover: {
            lineWidth: 3
          }
        },
        marker: {
          enabled: true,
          radius: 2.5
        }
      }
    },
    series: series,
    tooltip: {
      backgroundColor: 'rgba(255, 255, 255, 0.98)',
      borderRadius: 12,
      borderWidth: 1,
      borderColor: '#d2d2d7',
      shared: true,
      useHTML: true,
      formatter: function() {
        let html = `<div style="padding: 10px;">`
        html += `<div style="font-size: 15px; color: #1d1d1f; font-weight: 600; margin-bottom: 8px;">${this.x}</div>`
        
        const totalPoint = this.points.find(point => point.series.options.id === 'total-interactions')
        const hoveredPoint = this.points.find(point =>
          point !== totalPoint && point.series.name === lastHoveredSeriesName
        )
        const otherPoints = this.points
          .filter(point => point !== totalPoint && point !== hoveredPoint)
          .sort((a, b) => b.y - a.y)

        const sortedPoints = [totalPoint, hoveredPoint, ...otherPoints].filter(Boolean)

        sortedPoints.forEach(point => {
          if (point.y > 0 || point.series.options.id === 'total-interactions') {
            html += `
              <div style="margin-bottom: 4px;">
                <span style="color: ${point.color}; font-weight: 600;">●</span>
                <span style="color: #1d1d1f;">${point.series.name}: </span>
                <span style="color: #1d1d1f; font-weight: 600;">${point.y}</span>
              </div>
            `
          }
        })
        html += '</div>'
        return html
      }
    }
  }

  const systemName = systemsStore.currentSystem?.id || 'unknown'
  const exportOptions = withExporting(chartOptions, `interaction-trends-${systemName}`)
  chart = Highcharts.chart(chartContainer.value, exportOptions)
}

const downloadSummary = () => {
  const escape = value => `"${String(value).replaceAll('"', '""')}"`
  const lines = [
    ['Interaction type', 'Color', 'Mean across all frames', 'Sample standard deviation', 'Total frames'],
    ...sortedTableRows.value.map(row => [row.name, row.color, row.mean, row.standardDeviation, summaryFrameCount.value])
  ]
  const csv = lines.map(row => row.map(escape).join(',')).join('\r\n') + '\r\n'
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }))
  const link = document.createElement('a')
  link.href = url
  link.download = `interaction-summary-${systemsStore.currentSystem?.id || 'system'}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

onMounted(() => {
  updateChart()
})

onBeforeUnmount(() => chart?.destroy())

watch([
  () => chartUiStore.currentChartType,
  () => analysisStore.trends,
  () => chartUiStore.useLogScale,
  () => systemsStore.totalFrames,
  () => analysisStore.trendFrameNumbers,
  () => chartUiStore.timeUnit,
  () => chartUiStore.currentThreshold,
  () => chartUiStore.typeConservationThreshold,
  () => Array.from(chartUiStore.selectedInteractionTypes),
  () => analysisStore.interactions
], () => {
  if (chartUiStore.currentChartType === 'line') {
    updateChart()
  }
}, { deep: true })
</script>

<style scoped>
.chart-wrapper {
  width: 100%;
}

.chart-container {
  width: 100%;
  min-height: 650px;
}

.trend-summary { margin-top: 24px; border: 1px solid #e8e8ed; border-radius: 12px; overflow: hidden; background: #fff; color: #1d1d1f; }
.summary-heading { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 20px 24px; }
.summary-heading h3 { margin: 0 0 4px; font-size: 18px; }
.summary-heading p { margin: 0; color: #6e6e73; font-size: 13px; }
.download-button { border: 1px solid #d2d2d7; border-radius: 8px; background: #fff; padding: 9px 14px; color: #1d1d1f; font: inherit; font-weight: 600; cursor: pointer; white-space: nowrap; }
.download-button:hover { background: #f5f5f7; }
.download-button:focus-visible { outline: 2px solid #3b6ef5; outline-offset: 2px; }
.table-scroll { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { padding: 12px 24px; border-top: 1px solid #e8e8ed; text-align: left; }
thead th { background: #f5f5f7; color: #6e6e73; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }
.sort-button { border: 0; background: none; padding: 0; color: inherit; font: inherit; font-weight: inherit; text-transform: inherit; letter-spacing: inherit; cursor: pointer; white-space: nowrap; }
.sort-button:hover { color: #1d1d1f; }
.sort-button:focus-visible { outline: 2px solid #3b6ef5; outline-offset: 3px; }
tbody tr:nth-child(even) { background: #fafafa; }
tbody th { font-weight: 600; }
td { font-variant-numeric: tabular-nums; }
.color-swatch { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 10px; vertical-align: baseline; }

.chart-toolbar {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 20px 32px 0;
  margin-top: 8px;
  border-top: 1px solid #e8e8ed;
}

.slider-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.slider-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 0;
  letter-spacing: -0.022em;
}

.slider-label .info-icon {
  font-size: 14px;
  color: #8e8e93;
  cursor: pointer;
  transition: color 0.15s ease;
}

.slider-label .info-icon:hover {
  color: #3B6EF5;
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
  border-radius: 3px;
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

input[type="range"]::-moz-range-thumb {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #1d1d1f;
  cursor: pointer;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  transition: all 0.15s ease;
}

input[type="range"]::-moz-range-thumb:hover {
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
  margin: 0;
  font-size: 13px;
  color: #6e6e73;
  font-weight: 500;
  font-style: italic;
}

.global-tooltip {
  position: fixed;
  padding: 10px 14px;
  background: #1d1d1f;
  color: #ffffff;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.5;
  white-space: normal;
  max-width: 320px;
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
  z-index: 100000;
  pointer-events: none;
  text-align: left;
  animation: tooltipFadeIn 0.15s ease;
}

@keyframes tooltipFadeIn {
  from {
    opacity: 0;
    transform: translateY(4px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

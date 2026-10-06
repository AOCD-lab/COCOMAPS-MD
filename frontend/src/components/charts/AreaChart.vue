<template>
  <div class="chart-wrapper">
    <div class="chart-toolbar">
      <div class="toggle-group">
        <span>Mean ± Std Dev</span>
        <label class="switch">
          <input type="checkbox" v-model="showStats" aria-label="Mean ± Std Dev">
          <span class="slider"></span>
        </label>
      </div>
      <div class="toggle-group">
        <span>BSA</span>
        <label class="switch">
          <input type="checkbox" v-model="showBSA" aria-label="BSA" :disabled="!showInterfaceArea">
          <span class="slider"></span>
        </label>
      </div>
      <div class="toggle-group">
        <span>Interface Area</span>
        <label class="switch">
          <input type="checkbox" v-model="showInterfaceArea" aria-label="Interface Area" :disabled="!showBSA">
          <span class="slider"></span>
        </label>
      </div>
    </div>
    <div ref="chartContainer" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import Highcharts from '../../utils/highchartsConfig'
import { withExporting } from '../../utils/highchartsConfig'
import HighchartsMore from 'highcharts/highcharts-more'
import { useAnalysisStore } from '../../stores/analysisStore'
import { useChartUiStore } from '../../stores/chartUiStore'
import { useSystemsStore } from '../../stores/systemsStore'

HighchartsMore(Highcharts)

const showStats = ref(false)
const showBSA = ref(true)
const showInterfaceArea = ref(false)
const analysisStore = useAnalysisStore()
const chartUiStore = useChartUiStore()
const systemsStore = useSystemsStore()
const chartContainer = ref(null)
let chart = null
let hasAnimated = false

const calculateStats = (data) => {
  if (!data.length) {
    return { mean: 0, stdDev: 0, lower: 0, upper: 0 }
  }
  const mean = data.reduce((sum, value) => sum + value, 0) / data.length
  const variance = data.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / data.length
  const stdDev = Math.sqrt(variance)
  return {
    mean,
    stdDev,
    lower: Math.max(0, mean - stdDev),
    upper: mean + stdDev
  }
}

const updateChart = () => {
  if (!chartContainer.value) return

  if (!analysisStore.areaData || analysisStore.areaData.length === 0) {
    if (chart) {
      chart.destroy()
      chart = null
    }
    chartContainer.value.innerHTML = '<div style="text-align: center; padding: 100px 20px; color: #6e6e73; font-size: 19px;">No area data available for this system.</div>'
    return
  }

  const sortedAreaData = [...analysisStore.areaData].sort((a, b) => a.frame - b.frame) //prevents lexicographic order

  const categories = sortedAreaData.map(d => `${d.frame}`)
  const totalBSAData = sortedAreaData.map(d => d.totalBSA)
  const polarBSAData = sortedAreaData.map(d => d.polarBSA)
  const nonPolarBSAData = sortedAreaData.map(d => d.nonPolarBSA)

  if (chart) {
    chart.destroy()
  }


  const buildRangeSeries = (id, color, stats, baseData) => {
    if (!stats.stdDev || stats.stdDev === 0) return null
    const areaData = baseData.map((_, index) => [index, stats.lower, stats.upper])
    return {
      type: 'arearange',
      linkedTo: id,
      data: areaData,
      color,
      fillOpacity: showBSA.value && showInterfaceArea.value ? 0.05 : 0.10,
      lineWidth: 0,
      enableMouseTracking: false,
      showInLegend: false,
      zIndex: 0,
      marker: {
        enabled: false
      }
    }
  }

  // COCOMAPS defines each interface area as half its corresponding BSA.
  // Derive it from existing frame data so older results need no reprocessing.
  const series = []
  const components = [
    { key: 'total', label: 'Total', data: totalBSAData, color: '#0072B2', symbol: 'circle' },
    { key: 'polar', label: 'Polar', data: polarBSAData, color: '#B85C00', symbol: 'square' },
    { key: 'nonpolar', label: 'Non-Polar', data: nonPolarBSAData, color: '#8E5AA9', symbol: 'triangle' }
  ]
  for (const measure of [
    { key: 'bsa', label: 'BSA', enabled: showBSA.value, scale: 1, dashStyle: 'Solid' },
    { key: 'interface-area', label: 'Interface Area', enabled: showInterfaceArea.value, scale: 0.5, dashStyle: 'Dash' }
  ]) {
    if (!measure.enabled) continue
    for (const component of components) {
      const data = component.data.map(value => value * measure.scale)
      const stats = calculateStats(data)
      const id = `${component.key}-${measure.key}-line`
      series.push({
        id,
        name: `${component.label} ${measure.label}`,
        custom: { stats },
        data,
        color: component.color,
        dashStyle: measure.dashStyle,
        zIndex: 2,
        marker: {
          symbol: component.symbol,
          fillColor: measure.key === 'bsa' ? component.color : '#ffffff',
          lineColor: component.color,
          lineWidth: 1.5
        }
      })
      if (showStats.value) {
        const range = buildRangeSeries(id, component.color, stats, data)
        if (range) series.push(range)
      }
    }
  }
  const areaLabel = showBSA.value
    ? (showInterfaceArea.value ? 'Buried Surface Area and Interface Area' : 'Buried Surface Area')
    : 'Interface Area'

  const chartOptions = {
    chart: {
      type: 'line',
      backgroundColor: 'transparent',
      // Reserve room for the full legend so toggling statistics never resizes
      // the plot. Each responsive layout retains a 500px plotting area.
      height: 750,
      marginTop: 180,
      marginBottom: 70
    },
    title: {
      text: `${systemsStore.currentSystem?.name || 'System'} - ${areaLabel} Across Frames`,
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
      title: {
        text: `${areaLabel} (Å²)`,
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
    legend: {
      align: 'center',
      verticalAlign: 'top',
      layout: 'horizontal',
      useHTML: false,
      width: 720,
      itemWidth: 240,
      itemDistance: 0,
      itemMarginTop: 6,
      itemMarginBottom: 10,
      symbolWidth: 32,
      symbolPadding: 10,
      labelFormatter: function() {
        if (!showStats.value) return this.name
        const stats = this.options.custom.stats
        return `${this.name}<br/><span style="font-size:12px;font-weight:400">${stats.mean.toFixed(2)} ± ${stats.stdDev.toFixed(2)} Å²</span>`
      },
      title: {
        text: showStats.value ? 'Mean ± Std Dev (Å²)' : null,
        style: { fontSize: '12px', fontWeight: '400', color: '#6e6e73' }
      },
      itemStyle: {
        fontSize: '14px',
        fontWeight: '500',
        color: '#1d1d1f'
      }
    },
    responsive: {
      rules: [
        {
          condition: { maxWidth: 780 },
          chartOptions: {
            chart: { height: 800, marginTop: 230 },
            legend: { width: 480 }
          }
        },
        {
          condition: { maxWidth: 540 },
          chartOptions: {
            chart: { height: 960, marginTop: 390 },
            legend: { width: 240 }
          }
        }
      ]
    },
    plotOptions: {
      line: {
        animation: hasAnimated ? false : { duration: 800 },
        lineWidth: 2,
        marker: {
          enabled: true,
          radius: 3,
          lineWidth: 1,
          lineColor: '#ffffff'
        },
        states: {
          hover: {
            lineWidth: 3
          }
        }
      }
    },
    series,
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
        
        const sortedPoints = [...this.points].sort((a, b) => b.y - a.y)
        sortedPoints.forEach(point => {
          html += `
            <div style="margin-bottom: 4px;">
              <span style="color: ${point.color}; font-weight: 600;">●</span>
              <span style="color: #1d1d1f;">${point.series.name}: </span>
              <span style="color: #1d1d1f; font-weight: 600;">${point.y.toFixed(2)} Å²</span>
            </div>
          `
        })
        html += '</div>'
        return html
      }
    }
  }

  const systemName = systemsStore.currentSystem?.id || 'unknown'
  const exportOptions = withExporting(chartOptions, `${showBSA.value ? (showInterfaceArea.value ? 'bsa-and-interface-area' : 'buried-surface-area') : 'interface-area'}-${systemName}`)
  chart = Highcharts.chart(chartContainer.value, exportOptions)
  hasAnimated = true
}

onBeforeUnmount(() => chart?.destroy())

onMounted(() => {
  updateChart()
})

watch([
  () => chartUiStore.currentChartType,
  () => analysisStore.areaData,
  () => showStats.value,
  () => showBSA.value,
  () => showInterfaceArea.value,
  () => chartUiStore.timeUnit
], () => {
  if (chartUiStore.currentChartType === 'area') {
    updateChart()
  }
}, { deep: true })
</script>

<style scoped>
.chart-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
  height: 100%;
}

.chart-toolbar {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  margin-bottom: 8px;
  padding: 4px 0;
  gap: 12px;
}

.toggle-group {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  width: 200px;
  font-size: 16px;
  font-weight: 500;
  color: #1d1d1f;
}

.switch {
  position: relative;
  display: inline-block;
  width: 42px;
  height: 22px;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #d2d2d7;
  transition: .2s;
  border-radius: 22px;
}

.slider:before {
  position: absolute;
  content: "";
  height: 18px;
  width: 18px;
  left: 2px;
  bottom: 2px;
  background-color: white;
  transition: .2s;
  border-radius: 50%;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
}

input:disabled + .slider {
  cursor: not-allowed;
  opacity: 0.6;
}

input:focus-visible + .slider {
  outline: 2px solid #1d1d1f;
  outline-offset: 3px;
}

input:checked + .slider {
  background-color: #3B6EF5;
}

input:checked + .slider:before {
  transform: translateX(20px);
}

.chart-container {
  flex: 1;
  width: 100%;
  height: calc(100% - 40px);
}
</style>

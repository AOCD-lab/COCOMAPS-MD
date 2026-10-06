import { afterEach, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AreaChart from '../AreaChart.vue'
import Highcharts from '../../../utils/highchartsConfig'
import { useAnalysisStore } from '../../../stores/analysisStore'
import { useChartUiStore } from '../../../stores/chartUiStore'

let wrapper

afterEach(() => {
  wrapper?.unmount()
  document.body.innerHTML = ''
})

// Keep Highcharts real: mocked option checks cannot detect renderer crashes.
it('renders with statistics off and switches between both measures and interface-only', async () => {
  const pinia = createPinia()
  setActivePinia(pinia)
  useChartUiStore().currentChartType = 'area'
  useAnalysisStore().areaData = [
    { frame: 1, totalBSA: 1488, polarBSA: 617, nonPolarBSA: 871 },
    { frame: 2, totalBSA: 1500, polarBSA: 620, nonPolarBSA: 880 }
  ]
  wrapper = mount(AreaChart, { global: { plugins: [pinia] }, attachTo: document.body })

  const plotHeight = () => Highcharts.charts.filter(Boolean).at(-1).plotHeight
  expect(plotHeight()).toBe(500)
  const legendText = () => wrapper.get('.highcharts-legend').text()
  expect(wrapper.get('input[aria-label="Mean ± Std Dev"]').element.checked).toBe(false)
  expect(legendText()).toContain('Total BSA')

  await wrapper.get('input[aria-label="Interface Area"]').setValue(true)
  expect(legendText()).toContain('Total BSA')
  expect(legendText()).toContain('Total Interface Area')

  await wrapper.get('input[aria-label="Mean ± Std Dev"]').setValue(true)
  expect(legendText()).toContain('Mean ± Std Dev')
  expect(plotHeight()).toBe(500)

  await wrapper.get('input[aria-label="BSA"]').setValue(false)
  expect(legendText()).toContain('Total Interface Area')
  expect(legendText()).not.toContain('Total BSA')

  await wrapper.get('input[aria-label="Mean ± Std Dev"]').setValue(false)
  expect(legendText()).toContain('Total Interface Area')
  expect(legendText()).not.toContain('Mean ± Std Dev')
  expect(plotHeight()).toBe(500)

  await wrapper.get('input[aria-label="BSA"]').setValue(true)
  // Check the full six-series legend at all responsive widths, off and on.
  for (const width of [1000, 700, 450]) {
    for (const enabled of [true, false]) {
      await wrapper.get('input[aria-label="Mean ± Std Dev"]').setValue(enabled)
      const chart = Highcharts.charts.filter(Boolean).at(-1)
      chart.setSize(width, undefined, false)
      expect(chart.plotHeight).toBe(500)
    }
  }
})

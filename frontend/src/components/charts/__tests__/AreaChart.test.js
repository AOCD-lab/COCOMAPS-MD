import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import AreaChart from '../AreaChart.vue'
import Highcharts from '../../../utils/highchartsConfig'
import { useAnalysisStore } from '../../../stores/analysisStore'
import { useChartUiStore } from '../../../stores/chartUiStore'

vi.mock('../../../utils/highchartsConfig', () => ({
  default: { chart: vi.fn(() => ({ destroy: vi.fn() })) },
  withExporting: options => options
}))
vi.mock('highcharts/highcharts-more', () => ({ default: vi.fn() }))

const options = () => Highcharts.chart.mock.calls.at(-1)[1]
const lines = () => options().series.filter(series => series.id)

describe('AreaChart area measures', () => {
  let pinia
  beforeEach(() => {
    vi.clearAllMocks()
    pinia = createPinia()
    setActivePinia(pinia)
    useChartUiStore().currentChartType = 'area'
    useAnalysisStore().areaData = [
      { frame: 2, totalBSA: 1508.3, polarBSA: 637.5, nonPolarBSA: 890.6 },
      { frame: 1, totalBSA: 1488.3, polarBSA: 617.5, nonPolarBSA: 870.6 }
    ]
  })

  it('supports BSA, both, and interface-only while preventing both switches being off', async () => {
    const wrapper = mount(AreaChart, { global: { plugins: [pinia] } })
    const bsa = wrapper.get('input[aria-label="BSA"]')
    const area = wrapper.get('input[aria-label="Interface Area"]')
    expect(bsa.element.disabled).toBe(true)
    expect(wrapper.get('input[aria-label="Mean ± Std Dev"]').element.checked).toBe(false)
    expect(options().series).toHaveLength(3)
    await area.setValue(true)
    expect(lines()).toHaveLength(6)
    expect(bsa.element.disabled).toBe(false)
    expect(options().title.text).toContain('Buried Surface Area and Interface Area')
    await bsa.setValue(false)
    expect(area.element.disabled).toBe(true)
    expect(lines()).toHaveLength(3)
    expect(lines().map(line => line.data[0])).toEqual([744.15, 308.75, 435.3])
    expect(options().yAxis.title.text).toBe('Interface Area (Å²)')
    await bsa.setValue(true)
    await area.setValue(false)
    expect(bsa.element.disabled).toBe(true)
    expect(lines().map(line => line.data[0])).toEqual([1488.3, 617.5, 870.6])
    wrapper.unmount()
  })

  it('scales means and deviation bands and hides statistics for both measures', async () => {
    const wrapper = mount(AreaChart, { global: { plugins: [pinia] } })
    await wrapper.get('input[aria-label="Interface Area"]').setValue(true)
    await wrapper.get('input[aria-label="Mean ± Std Dev"]').setValue(true)
    const totalArea = lines().find(line => line.id === 'total-interface-area-line')
    expect(totalArea.name).toBe('Total Interface Area')
    const label = options().legend.labelFormatter.call({ name: totalArea.name, options: totalArea })
    expect(label).toContain('Total Interface Area<br/>')
    expect(label).toContain('749.15 ± 5.00 Å²')
    const band = options().series.find(series => series.linkedTo === totalArea.id)
    expect(band.data[0]).toEqual([0, 744.15, 754.15])
    await wrapper.get('input[aria-label="Mean ± Std Dev"]').setValue(false)
    expect(options().series).toHaveLength(6)
    expect(options().legend.labelFormatter.call({ name: totalArea.name, options: totalArea })).toBe('Total Interface Area')
    wrapper.unmount()
  })
  it('keeps component colors consistent and distinguishes measures without color alone', async () => {
    const wrapper = mount(AreaChart, { global: { plugins: [pinia] } })
    await wrapper.get('input[aria-label="Interface Area"]').setValue(true)
    const bsa = lines().slice(0, 3)
    const area = lines().slice(3)
    expect(new Set(bsa.map(line => line.color)).size).toBe(3)
    bsa.forEach((line, index) => {
      expect(area[index].color).toBe(line.color)
      expect(line.dashStyle).toBe('Solid')
      expect(area[index].dashStyle).toBe('Dash')
      expect(line.marker.fillColor).toBe(line.color)
      expect(area[index].marker.fillColor).toBe('#ffffff')
      expect(area[index].marker.symbol).toBe(line.marker.symbol)
    })
    wrapper.unmount()
  })

})

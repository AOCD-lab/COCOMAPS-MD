import { expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import InteractionTrends from '../InteractionTrends.vue'
import Highcharts from '../../../utils/highchartsConfig'
import { useAnalysisStore } from '../../../stores/analysisStore'
import { useChartUiStore } from '../../../stores/chartUiStore'

vi.mock('../../../utils/highchartsConfig', () => ({
  default: { chart: vi.fn(() => ({ destroy: vi.fn() })) },
  withExporting: options => options
}))

it('renders the total first and updates it for same-size filter changes and log scale', async () => {
  const pinia = createPinia()
  setActivePinia(pinia)
  const analysis = useAnalysisStore()
  const ui = useChartUiStore()
  ui.currentChartType = 'line'
  ui.useLogScale = false
  ui.selectedInteractionTypes = new Set(['h-bond'])
  analysis.trendFrameNumbers = [1, 2, 3]
  analysis.interactions = [{
    consistency: 1,
    typePersistence: { 'H-bonds': 1, 'Salt-bridges': 1 },
    typeFrames: { 'H-bonds': [1, 2], 'Salt-bridges': [2] }
  }]
  const wrapper = mount(InteractionTrends, { global: { plugins: [pinia] } })
  const total = () => Highcharts.chart.mock.calls.at(-1)[1].series[0]
  expect(total().name).toBe('Total Interactions')
  expect(total().showInLegend).toBe(true)
  expect(total().data).toEqual([1, 1, 0])
  ui.selectedInteractionTypes = new Set(['salt-bridge'])
  await wrapper.vm.$nextTick()
  expect(total().data).toEqual([0, 1, 0])
  ui.selectedInteractionTypes.add('h-bond')
  await wrapper.vm.$nextTick()
  expect(total().data).toEqual([1, 2, 0])
  ui.useLogScale = true
  await wrapper.vm.$nextTick()
  expect(total().data).toEqual([1, 2, null])
  wrapper.unmount()
})

it('shows Total Interactions first and the hovered line second', async () => {
  const pinia = createPinia()
  setActivePinia(pinia)
  const analysis = useAnalysisStore()
  useChartUiStore().currentChartType = 'line'
  analysis.trendFrameNumbers = [1]
  const wrapper = mount(InteractionTrends, { global: { plugins: [pinia] } })
  const options = Highcharts.chart.mock.calls.at(-1)[1]
  const points = [
    { y: 3, color: '#f00', series: { name: 'H-bonds', options: {} } },
    { y: 5, color: '#000', series: { name: 'Total Interactions', options: { id: 'total-interactions' } } },
    { y: 2, color: '#0f0', series: { name: 'Salt-bridges', options: {} } }
  ]
  const html = options.tooltip.formatter.call({ x: 1, points })
  expect(html.indexOf('Total Interactions:')).toBeLessThan(html.indexOf('H-bonds:'))
  expect(html.indexOf('H-bonds:')).toBeLessThan(html.indexOf('Salt-bridges:'))

  const saltSeries = options.series.find(series => series.name === 'Salt-bridges')
  saltSeries.point.events.mouseOver.call({ series: { name: 'Salt-bridges' } })
  const hoveredHtml = options.tooltip.formatter.call({ x: 1, points })
  expect(hoveredHtml.indexOf('Total Interactions:')).toBeLessThan(hoveredHtml.indexOf('Salt-bridges:'))
  expect(hoveredHtml.indexOf('Salt-bridges:')).toBeLessThan(hoveredHtml.indexOf('H-bonds:'))
  wrapper.unmount()
})

it('shows statistics for plotted interactions and follows legend visibility', async () => {
  const pinia = createPinia()
  setActivePinia(pinia)
  const analysis = useAnalysisStore()
  const ui = useChartUiStore()
  ui.currentChartType = 'line'
  ui.selectedInteractionTypes = new Set(['h-bond', 'salt-bridge'])
  analysis.trendFrameNumbers = [1, 2, 3]
  analysis.interactions = [{
    consistency: 1,
    typePersistence: { 'H-bonds': 1, 'Salt-bridges': 1 },
    typeFrames: { 'H-bonds': [1, 2], 'Salt-bridges': [2] }
  }, {
    consistency: 1,
    typePersistence: { 'H-bonds': 1 },
    typeFrames: { 'H-bonds': [2] }
  }]

  const wrapper = mount(InteractionTrends, { global: { plugins: [pinia] } })
  await wrapper.vm.$nextTick()
  expect(wrapper.findAll('tbody tr')).toHaveLength(2)
  expect(wrapper.findAll('tbody tr')[0].text()).toContain('1.00')
  expect(wrapper.findAll('tbody tr')[1].text()).toContain('0.33')
  expect(wrapper.text()).toContain('Mean and sample standard deviation per interaction type')
  expect(wrapper.text()).not.toContain('Total Interactions')

  const meanHeader = wrapper.findAll('thead button')[0]
  await meanHeader.trigger('click')
  expect(wrapper.findAll('tbody tr')[0].text()).toContain('H-bonds')
  expect(wrapper.findAll('thead th')[1].attributes('aria-sort')).toBe('descending')
  await meanHeader.trigger('click')
  expect(wrapper.findAll('tbody tr')[0].text()).toContain('Salt-bridges')
  expect(wrapper.findAll('thead th')[1].attributes('aria-sort')).toBe('ascending')

  const deviationHeader = wrapper.findAll('thead button')[1]
  await deviationHeader.trigger('click')
  expect(wrapper.findAll('thead th')[2].attributes('aria-sort')).toBe('descending')

  const options = Highcharts.chart.mock.calls.at(-1)[1]
  const chart = { series: [
    { name: 'H-bonds', visible: false },
    { name: 'Salt-bridges', visible: true }
  ] }
  options.plotOptions.series.events.hide.call({ chart })
  await wrapper.vm.$nextTick()
  expect(wrapper.findAll('tbody tr')).toHaveLength(1)
  expect(wrapper.find('tbody').text()).toContain('Salt-bridges')
  wrapper.unmount()
})

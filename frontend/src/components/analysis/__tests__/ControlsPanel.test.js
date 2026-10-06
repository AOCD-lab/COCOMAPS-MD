import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'

import ControlsPanel from '../ControlsPanel.vue'
import { useChartUiStore } from '../../../stores/chartUiStore'

const CONSERVATION_CHARTS = [
  'interactionConservationMatrix',
  'filteredHeatmap',
  'line',
  'violinPlot'
]

describe('ControlsPanel conservation sliders', () => {
  let pinia
  let chartUiStore

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    chartUiStore = useChartUiStore()
  })

  const mountPanel = () => mount(ControlsPanel, {
    global: { plugins: [pinia] }
  })

  it.each(CONSERVATION_CHARTS)('shows both 0–100% sliders on %s', (chartType) => {
    chartUiStore.setChartType(chartType)
    const wrapper = mountPanel()
    const sliders = wrapper.findAll('input[type="range"]')

    expect(sliders).toHaveLength(2)
    expect(sliders.map(slider => slider.attributes('id'))).toEqual([
      'pairConservationSlider',
      'typeConservationSlider'
    ])
    sliders.forEach(slider => {
      expect(slider.attributes('min')).toBe('0')
      expect(slider.attributes('max')).toBe('1')
      expect(slider.element.value).toBe('0.5')
    })
  })

  it.each(CONSERVATION_CHARTS)('shows the shared interaction filter on %s', (chartType) => {
    chartUiStore.setChartType(chartType)
    const wrapper = mountPanel()

    expect(wrapper.find('.filter-section').exists()).toBe(true)
    expect(wrapper.find('.filter-badge').text()).toBe('17/18 selected')
  })

  it.each(['area', 'interfacePatchesList'])('does not add the shared sliders to %s', (chartType) => {
    chartUiStore.setChartType(chartType)
    const wrapper = mountPanel()

    expect(wrapper.find('#pairConservationSlider').exists()).toBe(false)
    expect(wrapper.find('#typeConservationSlider').exists()).toBe(false)
    expect(wrapper.find('.filter-section').exists()).toBe(false)
  })

  it('keeps both values when switching between chart types', async () => {
    chartUiStore.setChartType('filteredHeatmap')
    const wrapper = mountPanel()

    await wrapper.find('#pairConservationSlider').setValue('0.8')
    await wrapper.find('#typeConservationSlider').setValue('0.2')
    chartUiStore.setChartType('line')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('#pairConservationSlider').element.value).toBe('0.8')
    expect(wrapper.find('#typeConservationSlider').element.value).toBe('0.2')
  })

  it('keeps the interaction selection when switching between conservation charts', async () => {
    chartUiStore.setChartType('interactionConservationMatrix')
    const wrapper = mountPanel()

    chartUiStore.toggleInteractionType('polar-vdw')
    chartUiStore.setChartType('violinPlot')
    await wrapper.vm.$nextTick()

    expect(wrapper.find('.filter-section').exists()).toBe(true)
    expect(wrapper.find('.filter-badge').text()).toBe('16/18 selected')
    expect(chartUiStore.selectedInteractionTypes.has('polar-vdw')).toBe(false)
  })
})

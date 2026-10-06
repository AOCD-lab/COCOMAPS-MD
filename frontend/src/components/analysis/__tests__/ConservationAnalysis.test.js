import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'

import ConservationAnalysis from '../ConservationAnalysis.vue'
import ControlsPanel from '../ControlsPanel.vue'
import { useAnalysisStore } from '../../../stores/analysisStore'
import { useSystemsStore } from '../../../stores/systemsStore'

describe('ConservationAnalysis', () => {
  let pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    useSystemsStore().currentSystem = { frames: 10 }
    useAnalysisStore().interactions = [{
      id1: 'C105_A',
      id2: 'PHE160_B',
      consistency: 1,
      frames: Array.from({ length: 10 }, (_, index) => index + 1),
      typesArray: ['H-bonds'],
      typePersistence: { 'H-bonds': 1 },
      typeFrames: { 'H-bonds': Array.from({ length: 10 }, (_, index) => index + 1) }
    }]
  })

  it('shows pair conservation as a percentage of frames', () => {
    const wrapper = mount(ConservationAnalysis, {
      global: { plugins: [pinia] }
    })

    expect(wrapper.text()).toContain('100% of frames')
    expect(wrapper.text()).not.toContain('10/10 frames')
  })

  it('updates the CA subscript from the interaction type threshold slider', async () => {
    const controls = mount(ControlsPanel, { global: { plugins: [pinia] } })
    const analysis = mount(ConservationAnalysis, { global: { plugins: [pinia] } })

    expect(analysis.findAll('.metric-label')[1].find('sub').text()).toBe('50')
    await controls.find('#typeConservationSlider').setValue('0.8')
    expect(analysis.findAll('.metric-label')[1].find('sub').text()).toBe('80')
  })
})

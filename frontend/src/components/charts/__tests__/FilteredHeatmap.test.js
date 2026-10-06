import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import FilteredHeatmap from '../FilteredHeatmap.vue'
import Highcharts from '../../../utils/highchartsConfig'
import { useAnalysisStore } from '../../../stores/analysisStore'
import { useChartUiStore } from '../../../stores/chartUiStore'
import { useSystemsStore } from '../../../stores/systemsStore'

vi.mock('../../../utils/highchartsConfig', () => ({
  default: { chart: vi.fn(() => ({ destroy: vi.fn() })) },
  withExporting: options => options
}))
vi.mock('highcharts/modules/heatmap', () => ({ default: vi.fn() }))

const options = () => Highcharts.chart.mock.calls.at(-1)[1]

describe('FilteredHeatmap residue ordering', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    const pinia = createPinia()
    setActivePinia(pinia)

    useChartUiStore().currentChartType = 'filteredHeatmap'
    useChartUiStore().currentThreshold = 0
    useChartUiStore().typeConservationThreshold = 0
    useSystemsStore().currentSystem = {
      id: 'ordering-test',
      name: 'Ordering Test',
      chain1: 'A',
      chain2: 'B',
      frames: 10
    }
    useAnalysisStore().interactions = [
      {
        id1: 'GLY10_A',
        id2: 'SER30_B',
        consistency: 1,
        frameCount: 10,
        typesArray: ['H-bond'],
        typePersistence: { 'H-bond': 1 }
      },
      {
        id1: 'ALA2_A',
        id2: 'THR5_B',
        consistency: 1,
        frameCount: 10,
        typesArray: ['H-bond'],
        typePersistence: { 'H-bond': 1 }
      }
    ]
  })

  it('places ascending Y-axis residues from the bottom-left origin', () => {
    const wrapper = mount(FilteredHeatmap)

    expect(options().xAxis.categories).toEqual(['ALA2_A', 'GLY10_A'])
    expect(options().yAxis.categories).toEqual(['THR5_B', 'SER30_B'])
    expect(options().yAxis.reversed).toBe(false)
    expect(options().series[0].data.map(point => [point.x, point.y])).toEqual([
      [1, 1],
      [0, 0]
    ])

    wrapper.unmount()
  })
})

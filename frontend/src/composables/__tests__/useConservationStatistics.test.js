import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { ref } from 'vue'

import { useConservationStatistics } from '../useConservationStatistics'
import { useAnalysisStore } from '../../stores/analysisStore'
import { useChartUiStore } from '../../stores/chartUiStore'
import { useSystemsStore } from '../../stores/systemsStore'

const makeInteraction = ({ id1, id2, typePersistence }) => ({
  id1,
  id2,
  consistency: 1,
  frames: Array.from({ length: 10 }, (_, index) => index + 1),
  typesArray: Object.keys(typePersistence),
  typePersistence,
  typeFrames: Object.fromEntries(
    Object.entries(typePersistence).map(([type, persistence]) => [
      type,
      Array.from({ length: Math.round(persistence * 10) }, (_, index) => index + 1)
    ])
  )
})

describe('useConservationStatistics', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useSystemsStore().currentSystem = { frames: 10 }
  })

  it('orders equal-rank pairs by their aggregate type-conservation profile', () => {
    useAnalysisStore().interactions = [
      makeInteraction({
        id1: 'U104_A',
        id2: 'PHE160_B',
        typePersistence: { 'H-bonds': 0.8, 'Water mediated': 0.2 }
      }),
      makeInteraction({
        id1: 'C105_A',
        id2: 'PHE160_B',
        typePersistence: { 'H-bonds': 1, 'Water mediated': 0.9 }
      })
    ]

    const { statistics } = useConservationStatistics({
      pairThreshold: ref(0.7),
      typeThreshold: ref(0)
    })

    expect(statistics.value.residue.mostConservedList.map(item => ({
      pair: item.pair,
      rank: item.rank
    }))).toEqual([
      { pair: 'C105_A ↔ PHE160_B', rank: 1 },
      { pair: 'U104_A ↔ PHE160_B', rank: 1 }
    ])
  })

  it('calculates longest stretches without proximal contacts', () => {
    const chartUiStore = useChartUiStore()
    chartUiStore.setThreshold(0)
    chartUiStore.selectAllInteractionTypes()

    useAnalysisStore().interactions = [
      {
        id1: 'A1_A',
        id2: 'B1_B',
        consistency: 1,
        frames: Array.from({ length: 10 }, (_, index) => index + 1),
        typesArray: ['H-bonds', 'Proximal contacts'],
        typePersistence: { 'H-bonds': 0.4, 'Proximal contacts': 1 },
        typeFrames: {
          'H-bonds': [1, 2, 7, 8],
          'Proximal contacts': Array.from({ length: 10 }, (_, index) => index + 1)
        }
      },
      {
        id1: 'A2_A',
        id2: 'B2_B',
        consistency: 1,
        frames: Array.from({ length: 10 }, (_, index) => index + 1),
        typesArray: ['H-bonds', 'Proximal contacts'],
        typePersistence: { 'H-bonds': 0.3, 'Proximal contacts': 1 },
        typeFrames: {
          'H-bonds': [3, 4, 5],
          'Proximal contacts': Array.from({ length: 10 }, (_, index) => index + 1)
        }
      },
      {
        id1: 'A3_A',
        id2: 'B3_B',
        consistency: 1,
        frames: Array.from({ length: 10 }, (_, index) => index + 1),
        typesArray: ['Proximal contacts'],
        typePersistence: { 'Proximal contacts': 1 },
        typeFrames: {
          'Proximal contacts': Array.from({ length: 10 }, (_, index) => index + 1)
        }
      }
    ]

    const { statistics } = useConservationStatistics({
      pairThreshold: ref(0),
      typeThreshold: ref(0)
    })

    const stretches = statistics.value.residue.longestStretchList
    expect(stretches.map(item => ({
      pair: item.pair,
      stretchLength: item.stretchLength,
      types: item.types.map(type => type.type)
    }))).toEqual([
      { pair: 'A2_A ↔ B2_B', stretchLength: 3, types: ['H-bonds'] },
      { pair: 'A1_A ↔ B1_B', stretchLength: 2, types: ['H-bonds'] }
    ])
  })
})

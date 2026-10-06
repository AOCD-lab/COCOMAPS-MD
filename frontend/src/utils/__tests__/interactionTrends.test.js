import { describe, expect, it } from 'vitest'
import { buildConservationFilteredTrends, sumInteractionTrends, summarizeInteractionTrend } from '../interactionTrends'

it('computes sample statistics per interaction type across all frames', () => {
  expect(summarizeInteractionTrend([1, 3, 0, null])).toEqual({ mean: 1, standardDeviation: Math.sqrt(2) })
  expect(summarizeInteractionTrend([0, 0])).toEqual({ mean: 0, standardDeviation: 0 })
  expect(summarizeInteractionTrend([4])).toEqual({ mean: 4, standardDeviation: 0 })
})

const interactions = [
  {
    id1: 'ALA1_A',
    id2: 'GLY2_B',
    consistency: 0.75,
    typePersistence: {
      'H-bonds': 0.75,
      'Salt-bridges': 0.25
    },
    typeFrames: {
      'H-bonds': [1, 2, 3],
      'Salt-bridges': [2]
    }
  },
  {
    id1: 'SER3_A',
    id2: 'ASP4_B',
    consistency: 0.5,
    typePersistence: {
      'H-bonds': 0.5
    },
    typeFrames: {
      'H-bonds': [1, 4]
    }
  }
]

describe('buildConservationFilteredTrends', () => {
  it('recalculates every frame from qualifying residue-pair interactions', () => {
    const trends = buildConservationFilteredTrends({
      interactions,
      frameNumbers: [1, 2, 3, 4],
      pairThreshold: 0.5,
      typeThreshold: 0.5
    })

    expect(trends['h-bond']).toEqual([2, 1, 1, 1])
    expect(trends['salt-bridge']).toEqual([0, 0, 0, 0])
  })

  it('removes contributions when either conservation threshold is raised', () => {
    const pairFiltered = buildConservationFilteredTrends({
      interactions,
      frameNumbers: [1, 2, 3, 4],
      pairThreshold: 0.75,
      typeThreshold: 0.5
    })
    const typeFiltered = buildConservationFilteredTrends({
      interactions,
      frameNumbers: [1, 2, 3, 4],
      pairThreshold: 0.5,
      typeThreshold: 0.75
    })

    expect(pairFiltered['h-bond']).toEqual([1, 1, 1, 0])
    expect(typeFiltered['h-bond']).toEqual([1, 1, 1, 0])
  })

  it('counts a residue pair only once for equivalent labels in the same frame', () => {
    const trends = buildConservationFilteredTrends({
      interactions: [{
        consistency: 1,
        typePersistence: { 'H-bonds': 1, 'H-bond*': 1 },
        typeFrames: { 'H-bonds': [10, 20], 'H-bond*': [10] }
      }],
      frameNumbers: [10, 20],
      pairThreshold: 1,
      typeThreshold: 1
    })

    expect(trends['h-bond']).toEqual([1, 1])
  })
})


describe('sumInteractionTrends', () => {
  it('sums pair-type counts after conservation filtering in frame order', () => {
    const trends = buildConservationFilteredTrends({
      interactions,
      frameNumbers: [4, 2, 1, 3, 5],
      pairThreshold: 0.5,
      typeThreshold: 0.25
    })
    expect(sumInteractionTrends(trends, ['h-bond', 'salt-bridge'], 5)).toEqual([1, 2, 2, 1, 0])
    expect(sumInteractionTrends(trends, ['salt-bridge'], 5)).toEqual([0, 1, 0, 0, 0])
    const stricter = buildConservationFilteredTrends({
      interactions, frameNumbers: [1, 2, 3, 4], pairThreshold: 0.75, typeThreshold: 0.5
    })
    expect(sumInteractionTrends(stricter, ['h-bond', 'salt-bridge'], 4)).toEqual([1, 1, 1, 0])
  })

  it('preserves empty frames and does not count duplicate or unknown selections', () => {
    expect(sumInteractionTrends({ a: [2, 0, 1] }, ['a', 'a', 'unknown'], 3)).toEqual([2, 0, 1])
    expect(sumInteractionTrends({ a: [2, 1] }, [], 2)).toEqual([0, 0])
    expect(sumInteractionTrends({}, ['a'], 0)).toEqual([])
  })
})

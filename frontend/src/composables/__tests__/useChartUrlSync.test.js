import { describe, expect, it } from 'vitest'

import {
  mergeChartStateIntoQuery,
  readChartStateFromQuery,
  writeChartStateToQuery
} from '../useChartUrlSync'

describe('chart URL state', () => {
  it('reads chart state from shareable query params', () => {
    const state = readChartStateFromQuery({
      chart: 'line',
      pairThreshold: '70',
      typeThreshold: '0.8',
      patchThreshold: '90',
      logScale: '1',
      timeUnit: 'ns',
      types: 'h-bond,salt-bridge'
    })

    expect(state).toEqual({
      chart: 'line',
      pairThreshold: 0.7,
      typeThreshold: 0.8,
      patchThreshold: 0.9,
      logScale: true,
      timeUnit: 'ns',
      types: ['h-bond', 'salt-bridge']
    })
  })

  it('writes only non-default state into the query string', () => {
    expect(writeChartStateToQuery({
      chart: 'interactionConservationMatrix',
      pairThreshold: 0.5,
      typeThreshold: 0.5,
      patchThreshold: 0.7,
      logScale: false,
      timeUnit: null,
      types: [
        'pi-pi',
        'amino-pi',
        'anion-pi',
        'apolar-vdw',
        'ch-on',
        'ch-pi',
        'cation-pi',
        'clash',
        'h-bond',
        'halogen',
        'lone-pair-pi',
        'metal',
        'ons-oh-pi',
        'polar-vdw',
        'salt-bridge',
        'ss-bond',
        'water'
      ]
    })).toEqual({})
  })

  it('preserves unrelated route query params when writing chart state', () => {
    const query = mergeChartStateIntoQuery(
      { source: 'email', chart: 'area', pairThreshold: '90' },
      {
        chart: 'violinPlot',
        pairThreshold: 0.6,
        typeThreshold: 0.5,
        patchThreshold: 0.8,
        logScale: false,
        timeUnit: 'ps',
        types: ['h-bond']
      }
    )

    expect(query).toEqual({
      source: 'email',
      chart: 'violinPlot',
      pairThreshold: '60',
      patchThreshold: '80',
      timeUnit: 'ps',
      types: 'h-bond'
    })
  })

  it('round-trips an intentionally empty interaction type selection', () => {
    const query = writeChartStateToQuery({
      chart: 'filteredHeatmap',
      pairThreshold: 0.5,
      typeThreshold: 0.5,
      patchThreshold: 0.7,
      logScale: false,
      timeUnit: null,
      types: []
    })

    expect(query.types).toBe('none')
    expect(readChartStateFromQuery(query).types).toEqual([])
  })

  it('normalizes interface patch thresholds to 10% slider steps', () => {
    expect(readChartStateFromQuery({ patchThreshold: '74' }).patchThreshold).toBe(0.7)
    expect(readChartStateFromQuery({ patchThreshold: '96' }).patchThreshold).toBe(1)
  })
})

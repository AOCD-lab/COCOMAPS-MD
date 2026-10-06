import { describe, expect, it } from 'vitest'

import { INTERACTION_TYPES } from '../constants'
import {
  interactionTypesEquivalent,
  matchesSelectedTypes,
  resolveInteractionType,
  sortInteractionLegendSeries
} from '../chartHelpers'

describe('interaction type matching', () => {
  it('keeps Polar and Apolar vdW contacts distinct', () => {
    expect(resolveInteractionType('Apolar vdW contacts')?.id).toBe('apolar-vdw')
    expect(resolveInteractionType('Polar vdW contacts')?.id).toBe('polar-vdw')
    expect(interactionTypesEquivalent('Apolar vdW contacts', 'Polar vdW contacts')).toBe(false)

    expect(matchesSelectedTypes(
      'Apolar vdW contacts',
      new Set(['polar-vdw']),
      INTERACTION_TYPES
    )).toBe(false)
    expect(matchesSelectedTypes(
      'Polar vdW contacts',
      new Set(['polar-vdw']),
      INTERACTION_TYPES
    )).toBe(true)
  })

  it('matches all 18 interactions when the full filter is selected', () => {
    const selectedTypes = new Set(INTERACTION_TYPES.map(type => type.id))

    expect(selectedTypes.size).toBe(18)
    INTERACTION_TYPES.forEach((type) => {
      expect(matchesSelectedTypes(type.label, selectedTypes, INTERACTION_TYPES)).toBe(true)
    })
  })

  it('does not let an Apolar data series consume the Polar legend slot', () => {
    const legendNames = ['Apolar vdW contacts']

    INTERACTION_TYPES.forEach((type) => {
      const alreadyRepresented = legendNames.some(name => (
        interactionTypesEquivalent(name, type.label, INTERACTION_TYPES)
      ))
      if (!alreadyRepresented) legendNames.push(type.label)
    })

    expect(legendNames).toHaveLength(18)
    expect(legendNames).toContain('Apolar vdW contacts')
    expect(legendNames).toContain('Polar vdW contacts')
  })

  it('keeps occurrence order while moving deselected interactions to the end', () => {
    const series = [
      { name: 'Second observed', _hasData: true },
      { name: 'Deselected', _hasData: false, _isDeselected: true },
      { name: 'First selected without data', _hasData: false },
      { name: 'First observed', _hasData: true },
      { name: 'Atom Changes', _hasData: true, _isAnnotation: true },
      { name: 'Second selected without data', _hasData: false }
    ]

    expect(sortInteractionLegendSeries(series).map(item => item.name)).toEqual([
      'Second observed',
      'First observed',
      'Atom Changes',
      'First selected without data',
      'Second selected without data',
      'Deselected'
    ])
  })

  it('places selected Proximal contacts immediately before Atom Changes', () => {
    const series = [
      { name: 'H-bonds', _hasData: true },
      { name: 'Proximal contacts', _hasData: true },
      { name: 'Polar vdW contacts', _hasData: true },
      { name: 'Selected without data', _hasData: false },
      { name: 'Atom Changes', _hasData: true, _isAnnotation: true },
      { name: 'Deselected', _hasData: false, _isDeselected: true }
    ]

    expect(sortInteractionLegendSeries(series).map(item => item.name)).toEqual([
      'H-bonds',
      'Polar vdW contacts',
      'Proximal contacts',
      'Atom Changes',
      'Selected without data',
      'Deselected'
    ])
  })

  it('keeps Proximal contacts with selected no-data interactions when it has no data', () => {
    const series = [
      { name: 'H-bonds', _hasData: true },
      { name: 'Proximal contacts', _hasData: false },
      { name: 'Salt-bridges', _hasData: false }
    ]

    expect(sortInteractionLegendSeries(series).map(item => item.name)).toEqual([
      'H-bonds',
      'Proximal contacts',
      'Salt-bridges'
    ])
  })

  it('keeps deselected Proximal contacts in the final deselected group', () => {
    const series = [
      { name: 'H-bonds', _hasData: true },
      { name: 'Proximal contacts', _hasData: false, _isDeselected: true },
      { name: 'Atom Changes', _hasData: true, _isAnnotation: true },
      { name: 'Salt-bridges', _hasData: false, _isDeselected: true }
    ]

    expect(sortInteractionLegendSeries(series).map(item => item.name)).toEqual([
      'H-bonds',
      'Atom Changes',
      'Proximal contacts',
      'Salt-bridges'
    ])
  })
})

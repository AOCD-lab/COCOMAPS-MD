import { describe, expect, it } from 'vitest'

import {
  buildInterfacePatchCache,
  buildInterfacePatches,
  normalizeInterfacePatchThreshold
} from '../interfacePatches'

const residue = (chain, resNum, resName) => ({ chain, resNum, resName })

const edges = [
  {
    source: residue('A', 1, 'ALA'),
    target: residue('B', 10, 'GLY'),
    frameCount: 10,
    conservation: 1
  },
  {
    source: residue('B', 10, 'GLY'),
    target: residue('A', 2, 'SER'),
    frameCount: 7,
    conservation: 0.7
  },
  {
    source: residue('A', 3, 'TYR'),
    target: residue('B', 11, 'LYS'),
    frameCount: 5,
    conservation: 0.5
  }
]

describe('interface patch derivation', () => {
  it('builds connected components at the selected conservation threshold', () => {
    const patches = buildInterfacePatches(edges, 10, 0.7)

    expect(patches).toHaveLength(1)
    expect(patches[0]).toMatchObject({ id: 1, size: 3, chains: ['A', 'B'] })
    expect(patches[0].residues.map((item) => `${item.chain}:${item.resNum}`)).toEqual([
      'A:1',
      'A:2',
      'B:10'
    ])
  })

  it('splits patches as the threshold increases', () => {
    expect(buildInterfacePatches(edges, 10, 0.5).map((patch) => patch.size)).toEqual([3])
    expect(buildInterfacePatches(edges, 10, 1).map((patch) => patch.size)).toEqual([])
    expect(buildInterfacePatches(edges, 10, 0.5, 2).map((patch) => patch.size)).toEqual([3])
  })

  it('precomputes all six slider states and normalizes arbitrary input', () => {
    const cache = buildInterfacePatchCache(edges, 10)

    expect([...cache.keys()]).toEqual([0.5, 0.6, 0.7, 0.8, 0.9, 1])
    expect(cache.get(0.7)[0].size).toBe(3)
    expect(buildInterfacePatchCache(edges, 10, 3).get(0.5)).toHaveLength(1)
    expect(normalizeInterfacePatchThreshold(0.74)).toBe(0.7)
    expect(normalizeInterfacePatchThreshold(0.2)).toBe(0.5)
  })
})

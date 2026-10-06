export const INTERFACE_PATCH_THRESHOLDS = Object.freeze([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
export const DEFAULT_INTERFACE_PATCH_THRESHOLD = 0.7

const residueKey = (residue) => `${String(residue?.chain ?? '')}:${String(residue?.resNum ?? '')}`

const compareResidues = (left, right) => {
  const chainOrder = String(left?.chain ?? '').localeCompare(String(right?.chain ?? ''))
  if (chainOrder !== 0) return chainOrder

  const leftNumber = Number(left?.resNum)
  const rightNumber = Number(right?.resNum)
  if (Number.isFinite(leftNumber) && Number.isFinite(rightNumber) && leftNumber !== rightNumber) {
    return leftNumber - rightNumber
  }
  return String(left?.resNum ?? '').localeCompare(String(right?.resNum ?? ''))
}

const normalizedThreshold = (threshold) => {
  const numeric = Number(threshold)
  if (!Number.isFinite(numeric)) return DEFAULT_INTERFACE_PATCH_THRESHOLD
  return Math.min(1, Math.max(0.5, Math.round(numeric * 10) / 10))
}

const edgeConservation = (edge, totalFrames) => {
  const frameCount = Number(edge?.frameCount)
  if (Number.isFinite(frameCount) && totalFrames > 0) return frameCount / totalFrames

  const conservation = Number(edge?.conservation)
  return Number.isFinite(conservation) ? conservation : 0
}

export function buildInterfacePatches(edges, totalFrames, threshold, minSize = 3) {
  const selectedThreshold = normalizedThreshold(threshold)
  const frameTotal = Number(totalFrames) || 0
  const adjacency = new Map()
  const residuesByKey = new Map()

  const ensureNode = (residue) => {
    const key = residueKey(residue)
    if (!residuesByKey.has(key)) {
      residuesByKey.set(key, {
        chain: residue.chain,
        resNum: residue.resNum,
        resName: residue.resName || 'UNK'
      })
      adjacency.set(key, new Set())
    }
    return key
  }

  for (const edge of edges || []) {
    if (!edge?.source || !edge?.target) continue
    if (edgeConservation(edge, frameTotal) + Number.EPSILON < selectedThreshold) continue

    const sourceKey = ensureNode(edge.source)
    const targetKey = ensureNode(edge.target)
    if (sourceKey === targetKey) continue
    adjacency.get(sourceKey).add(targetKey)
    adjacency.get(targetKey).add(sourceKey)
  }

  const visited = new Set()
  const components = []

  for (const startKey of adjacency.keys()) {
    if (visited.has(startKey)) continue
    const stack = [startKey]
    const componentKeys = []
    visited.add(startKey)

    while (stack.length > 0) {
      const key = stack.pop()
      componentKeys.push(key)
      for (const neighbor of adjacency.get(key) || []) {
        if (visited.has(neighbor)) continue
        visited.add(neighbor)
        stack.push(neighbor)
      }
    }

    if (componentKeys.length < Math.max(3, minSize)) continue
    components.push(componentKeys)
  }

  return components
    .map((componentKeys) => {
      const componentKeySet = new Set(componentKeys)
      const residues = componentKeys
        .map((key) => {
          const residue = residuesByKey.get(key)
          const connectedTo = [...(adjacency.get(key) || [])]
            .filter((neighborKey) => componentKeySet.has(neighborKey))
            .map((neighborKey) => ({ ...residuesByKey.get(neighborKey) }))
            .sort(compareResidues)
          return { ...residue, connectedTo }
        })
        .sort(compareResidues)
      const signature = residues.map(residueKey).join('|')

      return {
        signature,
        size: residues.length,
        chains: [...new Set(residues.map((residue) => residue.chain))].sort(),
        residues
      }
    })
    .sort((left, right) => right.size - left.size || left.signature.localeCompare(right.signature))
    .map((patch, index) => ({ ...patch, id: index + 1 }))
}

export function buildInterfacePatchCache(edges, totalFrames, minSize = 3) {
  return new Map(
    INTERFACE_PATCH_THRESHOLDS.map((threshold) => [
      threshold,
      buildInterfacePatches(edges, totalFrames, threshold, minSize)
    ])
  )
}

export function normalizeInterfacePatchThreshold(threshold) {
  return normalizedThreshold(threshold)
}

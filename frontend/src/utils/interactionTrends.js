import { INTERACTION_TYPES } from './constants'
import { resolveInteractionType } from './chartHelpers'

/** Sum selected canonical type counts, preserving zero-count frames. */
export function sumInteractionTrends(trendsByTypeId, selectedTypeIds, frameCount) {
  const totals = Array(frameCount).fill(0)
  for (const typeId of new Set(selectedTypeIds)) {
    const counts = trendsByTypeId[typeId] || []
    totals.forEach((_, index) => { totals[index] += counts[index] ?? 0 })
  }
  return totals
}

/** Summarize one interaction type across the whole trajectory, including zeros. */
export function summarizeInteractionTrend(counts = []) {
  const values = counts.map(value => Number(value) || 0)
  if (!values.length) return { mean: 0, standardDeviation: 0 }
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length
  const variance = values.length > 1
    ? values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / (values.length - 1)
    : 0
  return { mean, standardDeviation: Math.sqrt(variance) }
}

/**
 * Reconstruct per-frame interaction trends after applying residue-pair and
 * pair-type conservation thresholds.
 *
 * Each interaction entry represents one residue pair. A qualifying pair
 * contributes at most one count to a canonical interaction type in a frame,
 * even when equivalent raw labels are present in the source data.
 */
export function buildConservationFilteredTrends({
  interactions = [],
  frameNumbers = [],
  pairThreshold = 0,
  typeThreshold = 0,
  interactionTypes = INTERACTION_TYPES
} = {}) {
  const normalizedFrameNumbers = frameNumbers.map(frame => Number(frame))
  const frameIndex = new Map(
    normalizedFrameNumbers.map((frame, index) => [frame, index])
  )
  const knownTypeIds = new Set(interactionTypes.map(type => type.id))
  const trendsByTypeId = Object.fromEntries(
    interactionTypes.map(type => [type.id, Array(normalizedFrameNumbers.length).fill(0)])
  )

  interactions.forEach((interaction) => {
    const pairConservation = Number(interaction.consistency)
    if (!Number.isFinite(pairConservation) || pairConservation < pairThreshold) return

    const qualifyingFramesByType = new Map()
    const typePersistence = interaction.typePersistence || {}
    const typeFrames = interaction.typeFrames || {}

    Object.entries(typeFrames).forEach(([rawType, frames]) => {
      const resolvedType = resolveInteractionType(rawType, interactionTypes)
      if (!resolvedType || !knownTypeIds.has(resolvedType.id) || !Array.isArray(frames)) return

      const persistence = Number(typePersistence[rawType])
      if (!Number.isFinite(persistence) || persistence < typeThreshold) return

      if (!qualifyingFramesByType.has(resolvedType.id)) {
        qualifyingFramesByType.set(resolvedType.id, new Set())
      }
      const qualifyingFrames = qualifyingFramesByType.get(resolvedType.id)
      frames.forEach(frame => qualifyingFrames.add(Number(frame)))
    })

    qualifyingFramesByType.forEach((frames, typeId) => {
      frames.forEach((frame) => {
        const index = frameIndex.get(frame)
        if (index !== undefined) trendsByTypeId[typeId][index] += 1
      })
    })
  })

  return trendsByTypeId
}

/**
 * Chart helper functions
 */

import { INTERACTION_TYPES } from './constants'

const INTERACTION_COLOR_RULES = [
  { color: [47, 79, 79], keywords: ['π-π', 'pi-pi', 'pi pi'] }, // π-π interaction
  { color: [152, 251, 152], keywords: ['amino-pi', 'amino_pi', 'amino-π', 'polar-π', 'polar-pi'] }, // Polar-π (Amino-π)
  { color: [255, 0, 255], keywords: ['anion-π', 'anion-pi', 'anion_pi'] }, // Anion-π interaction
  { color: [60, 95, 95], keywords: ['apolar vdw', 'apolar_vdw'] }, // Apolar vdW contact
  { color: [173, 216, 230], keywords: ['ch-o', 'c-h_on', 'c-h on', 'ch-on'] }, // CH-O/N bond
  { color: [34, 139, 34], keywords: ['ch-π', 'ch-pi', 'c-h_pi'] }, // CH-π interaction
  { color: [0, 255, 255], keywords: ['cation-π', 'cation-pi', 'cation_pi'] }, // Cation-π interaction
  { color: [139, 0, 0], keywords: ['clash'] }, // Clash
  { color: [75, 0, 130], keywords: ['h-bond*', 'h-bond', 'hydrogen bond'] }, // H-bond
  { color: [85, 107, 47], keywords: ['halogen'] }, // Halogen bond
  { color: [70, 130, 180], keywords: ['lp-π', 'lp-pi', 'lone pair', 'lone_pair_pi'] }, // lp-π interaction
  { color: [139, 69, 19], keywords: ['metal mediated', 'metal_mediated', 'metal-mediated'] }, // Metal mediated contact
  { color: [90, 75, 170], keywords: ['n-s-o-h', 'n-s-o-h_pi', 'o/n/sh'] }, // O/N/SH-π interaction
  { color: [255, 0, 127], keywords: ['polar vdw', 'polar_vdw'] }, // Polar vdW contact
  { color: [54, 69, 79], keywords: ['proximal'] }, // Proximal contact
  { color: [128, 0, 128], keywords: ['salt-bridge', 'salt bridge'] }, // Salt-bridge
  { color: [255, 103, 0], keywords: ['s-bond', 'ss bond', 's-s bond', 'ss_bond', 's-s'] }, // S / S-S bond
  { color: [72, 61, 139], keywords: ['water', 'water mediated', 'water_mediated', 'water-mediated'] } // Water mediated contact
]

function findInteractionColor(typeString) {
  const normalized = typeString.toLowerCase()
  for (const rule of INTERACTION_COLOR_RULES) {
    if (rule.keywords.some(keyword => normalized.includes(keyword.toLowerCase()))) {
      return rule.color
    }
  }
  return [75, 0, 130] // default (indigo)
}

/**
 * Get color for interaction type based on the fixed palette
 */
export function getInteractionColor(types, consistency) {
  const baseColor = findInteractionColor(types)
  const opacity = 0.3 + (consistency * 0.6)
  return `rgba(${baseColor[0]}, ${baseColor[1]}, ${baseColor[2]}, ${opacity})`
}

export function getInteractionBaseColor(typeLabel) {
  const color = findInteractionColor(typeLabel)
  return `rgb(${color[0]}, ${color[1]}, ${color[2]})`
}

/**
 * Return text color (white or dark) for contrast on getInteractionBaseColor background.
 */
export function getTextColorForBg(typeLabel) {
  const colorStr = getInteractionBaseColor(typeLabel)
  const match = colorStr.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/)
  if (!match) return '#ffffff'
  const r = parseInt(match[1], 10)
  const g = parseInt(match[2], 10)
  const b = parseInt(match[3], 10)
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
  return luminance > 0.5 ? '#1d1d1f' : '#ffffff'
}

const normalizeInteractionTypeText = (value) => String(value ?? '')
  .normalize('NFKC')
  .trim()
  .toLowerCase()

/**
 * Resolve a raw trajectory label to one canonical interaction definition.
 *
 * Longest-match selection is intentional: "Apolar vdW contacts" also contains
 * the text "polar vdW", so accepting the first substring match can merge the
 * two biologically distinct contact classes.
 */
export function resolveInteractionType(rawType, interactionTypeList = INTERACTION_TYPES) {
  const normalizedRawType = normalizeInteractionTypeText(rawType)
  if (!normalizedRawType) return null

  let bestMatch = null
  let bestMatchLength = -1

  interactionTypeList.forEach((interactionType) => {
    const aliases = [
      interactionType.label,
      interactionType.trendLabel,
      ...(interactionType.keywords || [])
    ]

    aliases.forEach((alias) => {
      const normalizedAlias = normalizeInteractionTypeText(alias)
      if (
        normalizedAlias &&
        normalizedRawType.includes(normalizedAlias) &&
        normalizedAlias.length > bestMatchLength
      ) {
        bestMatch = interactionType
        bestMatchLength = normalizedAlias.length
      }
    })
  })

  return bestMatch
}

export function interactionTypesEquivalent(
  firstType,
  secondType,
  interactionTypeList = INTERACTION_TYPES
) {
  const firstResolved = resolveInteractionType(firstType, interactionTypeList)
  const secondResolved = resolveInteractionType(secondType, interactionTypeList)

  if (firstResolved && secondResolved) {
    return firstResolved.id === secondResolved.id
  }

  return normalizeInteractionTypeText(firstType) === normalizeInteractionTypeText(secondType)
}

/**
 * Keep data-backed interactions in their existing occurrence order, with
 * data-backed Proximal contacts at the tail of that group. Chart annotations
 * follow the existing interactions, then selected no-data entries, and finally
 * deselected interactions. This places Proximal contacts immediately before
 * Atom Changes when both have data without moving Proximal contacts past the
 * no-data entries. Array sorting is stable within each group.
 */
export function sortInteractionLegendSeries(series) {
  const rank = (item) => {
    if (item._isDeselected) return 4
    if (item._isAnnotation) return 2
    if (item._hasData && resolveInteractionType(item.name)?.id === 'proximal') return 1
    if (item._hasData) return 0
    return 3
  }

  return [...series].sort((first, second) => rank(first) - rank(second))
}

/**
 * Check if interaction matches selected types
 */
export function matchesSelectedTypes(interactionTypes, selectedTypes, interactionTypeList) {
  if (selectedTypes.size === 0) return false

  const rawTypes = Array.isArray(interactionTypes)
    ? interactionTypes
    : String(interactionTypes ?? '').split(';')

  return rawTypes.some((rawType) => {
    const resolvedType = resolveInteractionType(rawType, interactionTypeList)
    return resolvedType ? selectedTypes.has(resolvedType.id) : false
  })
}

/**
 * Unified residue formatting helpers
 */
const residueIdPattern = /^([A-Za-z0-9]+?)(\d+)_([A-Za-z0-9]+)$/

export function formatResidueId(resName, resNum, chain) {
  if (!resName || resNum === undefined || resNum === null || !chain) return ''
  return `${String(resName).trim()}${resNum}_${String(chain).trim()}`
}

export function parseResidueId(id) {
  if (!id) return null
  const match = String(id).match(residueIdPattern)
  if (!match) return null
  return { resName: match[1], resNum: match[2], chain: match[3] }
}

export function formatResiduePairFromParts(res1, res2, delimiter = ' ↔ ') {
  if (!res1 || !res2) return ''
  return `${formatResidueId(res1.resName, res1.resNum, res1.chain)}${delimiter}${formatResidueId(res2.resName, res2.resNum, res2.chain)}`
}

export function formatResiduePairFromIds(id1, id2, delimiter = ' ↔ ') {
  if (!id1 || !id2) return ''
  return `${id1}${delimiter}${id2}`
}

export function formatPairKey(id1, id2) {
  return `${id1}__${id2}`
}

/**
 * Export INTERACTION_TYPES for use in components
 */
export { INTERACTION_TYPES }

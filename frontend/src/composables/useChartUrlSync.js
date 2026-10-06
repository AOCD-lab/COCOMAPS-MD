import { watch } from 'vue'
import { INTERACTION_TYPES } from '../utils/constants'
import {
  DEFAULT_INTERFACE_PATCH_THRESHOLD,
  normalizeInterfacePatchThreshold
} from '../utils/interfacePatches'

const QUERY_KEYS = new Set([
  'chart',
  'pairThreshold',
  'typeThreshold',
  'patchThreshold',
  'types',
  'logScale',
  'timeUnit'
])

const CHART_TYPES = [
  'interactionConservationMatrix',
  'filteredHeatmap',
  'line',
  'violinPlot',
  'area',
  'interfacePatchesList'
]

const DEFAULT_STATE = {
  chart: 'interactionConservationMatrix',
  pairThreshold: 0.5,
  typeThreshold: 0.5,
  patchThreshold: DEFAULT_INTERFACE_PATCH_THRESHOLD,
  logScale: false,
  timeUnit: null,
  types: INTERACTION_TYPES.filter(type => type.id !== 'proximal').map(type => type.id)
}

const validChartTypes = new Set(CHART_TYPES)
const validInteractionTypes = new Set(INTERACTION_TYPES.map(type => type.id))

const firstQueryValue = (value) => {
  if (Array.isArray(value)) return value[0]
  return value
}

const clamp = (value, min, max) => Math.min(max, Math.max(min, value))

const readThreshold = (queryValue, fallback) => {
  const rawValue = firstQueryValue(queryValue)
  if (rawValue === undefined || rawValue === null || rawValue === '') return fallback

  const numberValue = Number(rawValue)
  if (!Number.isFinite(numberValue)) return fallback

  return clamp(numberValue <= 1 ? numberValue : numberValue / 100, 0, 1)
}

const readBoolean = (queryValue) => {
  const rawValue = String(firstQueryValue(queryValue) || '').toLowerCase()
  return rawValue === '1' || rawValue === 'true' || rawValue === 'yes'
}

const normalizeTypeIds = (typeIds) => {
  const requestedTypes = new Set(typeIds)
  return INTERACTION_TYPES
    .map(type => type.id)
    .filter(typeId => requestedTypes.has(typeId))
}

const sameArray = (left, right) => {
  if (left.length !== right.length) return false
  return left.every((value, index) => value === right[index])
}

const thresholdToQueryValue = (threshold) => String(Math.round(clamp(threshold, 0, 1) * 100))

export const readChartStateFromQuery = (query) => {
  const chart = firstQueryValue(query.chart)
  const typesValue = firstQueryValue(query.types)
  let types = DEFAULT_STATE.types

  if (typesValue === 'none' || typesValue === '') {
    types = []
  } else if (typesValue) {
    const parsedTypes = normalizeTypeIds(String(typesValue).split(',').filter(Boolean))
    types = parsedTypes.length > 0 ? parsedTypes : DEFAULT_STATE.types
  }

  const timeUnit = firstQueryValue(query.timeUnit)

  return {
    chart: validChartTypes.has(chart) ? chart : DEFAULT_STATE.chart,
    pairThreshold: readThreshold(query.pairThreshold, DEFAULT_STATE.pairThreshold),
    typeThreshold: readThreshold(query.typeThreshold, DEFAULT_STATE.typeThreshold),
    patchThreshold: normalizeInterfacePatchThreshold(
      readThreshold(query.patchThreshold, DEFAULT_STATE.patchThreshold)
    ),
    logScale: readBoolean(query.logScale),
    timeUnit: timeUnit ? String(timeUnit) : DEFAULT_STATE.timeUnit,
    types
  }
}

export const readChartStateFromStore = (chartUiStore) => ({
  chart: validChartTypes.has(chartUiStore.currentChartType)
    ? chartUiStore.currentChartType
    : DEFAULT_STATE.chart,
  pairThreshold: clamp(Number(chartUiStore.currentThreshold), 0, 1),
  typeThreshold: clamp(Number(chartUiStore.typeConservationThreshold), 0, 1),
  patchThreshold: normalizeInterfacePatchThreshold(chartUiStore.interfacePatchThreshold),
  logScale: Boolean(chartUiStore.useLogScale),
  timeUnit: chartUiStore.timeUnit ? String(chartUiStore.timeUnit) : null,
  types: normalizeTypeIds([...chartUiStore.selectedInteractionTypes])
})

export const writeChartStateToQuery = (state) => {
  const query = {}

  if (state.chart !== DEFAULT_STATE.chart) query.chart = state.chart

  if (thresholdToQueryValue(state.pairThreshold) !== thresholdToQueryValue(DEFAULT_STATE.pairThreshold)) {
    query.pairThreshold = thresholdToQueryValue(state.pairThreshold)
  }

  if (thresholdToQueryValue(state.typeThreshold) !== thresholdToQueryValue(DEFAULT_STATE.typeThreshold)) {
    query.typeThreshold = thresholdToQueryValue(state.typeThreshold)
  }

  if (thresholdToQueryValue(state.patchThreshold) !== thresholdToQueryValue(DEFAULT_STATE.patchThreshold)) {
    query.patchThreshold = thresholdToQueryValue(state.patchThreshold)
  }

  if (state.logScale) query.logScale = '1'
  if (state.timeUnit) query.timeUnit = state.timeUnit

  if (!sameArray(state.types, DEFAULT_STATE.types)) {
    query.types = state.types.length > 0 ? state.types.join(',') : 'none'
  }

  return query
}

const withoutChartQuery = (query) => Object.fromEntries(
  Object.entries(query).filter(([key]) => !QUERY_KEYS.has(key))
)

const stringifyQuery = (query) => JSON.stringify(
  Object.entries(query)
    .filter(([, value]) => value !== undefined)
    .sort(([left], [right]) => left.localeCompare(right))
)

export const mergeChartStateIntoQuery = (query, state) => ({
  ...withoutChartQuery(query),
  ...writeChartStateToQuery(state)
})

export const useChartUrlSync = ({ route, router, chartUiStore }) => {
  let applyingRoute = false
  let updatingRoute = false

  const applyQueryToStore = () => {
    applyingRoute = true
    try {
      const state = readChartStateFromQuery(route.query)
      chartUiStore.setChartType(state.chart)
      chartUiStore.setThreshold(state.pairThreshold)
      chartUiStore.setTypeConservationThreshold(state.typeThreshold)
      chartUiStore.setInterfacePatchThreshold(state.patchThreshold)
      chartUiStore.setLogScale(state.logScale)
      chartUiStore.setTimeUnit(state.timeUnit)
      chartUiStore.setInteractionTypes(state.types)
    } finally {
      applyingRoute = false
    }
  }

  watch(
    () => route.query,
    () => {
      if (!updatingRoute) applyQueryToStore()
    },
    { immediate: true }
  )

  watch(
    () => readChartStateFromStore(chartUiStore),
    async (state) => {
      if (applyingRoute) return

      const nextQuery = mergeChartStateIntoQuery(route.query, state)
      if (stringifyQuery(nextQuery) === stringifyQuery(route.query)) return

      updatingRoute = true
      try {
        await router.replace({ query: nextQuery })
      } finally {
        updatingRoute = false
      }
    },
    { deep: true }
  )
}

/**
 * Per-system analysis payloads from the API (interactions, area, trends, interface patches).
 */
import { defineStore } from 'pinia'
import api from '../services/api'
import { matchesSelectedTypes } from '../utils/chartHelpers'
import { INTERACTION_TYPES } from '../utils/constants'
import { useChartUiStore } from './chartUiStore'

export const useAnalysisStore = defineStore('analysis', {
  state: () => ({
    interactions: [],
    areaData: [],
    trends: {},
    trendFrameNumbers: [],
    interfacePatchEdges: [],
    interfacePatchTotalFrames: 0,
    interfacePatchMinimumSize: 3,

    loading: {
      interactions: false,
      area: false,
      trends: false,
      interfacePatches: false
    },

    errors: {
      interactions: null,
      area: null,
      trends: null,
      interfacePatches: null
    }
  }),

  getters: {
    filteredInteractions: (state) => {
      const ui = useChartUiStore()
      return state.interactions.filter(d => {
        const thresholdPercent = Math.round(ui.currentThreshold * 100)
        const consistencyPercent = Math.round(d.consistency * 100)
        if (consistencyPercent < thresholdPercent) return false
        if (ui.selectedInteractionTypes.size === 0) return false

        const typesString = d.typesArray.join('; ')
        return matchesSelectedTypes(typesString, ui.selectedInteractionTypes, INTERACTION_TYPES)
      })
    }
  },

  actions: {
    async loadInteractions(resource) {
      this.loading.interactions = true
      this.errors.interactions = null
      try {
        const data = await api.getInteractions(resource)
        this.interactions = data.interactions || []
      } catch (error) {
        this.errors.interactions = error.message
        console.error('Error loading interactions:', error)
      } finally {
        this.loading.interactions = false
      }
    },

    async loadAreaData(resource) {
      this.loading.area = true
      this.errors.area = null
      try {
        const data = await api.getAreaData(resource)
        this.areaData = data.frames || []
      } catch (error) {
        this.errors.area = error.message
        console.error('Error loading area data:', error)
      } finally {
        this.loading.area = false
      }
    },

    async loadTrends(resource) {
      this.loading.trends = true
      this.errors.trends = null
      try {
        const data = await api.getTrends(resource)
        this.trends = data.trends || {}
        this.trendFrameNumbers = data.frameNumbers || []
      } catch (error) {
        this.errors.trends = error.message
        console.error('Error loading trends:', error)
      } finally {
        this.loading.trends = false
      }
    },

    async loadInterfacePatches(resource) {
      this.loading.interfacePatches = true
      this.errors.interfacePatches = null
      try {
        const data = await api.getInterfacePatches(resource)
        this.interfacePatchEdges = data.edges || []
        this.interfacePatchTotalFrames = Number(data.totalFrames) || 0
        this.interfacePatchMinimumSize = Math.max(3, Number(data.minimumPatchSize) || 3)
      } catch (error) {
        this.errors.interfacePatches = error.message
        this.interfacePatchEdges = []
        this.interfacePatchTotalFrames = 0
        this.interfacePatchMinimumSize = 3
        console.error('Error loading interface patches:', error)
      } finally {
        this.loading.interfacePatches = false
      }
    }
  }
})

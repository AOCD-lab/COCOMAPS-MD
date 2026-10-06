/**
 * Loaded systems / jobs and current selection.
 */
import { defineStore } from 'pinia'
import api from '../services/api'
import { useAnalysisStore } from './analysisStore'

export const useSystemsStore = defineStore('systems', {
  state: () => ({
    systems: [],
    currentSystem: null,
    isLoading: false,
    error: null
  }),

  getters: {
    totalFrames: (state) => state.currentSystem?.frames || 0
  },

  actions: {
    async loadSystems() {
      this.isLoading = true
      this.error = null
      try {
        this.systems = await api.getSystems()
      } catch (error) {
        this.error = error.message
        console.error('Error loading systems:', error)
      } finally {
        this.isLoading = false
      }
    },

    async setCurrentSystem(systemId) {
      const system = this.systems.find(s => s.id === systemId)
      if (!system) return

      this.currentSystem = system

      const analysis = useAnalysisStore()
      await Promise.all([
        analysis.loadInteractions(system),
        analysis.loadAreaData(system),
        analysis.loadTrends(system),
        analysis.loadInterfacePatches(system)
      ])
    },

    async loadAnalysisByJobId(jobId) {
      this.isLoading = true
      this.error = null
      try {
        const system = await api.getAnalysis(jobId)
        this.currentSystem = system

        const existing = this.systems.findIndex(s => s.jobId === system.jobId)
        if (existing === -1) {
          this.systems.push(system)
        } else {
          this.systems[existing] = system
        }

        const analysis = useAnalysisStore()
        await Promise.all([
          analysis.loadInteractions(system),
          analysis.loadAreaData(system),
          analysis.loadTrends(system),
          analysis.loadInterfacePatches(system)
        ])
        return system
      } catch (error) {
        this.error = error.message
        console.error('Error loading analysis:', error)
        return null
      } finally {
        this.isLoading = false
      }
    }
  }
})

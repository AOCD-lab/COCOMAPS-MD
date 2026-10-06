/**
 * API service for communicating with Flask backend
 */
import axios from 'axios'

const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? 'http://localhost:5001/api' : `${import.meta.env.BASE_URL}api`)

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json'
  },
  timeout: 30000 // 30 second timeout
})

// Add response interceptor for error handling
api.interceptors.response.use(
  response => response,
  error => {
    if (error.response) {
      // Server responded with error status
      const message = error.response.data?.error || error.response.data?.message || error.message
      return Promise.reject(new Error(message || 'Server error'))
    } else if (error.request) {
      // Request made but no response
      return Promise.reject(new Error('No response from server. Make sure the backend container is running and /api is being reverse proxied.'))
    } else {
      // Error setting up request
      return Promise.reject(new Error(error.message || 'Request failed'))
    }
  }
)

function encodeSegment(value) {
  return encodeURIComponent(String(value))
}

function resourcePath(resource) {
  if (resource && typeof resource === 'object') {
    if (resource.jobId) return `/analysis/${encodeSegment(resource.jobId)}`
    if (resource.id) return `/systems/${encodeSegment(resource.id)}`
  }
  return `/systems/${encodeSegment(resource)}`
}

export default {
  // Systems
  async getSystems() {
    const response = await api.get('/systems')
    return response.data
  },

  async getSystem(systemId) {
    const response = await api.get(`/systems/${systemId}`)
    return response.data
  },

  async getAnalysis(jobId) {
    const response = await api.get(`/analysis/${encodeSegment(jobId)}`)
    return response.data
  },

  // Data
  async getInteractions(resource) {
    const response = await api.get(`${resourcePath(resource)}/interactions`)
    return response.data
  },

  async getAreaData(resource) {
    const response = await api.get(`${resourcePath(resource)}/area`)
    return response.data
  },

  async getTrends(resource) {
    const response = await api.get(`${resourcePath(resource)}/trends`)
    return response.data
  },

  async getAtomPairs(resource, params) {
    const response = await api.get(`${resourcePath(resource)}/atom-pairs`, { params })
    return response.data
  },

  async getAtomPairsBatch(resource, pairs) {
    const response = await api.post(`${resourcePath(resource)}/atom-pairs/batch`, { pairs })
    return response.data
  },

  async getInteractionDistances(resource) {
    const response = await api.get(`${resourcePath(resource)}/interaction-distances`)
    return response.data
  },

  async getInterfacePatches(resource) {
    const response = await api.get(`${resourcePath(resource)}/interface-patches`)
    return response.data
  },

  /**
   * Get the URL for a frame's PDB file (for Mol* viewer).
   * Uses current origin in dev (Vite proxy) or VITE_API_URL when set.
   */
  getFramePdbUrl(resource, frameNum = 1) {
    const base = import.meta.env.VITE_API_URL
    const path = `${resourcePath(resource)}/frame/${frameNum}/pdb`
    if (base) {
      return `${base.replace(/\/$/, '')}${path}`
    }
    return `${typeof window !== 'undefined' ? window.location.origin : ''}${import.meta.env.BASE_URL}api${path}`
  },

  /**
   * Fetch PDB file content for a frame (for Mol* loadStructureFromData).
   * Uses same-origin URL in dev (Vite proxy) so the request appears in Network tab
   * and avoids CORS. Falls back to direct API URL when VITE_API_URL is set.
   */
  async getFramePdbContent(resource, frameNum = 1) {
    const base = import.meta.env.VITE_API_URL
    const path = `${resourcePath(resource)}/frame/${frameNum}/pdb`
    const url = base
      ? `${base.replace(/\/$/, '')}${path}`
      : `${import.meta.env.BASE_URL}api${path}`
    const res = await fetch(url)
    if (!res.ok) throw new Error(`Failed to load PDB: ${res.status} ${res.statusText}`)
    return res.text()
  },

  async getDistanceDistributions(resource, interactionTypes, minConsistency) {
    const params = {}
    if (interactionTypes && interactionTypes.length > 0) {
      params.interaction_types = interactionTypes.join(',')
    }
    if (minConsistency !== undefined && minConsistency !== null) {
      params.min_consistency = minConsistency
    }
    const response = await api.get(`${resourcePath(resource)}/distance-distributions`, { params })
    return response.data
  },

  // Upload
  async uploadFile(file, onProgress) {
    const formData = new FormData()
    formData.append('file', file)

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      // Large MD trajectories take far longer than the 30s default to transfer;
      // disable the timeout so the upload isn't aborted mid-flight.
      timeout: 0,
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percentCompleted)
        }
      }
    })
    return response.data
  },

  async getStatus(jobId) {
    const response = await api.get(`/status/${jobId}`)
    return response.data
  },

  async lookupJobs(ids) {
    const response = await api.post('/jobs/lookup', { ids })
    return response.data
  },

  /**
   * Upload file with full configuration options
   * @param {File} file - The PDB file to upload
   * @param {Object} options - Configuration options
   * @param {string} options.jobName - Display name for the job (stored in .metadata.json)
   * @param {string} options.email - User email (stored in .metadata.json)
   * @param {string} options.chain1 - First chain ID
   * @param {string} options.chain2 - Second chain ID
   * @param {boolean} options.useReduce - Whether to use reduce preprocessing
   * @param {number} options.interfaceCutoff - Interface cutoff distance
   * @param {number} options.waterCutoff - Water cutoff distance
   * @param {number} [options.startFrame] - Start frame (1-indexed, optional)
   * @param {number} [options.endFrame] - End frame (1-indexed, optional)
   * @param {Function} onProgress - Progress callback
   */
  async uploadFileWithOptions(file, options, onProgress) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('job_name', options.jobName ?? '')
    formData.append('email', options.email ?? '')
    formData.append('chain1', options.chain1)
    formData.append('chain2', options.chain2)
    formData.append('reduce', options.useReduce ? 'true' : 'false')
    formData.append('interface_cutoff', options.interfaceCutoff)
    formData.append('water_cutoff', options.waterCutoff)

    // Add frame interval if specified
    if (options.startFrame !== undefined && options.endFrame !== undefined) {
      formData.append('start_frame', options.startFrame)
      formData.append('end_frame', options.endFrame)
    }

    // Add frame step if specified
    if (options.frameStep !== undefined) {
      formData.append('frame_step', options.frameStep)
    }

    const response = await api.post('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      },
      // Large MD trajectories take far longer than the 30s default to transfer;
      // disable the timeout so the upload isn't aborted mid-flight.
      timeout: 0,
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percentCompleted)
        }
      }
    })
    return response.data
  }
}

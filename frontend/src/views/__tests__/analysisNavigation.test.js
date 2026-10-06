import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import AnalysisView from '../AnalysisView.vue'
import ExamplesPage from '../ExamplesPage.vue'
import JobsPage from '../JobsPage.vue'
import { addSubmittedJobId } from '../../utils/cocomapsmdJobIds'
import api from '../../services/api'
import { useSystemsStore } from '../../stores/systemsStore'

vi.mock('../../components/analysis/ChartContainer.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../../components/analysis/ConservationAnalysis.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../../components/analysis/UploadModal.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../../services/api', () => ({ default: {
  getSystems: vi.fn(async () => [
    { id: '7QDE', jobId: 'server-first', isExample: true },
    { id: '6lxt-solv-prod1', jobId: 'server-second', isExample: true },
    { id: '6lxt_d936y-prod1_mut', jobId: 'server-third', isExample: true }
  ]),
  lookupJobs: vi.fn(async () => [
    { job_id: 'upload-second', analysis_job_id: 'server-second', status: 'completed', job_name: 'Second job' }
  ]),
  getAnalysis: vi.fn(async jobId => ({ id: jobId, jobId, name: jobId, frames: 10 })),
  getInteractions: vi.fn(async () => []),
  getAreaData: vi.fn(async () => []),
  getTrends: vi.fn(async () => []),
  getInterfacePatches: vi.fn(async () => ({}))
} }))

let wrapper
afterEach(() => { wrapper?.unmount(); localStorage.clear() })

async function setup(path) {
  const pinia = createPinia()
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/', component: { template: '<div />' } },
    { path: '/jobs', component: JobsPage },
    { path: '/examples', component: ExamplesPage },
    { path: '/analysis/:jobId', name: 'Analysis', component: AnalysisView }
  ] })
  await router.push(path)
  wrapper = mount(RouterView, { global: { plugins: [pinia, router], stubs: {
    ChartSelector: true, ControlsPanel: true, StatsPanel: true
  } } })
  await flushPromises()
  return { router, store: useSystemsStore(pinia) }
}

describe('analysis navigation', () => {
  it('opens the second example after returning from the first', async () => {
    const { router, store } = await setup('/examples')
    await wrapper.findAll('a.view-btn')[0].trigger('click')
    await flushPromises()
    expect(store.currentSystem.jobId).toBe('server-first')
    await router.push('/examples')
    await flushPromises()
    await wrapper.findAll('a.view-btn')[1].trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.params.jobId).toBe('server-second')
    expect(store.currentSystem.jobId).toBe('server-second')
  })

  it('loads the new job when the analysis route is reused', async () => {
    const { router, store } = await setup('/analysis/first')
    await router.push('/analysis/second')
    await flushPromises()
    expect(store.currentSystem.jobId).toBe('second')
  })
  it('keeps a failed job URL and shows an error instead of the previous result', async () => {
    const { router, store } = await setup('/analysis/first')
    vi.spyOn(console, 'error').mockImplementation(() => {})
    api.getAnalysis.mockRejectedValueOnce(new Error('Analysis not found'))
    await router.push('/analysis/missing')
    await flushPromises()
    expect(router.currentRoute.value.params.jobId).toBe('missing')
    expect(wrapper.find('[role="alert"]').text()).toBe('Analysis not found')
    expect(wrapper.find('h1').exists()).toBe(false)
    vi.restoreAllMocks()
  })

  it('does not reload the job when only chart settings change', async () => {
    const { router } = await setup('/analysis/first')
    api.getAnalysis.mockClear()
    await router.push('/analysis/first?chart=area')
    await flushPromises()
    expect(api.getAnalysis).not.toHaveBeenCalled()
    expect(router.currentRoute.value.params.jobId).toBe('first')
  })

  it('does not link to another system when an example is missing', async () => {
    api.getSystems.mockResolvedValueOnce([
      { id: '7QDE', jobId: 'server-first', isExample: true }
    ])
    await setup('/examples')
    expect(wrapper.findAll('a.view-btn')).toHaveLength(1)
    expect(wrapper.find('[role="status"]').text()).toContain('not available')
  })

  it('shows a recoverable error when example discovery fails', async () => {
    api.getSystems.mockRejectedValueOnce(new Error('Offline'))
    await setup('/examples')
    expect(wrapper.findAll('a.view-btn')).toHaveLength(0)
    expect(wrapper.text()).toContain('Could not load example links')
  })

  it('opens a completed job after viewing a different analysis', async () => {
    addSubmittedJobId('upload-second')
    const { router, store } = await setup('/analysis/server-first')
    await router.push('/jobs')
    await flushPromises()
    api.getAnalysis.mockClear()
    await wrapper.find('tr.job-row').trigger('click')
    await flushPromises()
    expect(router.currentRoute.value.params.jobId).toBe('server-second')
    expect(store.currentSystem.jobId).toBe('server-second')
    expect(api.getAnalysis).toHaveBeenCalledTimes(1)
  })

})

import { describe, expect, it, vi } from 'vitest'

vi.mock('../../views/LandingPage.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../../views/AnalysisView.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../../views/AboutPage.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../../views/HelpPage.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../../views/ReferencesPage.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../../views/ExamplesPage.vue', () => ({ default: { template: '<div />' } }))
vi.mock('../../views/JobsPage.vue', () => ({ default: { template: '<div />' } }))

const { default: router, formatDocumentTitle } = await import('../index.js')

describe('router document titles', () => {
  it('formats document titles with the app name', () => {
    expect(formatDocumentTitle('Jobs')).toBe('Jobs - COCOMAPS-MD')
  })

  it.each([
    ['/', 'Home - COCOMAPS-MD'],
    ['/jobs', 'Jobs - COCOMAPS-MD'],
    ['/about', 'About - COCOMAPS-MD'],
    ['/help', 'Help - COCOMAPS-MD'],
    ['/examples', 'Examples - COCOMAPS-MD'],
    ['/references', 'References - COCOMAPS-MD'],
    ['/analysis/example-job', 'Analysis - COCOMAPS-MD']
  ])('sets %s to %s', async (path, expectedTitle) => {
    await router.push(path)
    await router.isReady()

    expect(document.title).toBe(expectedTitle)
  })
})

import { createRouter, createWebHistory } from 'vue-router'
import LandingPage from '../views/LandingPage.vue'
import AnalysisView from '../views/AnalysisView.vue'
import AboutPage from '../views/AboutPage.vue'
import HelpPage from '../views/HelpPage.vue'
import ReferencesPage from '../views/ReferencesPage.vue'
import ExamplesPage from '../views/ExamplesPage.vue'
import JobsPage from '../views/JobsPage.vue'

export const APP_TITLE = 'COCOMAPS-MD'

export const formatDocumentTitle = (pageTitle) => `${pageTitle} - ${APP_TITLE}`

const routes = [
  {
    path: '/',
    name: 'Landing',
    component: LandingPage,
    meta: { pageTitle: 'Home' }
  },
  {
    path: '/analysis/:jobId',
    name: 'Analysis',
    component: AnalysisView,
    meta: { pageTitle: 'Analysis' }
  },
  {
    path: '/jobs',
    name: 'Jobs',
    component: JobsPage,
    meta: { pageTitle: 'Jobs' }
  },
  {
    path: '/about',
    name: 'About',
    component: AboutPage,
    meta: { pageTitle: 'About' }
  },
  {
    path: '/help',
    name: 'Help',
    component: HelpPage,
    meta: { pageTitle: 'Help' }
  },
  {
    path: '/references',
    name: 'References',
    component: ReferencesPage,
    meta: { pageTitle: 'References' }
  },
  {
    path: '/examples',
    name: 'Examples',
    component: ExamplesPage,
    meta: { pageTitle: 'Examples' }
  }
]

const router = createRouter({
  history: createWebHistory('/BioTools/COCOMAPS-MD'),
  routes
})

router.afterEach((to) => {
  const pageTitle = to.meta.pageTitle || 'Home'
  document.title = formatDocumentTitle(pageTitle)
})

export default router

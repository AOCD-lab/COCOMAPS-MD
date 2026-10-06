<template>
  <div class="examples-page">
    <!-- Header -->
    <header class="page-header">
      <h1>Examples</h1>
      <p class="subtitle">Pre-Analyzed Systems</p>
    </header>

    <!-- Main Content -->
    <main class="content">
      <div class="container">
        <!-- Example Cards -->
        <div class="examples-grid">
          <div v-for="example in examples" :key="example.id" class="example-card">
            <div class="card-header">
              <span class="card-badge">Example</span>
              <h3>{{ example.title }}</h3>
              <p class="card-description">{{ example.description }}</p>
            </div>

            <div class="card-stats">
              <div class="stat">
                <span class="stat-value">{{ example.frames }}</span>
                <span class="stat-label">Frames</span>
              </div>
              <div class="stat">
                <span class="stat-value">{{ example.chain1 }} ↔ {{ example.chain2 }}</span>
                <span class="stat-label">Chains</span>
              </div>
              <div class="stat">
                <span class="stat-value">{{ example.pdbId }}</span>
                <span class="stat-label">Source</span>
              </div>
            </div>

            <div class="card-details">
              <p>{{ example.details }}</p>
            </div>

            <router-link v-if="exampleJobIds[example.id]" :to="'/analysis/' + exampleJobIds[example.id]" class="view-btn">
              View Analysis
              <svg viewBox="0 0 16 16" fill="currentColor" class="arrow-icon">
                <path fill-rule="evenodd" d="M1 8a.5.5 0 0 1 .5-.5h11.793l-3.147-3.146a.5.5 0 0 1 .708-.708l4 4a.5.5 0 0 1 0 .708l-4 4a.5.5 0 0 1-.708-.708L13.293 8.5H1.5A.5.5 0 0 1 1 8z"/>
              </svg>
            </router-link>
            <p v-else role="status">{{ loadingExamples ? 'Loading analysis link...' : examplesError || 'This example is not available on this server.' }}</p>
          </div>
        </div>

        <!-- Getting Started -->
        <section class="section cta-section">
          <h2>Ready to Analyze Your Own System?</h2>
          <p>
            Upload a multi-model PDB file from your molecular dynamics trajectory and
            COCOMAPS-MD will analyze every frame automatically.
          </p>
          <router-link to="/" class="cta-btn">Upload a PDB File</router-link>
        </section>
      </div>
    </main>

    <!-- Footer -->
    <AppFooter />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import AppFooter from '../components/layout/AppFooter.vue'

const exampleJobIds = ref({})
const loadingExamples = ref(true)
const examplesError = ref('')

// Job IDs can change when bundled examples are regenerated or deployed.
onMounted(async () => {
  try {
    const systems = await api.getSystems()
    exampleJobIds.value = Object.fromEntries(
      systems.filter(system => system.isExample && system.jobId)
        .map(system => [system.id, system.jobId])
    )
  } catch {
    examplesError.value = 'Could not load example links. Please refresh to try again.'
  } finally {
    loadingExamples.value = false
  }
})

const examples = [
  {
    id: '7QDE',
    title: 'Npl3 RRM12 \u2013 RNA Complex (NMR)',
    pdbId: '7QDE',
    frames: 10,
    chain1: 'A',
    chain2: 'B',
    description:
      'NMR solution structure of yeast Npl3 RNA Recognition Motifs (RRM1 & RRM2) bound to AUCCAGUGGAA RNA, revealing how Npl3 recognizes U2 snRNA in a chaperone role during pre-mRNA splicing.',
    details:
      'This 10-conformer NMR ensemble captures the structural variability of the Npl3\u2013RNA interface. Chain A is the 11-nucleotide RNA and chain B is the Npl3 protein, showcasing base-specific recognition and cooperative binding mediated by the inter-RRM linker.'
  },
  {
    id: '6lxt-solv-prod1',
    title: '6LXT Wildtype A–C Trajectory',
    pdbId: '6LXT',
    frames: 101,
    chain1: 'A',
    chain2: 'C',
    description:
      'Full 101-frame molecular dynamics trajectory of the solvated 6LXT wildtype system, analyzed across the chain A–C interface.',
    details:
      'This example provides the wildtype reference for reviewing interaction conservation, interface areas, and conserved interface patches across the complete production trajectory.'
  },
  {
    id: '6lxt_d936y-prod1_mut',
    title: '6LXT D936Y Mutant A–C Trajectory',
    pdbId: '6LXT D936Y',
    frames: 101,
    chain1: 'A',
    chain2: 'C',
    description:
      'Full 101-frame molecular dynamics trajectory of the 6LXT D936Y mutant, analyzed across the chain A–C interface.',
    details:
      'Paired with the wildtype example, this trajectory supports direct review of mutation-associated changes in conserved contacts, interaction trends, interface areas, and interface patches.'
  }
]
</script>

<style scoped>
.examples-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
}

/* Header */
.page-header {
  padding: 60px 40px 40px;
  text-align: center;
  background: linear-gradient(180deg, #ffffff 0%, #f5f5f7 100%);
}

.page-header h1 {
  font-size: 48px;
  font-weight: 700;
  color: #1d1d1f;
  margin: 0;
  letter-spacing: -0.02em;
}

.subtitle {
  font-size: 21px;
  color: #6e6e73;
  margin: 12px 0 0;
}

/* Content */
.content {
  flex: 1;
  padding: 0 40px 80px;
}

.container {
  max-width: 1000px;
  margin: 0 auto;
}

/* Sections */
.section {
  background: #ffffff;
  border-radius: 20px;
  padding: 40px;
  margin-bottom: 32px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.section h2 {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 20px;
}

.section p {
  font-size: 17px;
  line-height: 1.6;
  color: #424245;
  margin: 0 0 16px;
}

.section p:last-child {
  margin-bottom: 0;
}

/* Examples Grid */
.examples-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 24px;
  margin-bottom: 32px;
}

/* Example Card */
.example-card {
  background: #ffffff;
  border-radius: 20px;
  padding: 40px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s ease;
}

.example-card:hover {
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
}

.card-header {
  position: relative;
  margin-bottom: 24px;
}

.card-badge {
  display: inline-block;
  padding: 4px 12px;
  background: #1d1d1f;
  color: #ffffff;
  font-size: 12px;
  font-weight: 600;
  border-radius: 980px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  margin-bottom: 16px;
}

.card-header h3 {
  font-size: 24px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 10px;
}

.card-description {
  font-size: 17px;
  line-height: 1.6;
  color: #424245;
  margin: 0;
}

/* Stats Row */
.card-stats {
  display: flex;
  gap: 16px;
  padding: 20px 24px;
  background: #f5f5f7;
  border-radius: 16px;
  margin-bottom: 20px;
}

.stat {
  flex: 1;
  text-align: center;
}

.stat-value {
  display: block;
  font-size: 18px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 4px;
}

.stat-label {
  display: block;
  font-size: 13px;
  color: #6e6e73;
}

/* Card Details */
.card-details p {
  font-size: 15px;
  line-height: 1.6;
  color: #6e6e73;
  margin: 0 0 24px;
}

/* View Button */
.view-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  background: #0066cc;
  color: #ffffff;
  font-size: 15px;
  font-weight: 500;
  border-radius: 980px;
  text-decoration: none;
  font-family: inherit;
  transition: background 0.15s ease;
}

.view-btn:hover {
  background: #0055aa;
}

.arrow-icon {
  width: 14px;
  height: 14px;
}

/* CTA Section */
.cta-section {
  text-align: center;
}

.cta-btn {
  display: inline-block;
  margin-top: 8px;
  padding: 12px 28px;
  background: #1d1d1f;
  color: #ffffff;
  font-size: 15px;
  font-weight: 500;
  border-radius: 980px;
  text-decoration: none;
  font-family: inherit;
  transition: background 0.15s ease;
}

.cta-btn:hover {
  background: #424245;
}

/* Responsive */
@media (max-width: 768px) {
  .page-header {
    padding: 40px 24px 32px;
  }

  .page-header h1 {
    font-size: 36px;
  }

  .content {
    padding: 0 24px 60px;
  }

  .section {
    padding: 28px;
  }

  .example-card {
    padding: 28px;
  }

  .card-header h3 {
    font-size: 20px;
  }

  .card-stats {
    flex-direction: column;
    gap: 12px;
  }

  .stat {
    display: flex;
    justify-content: space-between;
    text-align: left;
  }
}
</style>

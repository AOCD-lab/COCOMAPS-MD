<template>
  <div class="help-page">
    <header class="page-header">
      <h1>Help</h1>
      <p class="subtitle">Guides and Documentation</p>
    </header>

    <!-- Tab Bar -->
    <nav class="docs-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :class="['docs-tab', { active: activeTab === tab.id }]"
        @click="switchTab(tab.id)"
      >
        <span class="tab-icon" v-html="tab.icon"></span>
        {{ tab.label }}
      </button>
    </nav>

    <!-- Docs Layout -->
    <div class="docs-layout">
      <!-- Sidebar -->
      <aside :class="['docs-sidebar', { open: sidebarOpen }]">
        <div
          v-for="tab in tabs"
          :key="'sidebar-' + tab.id"
          :class="['docs-sidebar-panel', { active: activeTab === tab.id }]"
        >
          <h4 class="sidebar-heading">{{ tab.label }}</h4>
          <a
            v-for="section in tab.sections"
            :key="section.id"
            :href="'#' + section.id"
            :class="['sidebar-link', { active: activeSection === section.id }]"
            @click.prevent="scrollToSection(section.id)"
          >
            <span v-if="section.color" class="sidebar-color-dot" :style="{ background: section.color }"></span>
            {{ section.title }}
          </a>
        </div>
      </aside>

      <!-- Mobile sidebar backdrop -->
      <div
        v-if="sidebarOpen"
        class="sidebar-backdrop"
        @click="sidebarOpen = false"
      ></div>

      <!-- Mobile sidebar toggle -->
      <button
        class="sidebar-toggle"
        @click="sidebarOpen = !sidebarOpen"
        :aria-label="sidebarOpen ? 'Close sidebar' : 'Open sidebar'"
      >
        <svg v-if="!sidebarOpen" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
        <svg v-else viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>

      <!-- Content Panels -->
      <main class="docs-content">
        <div
          v-for="tab in tabs"
          :key="'panel-' + tab.id"
          :class="['docs-panel', { active: activeTab === tab.id }]"
        >
          <div
            v-for="section in tab.sections"
            :key="section.id"
            :id="section.id"
            class="docs-section"
          >
            <div class="docs-section-card">
              <!-- Title with optional color indicator -->
              <div class="section-header">
                <span v-if="section.color" class="section-color-bar" :style="{ background: section.color }"></span>
                <h2>{{ section.title }}</h2>
              </div>

              <!-- Description: string or array of strings -->
              <template v-if="Array.isArray(section.description)">
                <p v-for="(desc, di) in section.description" :key="'d'+di" class="section-description">{{ desc }}</p>
              </template>
              <p v-else-if="section.description" class="section-description">{{ section.description }}</p>

              <!-- Section-level image -->
              <div v-if="section.image" :class="['section-image', section.imageClass]">
                <img :src="section.image" :alt="section.imageAlt || section.title" />
              </div>

              <!-- Subsections -->
              <div
                v-for="(sub, si) in section.subsections"
                :key="si"
                :class="['docs-subsection', { 'docs-card-media': sub.image }]"
              >
                <div class="docs-card-text">
                  <h3 v-if="sub.heading">{{ sub.heading }}</h3>
                  <p v-for="(para, pi) in (sub.paragraphs || [])" :key="pi">{{ para }}</p>
                  <div v-if="sub.links && sub.links.length" class="subsection-links">
                    <a v-for="(link, li) in sub.links" :key="'link'+li" :href="link.url" target="_blank" rel="noopener" class="subsection-link">{{ link.label }}</a>
                  </div>
                  <div v-if="sub.codeBlocks && sub.codeBlocks.length" class="code-blocks">
                    <div v-for="(cb, cbi) in sub.codeBlocks" :key="'cb'+cbi" class="code-block">
                      <p v-if="cb.label" class="code-label">{{ cb.label }}</p>
                      <div class="code-container">
                        <pre><code>{{ cb.code }}</code></pre>
                        <button class="copy-btn" @click="copyCode(cb.code, $event)" title="Copy">
                          <svg class="icon-copy" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>
                          <svg class="icon-check" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                        </button>
                      </div>
                    </div>
                  </div>
                  <ol v-if="sub.criteria && sub.criteria.length" class="criteria-list">
                    <li v-for="(c, ci) in sub.criteria" :key="ci">{{ c }}</li>
                  </ol>
                  <ul v-if="sub.items && sub.items.length">
                    <li v-for="(item, ii) in sub.items" :key="ii">{{ item }}</li>
                  </ul>
                  <ul v-if="sub.statusList && sub.statusList.length" class="status-list">
                    <li v-for="(st, sti) in sub.statusList" :key="sti" class="status-list-item">
                      <span class="status-indicator" :style="{ background: st.color }"></span>
                      <span class="status-text"><strong>{{ st.label }}</strong>: {{ st.desc }}</span>
                    </li>
                  </ul>
                </div>
                <div v-if="sub.image" class="docs-card-image">
                  <img :src="sub.image" :alt="sub.imageAlt || 'Diagram'" />
                </div>
              </div>

              <!-- References footer -->
              <div v-if="section.references && section.references.length" class="section-references">
                <span class="ref-label">References:</span>
                <a
                  v-for="(ref, ri) in section.references"
                  :key="ri"
                  :href="ref.startsWith('http') ? ref : 'https://doi.org/' + ref"
                  target="_blank"
                  rel="noopener"
                  class="ref-link"
                >
                  {{ ref.startsWith('http') ? ref : 'DOI: ' + ref }}
                </a>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>

    <AppFooter />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppFooter from '../components/layout/AppFooter.vue'

const route = useRoute()
const router = useRouter()

const activeTab = ref('usage')
const activeSection = ref('')
const sidebarOpen = ref(false)

/** Match .docs-section scroll-margin-top — section is "active" once its top passes this line below the sticky header/tabs */
const SCROLL_ACTIVE_OFFSET = 140

let scrollRaf = null

function updateActiveFromScroll() {
  const currentTab = tabs.find(t => t.id === activeTab.value)
  if (!currentTab?.sections?.length) return

  const ids = currentTab.sections.map(s => s.id)
  let activeId = ''

  for (const id of ids) {
    const el = document.getElementById(id)
    if (!el) continue
    if (el.getBoundingClientRect().top <= SCROLL_ACTIVE_OFFSET) {
      activeId = id
    }
  }

  if (!activeId) {
    activeId = ids[0] || ''
  }

  const doc = document.documentElement
  const scrollBottom = window.scrollY + window.innerHeight
  if (ids.length && scrollBottom >= doc.scrollHeight - 8) {
    activeId = ids[ids.length - 1]
  }

  if (activeSection.value !== activeId) {
    activeSection.value = activeId
  }
}

function onScroll() {
  if (scrollRaf != null) return
  scrollRaf = requestAnimationFrame(() => {
    scrollRaf = null
    updateActiveFromScroll()
  })
}

function onResize() {
  updateActiveFromScroll()
}

const IMG = import.meta.env.BASE_URL + 'images/help/'

const usageSections = [
  {
    id: 'usage-intro',
    title: 'Introduction',
    description: [
      'COCOMAPS-MD is a web application for analyzing non-covalent interactions at protein–protein interfaces across molecular dynamics trajectories. You upload a multi-model PDB (trajectory), choose two chains, and the server computes interface contacts frame by frame. Results are explored through contact maps, trend charts, conservation-style summaries, and structure viewing.',
      'The workflow is: upload a PDB on the home page → select two chains → optionally adjust advanced settings → start the analysis. When processing finishes, you are taken to the analysis view for that job. You can also open past jobs from the Jobs page.'
    ],
    subsections: [
      {
        heading: 'Key features',
        items: [
          'Interface-focused analysis between two protein chains over many frames.',
          'Automatic detection of chains and frame count from your PDB; long trajectories are sampled so a manageable number of frames are analyzed.',
          'Detailed categorization of interaction types (see the Interactions tab in this Help section for definitions and geometric criteria).',
          'Job list with status, search, and quick access to completed analyses.'
        ]
      }
    ]
  },
  {
    id: 'usage-upload',
    title: '1. Upload a PDB file',
    description: [
      'From the home page, provide your structure by uploading a file. The server expects a standard PDB file with the .pdb extension.',
      'Drag and drop the file onto the upload area, or click the area to open the file picker. Only one file is processed at a time. If your structure is not in PDB format, convert it to PDB before uploading.'
    ],
    subsections: [
      {
        heading: 'What happens after you choose a file',
        paragraphs: [
          'The browser reads the file to list chain identifiers found in ATOM and HETATM records, and counts trajectory frames from MODEL records. If there are no MODEL records, the structure is treated as a single frame.',
          'At least two distinct chains are required for interface analysis. If fewer than two chains are found, you will be prompted to choose a different file.'
        ]
      }
    ]
  },
  {
    id: 'usage-chains',
    title: '2. Select two chains',
    description: [
      'After a valid PDB is loaded, use Select Chains for Analysis to choose Chain 1 and Chain 2. These define the two protein chains whose mutual interface will be analyzed. The two selections must be different chains.',
      'The page shows the file name, approximate size, number of chains, and number of frames detected.',
      'If there are more than 50 frames, the home page shows a short note about how many frames will be analyzed and the step size used. Full details on step size, defaults, and custom frame ranges are under Advanced Settings → Frame sampling.'
    ],
    subsections: []
  },
  {
    id: 'usage-advanced',
    title: '3. Advanced Settings',
    description: [
      'Open the Advanced Settings section to optionally customize the job. Defaults are appropriate for most runs.',
      'Geometric thresholds for each interaction class (hydrogen bonds, π-stacking, and so on) are fixed for a given server configurationm, they are documented under Help → Interactions.'
    ],
    subsections: [
      {
        heading: 'Job name',
        paragraphs: [
          'Job name identifies the run in the Jobs list and in analysis views. By default it is the same as your PDB file name (without the .pdb extension), unless you type a different value.'
        ]
      },
      {
        heading: 'Email',
        paragraphs: [
          'Optionally enter your email address. When the job is completed, you will receive an email containing the job ID and a link to the results.'
        ]
      },
      {
        heading: 'Use Reduce',
        paragraphs: [
          'When enabled, structures can be preprocessed to add hydrogens using Reduce before analysis. This can improve consistency for structures that lack hydrogens at the cost of longer runtime.',
          'Reference: Word, J. M., Lovell, S. C., Richardson, J. S., & Richardson, D. C. (1999). Asparagine and glutamine: Using hydrogen atom contacts in the choice of side-chain amide orientation. J. Mol. Biol. 285, 1735\u20131747.'
        ]
      },
      {
        heading: 'Time unit',
        paragraphs: [
          'An optional label (for example ns or ps) is used for time-like axes in charts when provided. If left empty, axes are labeled in frames.'
        ]
      },
      {
        heading: 'Frame sampling',
        paragraphs: [
          'Frame sampling controls are available for every uploaded trajectory, regardless of its length. Step size controls subsampling: only a subset of frames are sent to the analysis, taken at regular intervals from the first frame to the last.',
          'When the trajectory contains more than 50 frames, the interface does not analyze every frame by default. Shorter trajectories default to step size 1, so every frame is analyzed unless you choose a larger step or a custom interval.',
          'What step size means: a step size of N keeps every Nth frame in order. For example, step 2 keeps frames 1, 3, 5, … (every other frame); step 10 keeps frames 1, 11, 21, … Larger steps mean fewer, more widely spaced samples. Step 1 means every frame—which is appropriate when you have at most 50 frames overall, or when you use a short custom range in this section.',
          'Default: the app sets the step size automatically so that spanning the full trajectory yields roughly on the order of 50 analyzed frames (the step is derived from the total frame count). Before you open Advanced Settings, a short note on the home page already states how many frames will be analyzed and which step size is used.',
          'The Step size field in Advanced Settings matches that default and can be changed: increase the step to lighten the job or decrease it for denser sampling. Use custom interval turns off regular stepping across the entire trajectory and lets you pick a specific start and end frame (within the limits shown). The panel displays how many frames will be analyzed for your current choices.'
        ]
      }
    ]
  },
  {
    id: 'usage-run',
    title: '4. Run the analysis',
    description: [
      'When Chain 1 and Chain 2 are set, Start Analysis becomes available. Click it to upload the file and queue the job on the server.',
      'Progress appears on the same page with a progress indicator. The page URL may include a job query parameter so that refreshing the browser can resume tracking that run.',
      'When the job completes successfully, you are redirected to the analysis view for that result. If the analysis URL cannot be resolved, you may be sent to the Jobs page instead. If the job fails, an error message is shown on the home page.',
      'To use a different structure, use Change on the file card to clear the upload and start over.'
    ],
    subsections: []
  },
  {
    id: 'usage-jobs',
    title: 'Jobs page',
    description: [
      'Open Jobs from the navigation bar to see all your jobs in a searchable, sortable table: status, name, creation date, and frame count.',
      'Use Submit a new job to return to the home page and upload another PDB.'
    ],
    subsections: [
      {
        heading: 'Job status',
        paragraphs: [
          'Each job row shows a colored icon reflecting its current state:'
        ],
        statusList: [
          { label: 'Completed', color: '#34c759', desc: 'The analysis finished successfully. Click the row to open the results in the analysis view.' },
          { label: 'Queued', color: '#ff9500', desc: 'The upload is safely stored and waiting for one of the two analysis workers.' },
          { label: 'Processing', color: '#ff9500', desc: 'The job is still running. Click the row to return to the home page and track its progress in real time.' },
          { label: 'Failed', color: '#ff3b30', desc: 'The analysis encountered an error. The row is not clickable; you can submit a new job instead.' }
        ]
      }
    ]
  }
]

const interactionSections = [
  {
    id: 'int-overview',
    title: 'Overview',
    description: 'CoCoMaps-MD identifies and classifies 18 types of atomic interactions at molecular interfaces. These include 16 specific interaction types defined by precise geometric criteria, plus proximal contacts and clashes. Each section below describes the interaction and its detection criteria.',
    subsections: []
  },
  {
    id: 'int-table',
    title: 'Table of Atomic Interactions',
    description: [
      'Based on a cut-off distance between any pair of heavy (non-hydrogen) atoms from the chains whose interaction interface is under analysis, an overall analysis of residues contacting each other at the interface is derived. The default cut-off value is 5 \u00C5.',
      'Each pair of contacting residues at the interface is tagged with its associated specific atomic interactions, as detailed below. All contacts occurring within the cut-off distance and not falling in any class of the considered atomic interactions, are categorized as \u201CProximal contacts\u201D (see below).',
      'In the interactions table, each interaction type can be toggled on or off. By default, Proximal contacts is turned off: the table initially includes the other interaction classes only, so you can focus on specific interaction types first. Turn Proximal contacts on when you also want to see contacts that fall only in that category.'
    ],
    image: IMG + 'interactions-table-proximal.png',
    imageAlt: 'Interactions table with Proximal contacts toggle off by default',
    subsections: [
      {
        paragraphs: [
          'In the following, all the types of atomic interactions identified and visualized by the web server are listed.'
        ]
      }
    ]
  },
  {
    id: 'int-hbonds',
    title: 'H-bonds',
    color: '#2196F3',
    description: 'Hydrogen bonds form due to an electrostatic attraction between a hydrogen atom covalently bonded to a highly electronegative atom, such as O or N (H-bond donor, D) and another non-covalently bonded electronegative atom (H-bond acceptor, A). Detected using HBPLUS v3.2.',
    image: IMG + 'h-bond.png',
    imageAlt: 'H-bond interaction diagram',
    references: ['10.1006/jmbi.1994.1334'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: ['The following geometric criteria are applied:'],
        criteria: [
          'The distance between the donor (D) and the acceptor (A) atoms must be within 4.0 Å.',
          'The θ angle formed by the donor (D), hydrogen (H), and acceptor (A) atoms must exceed 90°.'
        ],
      }
    ]
  },
  {
    id: 'int-salt-bridges',
    title: 'Salt-bridges',
    color: '#E91E63',
    description: [
      'Salt-bridges are strong electrostatic attractions between positively and negatively charged atoms. They form between NH₃⁺ groups and COO⁻ groups.',
      'For protein-protein interactions, they are identified between Lys/Arg (positive) and Asp/Glu (negative) side chains. For protein-nucleic acid complexes, the negative charges come from nucleotide phosphate groups (OP1/OP2). Detected using HBPLUS v3.2.'
    ],
    image: IMG + 'salt-bridge.png',
    imageAlt: 'Salt-bridge interaction diagram',
    references: ['10.1006/jmbi.1994.1334'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance between the positive and negative charged atoms must be within 4.5 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-water-mediated',
    title: 'Water-mediated contacts',
    color: '#00BCD4',
    description: 'Water molecules act as bridges between two electronegative atoms by H-bonding to them, contributing to overall complex stability. Detected using HBPLUS v3.2.',
    image: IMG + 'water-mediated.png',
    imageAlt: 'Water-mediated contact diagram',
    references: ['10.1006/jmbi.1994.1334', '10.1002/prot.24439'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance between the water oxygen and H-bonded electronegative atoms must be within 4.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-ch-on',
    title: 'CH-O/N bonds',
    color: '#8BC34A',
    description: 'Weak electrostatic attraction between a hydrogen atom covalently bonded to C (donor) and an electronegative atom X (O or N, acceptor). Weaker than proper H-bonds but play important roles in supramolecular chemistry and molecular recognition.',
    image: IMG + 'ch-on.png',
    imageAlt: 'CH-O/N bond diagram',
    references: ['10.1021/ar950135n', 'https://journals.iucr.org/services/cif/hbonds.html'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance d(C–X) must be within 4.0 Å.',
          'The angle θ(C-H-X) must exceed 110°.'
        ],
      }
    ]
  },
  {
    id: 'int-ss-bonds',
    title: 'Disulfide bridges (S-S bonds)',
    color: '#FFC107',
    description: 'The only covalent bonds considered in this analysis. They form intra- or inter-molecularly between sulfur atoms at the γ position (SG) of Cysteine side chains.',
    image: IMG + 'ss-bonds.png',
    imageAlt: 'Disulfide bridge diagram',
    references: ['10.1016/0022-2836(81)90515-5'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The SG–SG distance must be within 3.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-halogen',
    title: 'Halogen bonds',
    color: '#9C27B0',
    description: 'Non-covalent interactions from electrostatic attraction between a halogen atom Z (F, Cl, Br, I) covalently bonded to C, and an electronegative atom X (O, N, S) covalently bonded to a C/P/S (Y) atom.',
    image: IMG + 'halogen-bonds.png',
    imageAlt: 'Halogen bond diagram',
    references: ['10.1073/pnas.0407607101'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The X–Z distance must be within the sum of their van der Waals radii.',
          'The angle θ₁(C-Z-X) must exceed 165°.',
          'The angle θ₂(Z-X-Y) must exceed 120°.'
        ],
      }
    ]
  },
  {
    id: 'int-metal',
    title: 'Metal-mediated contacts',
    color: '#795548',
    description: 'Metal cations (M) act as bridges between two molecules by coordinating to electronegative atoms X (O, N, S). Van der Waals radii are not used here due to uncertainties about the charge and oxidation state of metal ions in the structures.',
    image: IMG + 'metal-mediated.png',
    imageAlt: 'Metal-mediated contact diagram',
    references: ['10.1002/pro.727'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The M–X distance must be within 3.2 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-pi-framework',
    title: 'Geometrical Framework for π Interactions',
    description: [
      '\u03C0 (Pi) interactions may involve the \u03C0 cloud of the single or double aromatic ring of the nucleobases: G, U, A, T/U in nucleic acids, and aromatic rings of the amino acids: His, Phe, Trp, and Tyr in proteins. To detect such interactions, we set up a geometrical frame on the \u03C0 rings, both single and double, as detailed below.',
      'For each aromatic ring, we assign its geometrical center (centroid), then define a ring plane (shown as a gray grid in the figure below), passing through the above centroid and the two ring atoms listed first in the corresponding .pdb/.cif file. Then, to define whether an interaction exists between a given atom/ion and the aromatic ring, we orthogonally project the atom into the ring plane and measure this orthogonal distance. The interaction is assigned if: i) the orthogonal distance is within a given threshold, and ii) the projection falls within the perimeter of the ring (to this aim we use the ConvexHull function available from the SciPy library in Python).'
    ],
    references: ['https://docs.scipy.org/doc/scipy/reference/generated/scipy.spatial.ConvexHull.html'],
    subsections: []
  },
  {
    id: 'int-cation-pi',
    title: 'Cation-π interactions',
    color: '#FF5722',
    description: 'Attraction between a positive charge (cation) and the π cloud of an aromatic ring. The positive charges on the side chains of Arg (NE, CZ, NH1, NH2) and Lys (CE, NZ) are considered as cations.',
    image: IMG + 'cation-pi.png',
    imageAlt: 'Cation-π interaction diagram',
    references: ['10.1093/nar/gkh733'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The vertical distance from the cation to the ring plane must be within 5.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-anion-pi',
    title: 'Anion-π interactions',
    color: '#F44336',
    description: 'Attraction between a negative charge (anion) and the π cloud of an aromatic ring. The negative charges on the side chains of Glu (OE1, OE2) and Asp (OD1, OD2), and on DNA/RNA phosphate groups (OP1/OP2) are considered.',
    image: IMG + 'anion-pi.png',
    imageAlt: 'Anion-π interaction diagram',
    references: ['10.1093/nar/gkx757'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The vertical distance from the anion to the ring plane must be within 5.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-amino-pi',
    title: 'Amino-π interactions',
    color: '#3F51B5',
    description: 'Attractive forces between an amino group and the π-electron cloud of an aromatic ring. Amino atoms considered: ND1 of Asn, NE2 of Gln, N2 of guanine (G), N6 of adenine (A), and N4 of cytosine (C).',
    image: IMG + 'amino-pi.png',
    imageAlt: 'Amino-π interaction diagram',
    references: ['10.1002/prot.24527'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The vertical distance from the amino atom to the ring plane must be within 5.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-lp-pi',
    title: 'lp-π interactions',
    color: '#009688',
    description: 'Attraction between an electric lone pair (on atom LP) and the π cloud of an aromatic ring. Lone-pair-presenting atoms considered are any O, S, N atoms featuring at least one electron lone pair.',
    image: IMG + 'lp-pi.png',
    imageAlt: 'lp-π interaction diagram',
    references: ['10.1093/nar/gkx757'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The vertical distance from the lone-pair-presenting atom to the ring plane must be within 5.0 Å.'
        ],
      }
    ]
  },
  {
    id: 'int-pi-pi',
    title: 'π-π stacking',
    color: '#673AB7',
    description: 'Attraction between the π clouds of aromatic rings in close proximity. Three geometric parameters (distance and two angles) characterize the intermolecular orientation of the rings.',
    image: IMG + 'pi-pi.png',
    imageAlt: 'π-π stacking diagram',
    references: ['10.1074/jbc.273.25.15458'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The centroid-to-centroid distance between the two rings must be within 5.5 Å.',
          'The center-normal angle (θ) must be within 80°.',
          'The normal-normal angle (γ) must be within 90°.'
        ],
      }
    ]
  },
  {
    id: 'int-ch-pi',
    title: 'CH-π interactions',
    color: '#4CAF50',
    description: 'Attraction between a hydrogen atom covalently bonded to C and the π cloud of an aromatic ring. Relatively weak but can significantly contribute to the stability of molecular complexes.',
    image: IMG + 'ch-pi.png',
    imageAlt: 'CH-π interaction diagram',
    references: ['10.1006/jmbi.2000.4473'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance from C to the ring centroid (πm) must be within 4.5 Å.',
          'The angle θ₁(C-πm-πn) must be within 30°.',
          'The angle θ₂ between the C-H bond and the H-πm vector must be at least 120°.'
        ],
      }
    ]
  },
  {
    id: 'int-onsh-pi',
    title: 'O/N/SH-π interactions',
    color: '#FF9800',
    description: 'Attraction between a hydrogen atom covalently bonded to O, N, or S (atom X) and the π-cloud of an aromatic ring.',
    image: IMG + 'onsh-pi.png',
    imageAlt: 'O/N/SH-π interaction diagram',
    references: ['10.1006/jmbi.2000.4301', '10.1093/nar/gkg528'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance from X to the ring origin must be within 4.5 Å.',
          'The angle θ₁(X-origin-z) must be within 30°.',
          'The angle θ₂ between the X-H bond and the H-origin vector must be at least 120°.'
        ],
      }
    ]
  },
  {
    id: 'int-apolar',
    title: 'Apolar vdW contacts',
    color: '#607D8B',
    description: 'Van der Waals interactions between two apolar atoms (C atoms bonded only to C or H). Apolar interactions between π-π stacking rings are excluded from this category.',
    image: IMG + 'apolar.png',
    imageAlt: 'Apolar vdW contact diagram',
    references: ['10.1093/nar/gkv315'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance must be within the sum of van der Waals radii + 0.5 Å tolerance (for C at 1.7 Å, this gives a cutoff of 3.9 Å).'
        ],
      }
    ]
  },
  {
    id: 'int-polar',
    title: 'Polar vdW contacts',
    color: '#9E9E9E',
    description: 'Van der Waals interactions between two atoms where at least one is not apolar. Polar interactions between π-π stacking rings are excluded from this category.',
    image: IMG + 'polar.png',
    imageAlt: 'Polar vdW contact diagram',
    references: ['10.1093/nar/gkv315'],
    subsections: [
      {
        heading: 'Detection Criteria',
        paragraphs: [],
        criteria: [
          'The distance must be within the sum of van der Waals radii + 0.5 Å tolerance.'
        ],
      }
    ]
  },
  {
    id: 'int-proximal',
    title: 'Proximal contacts',
    color: '#BDBDBD',
    description: 'All contacts within the cut-off distance (5 Å by default) that do not fall into any of the specific interaction classes above.',
    references: ['10.1016/j.jmb.2016.12.004'],
    subsections: []
  },
  {
    id: 'int-clashes',
    title: 'Clashes',
    color: '#D32F2F',
    description: 'Contacts between heavy atoms occurring at a distance below the sum of their van der Waals radii, indicating steric overlap.',
    references: ['10.1016/j.jmb.2016.12.004'],
    subsections: []
  },
  {
    id: 'int-vdw-radii',
    title: 'Van der Waals radii',
    subsections: [
      {
        items: [
          'Br \u2013 1.85 \u00C5',
          'C \u2013 1.70 \u00C5',
          'Cl \u2013 1.75 \u00C5',
          'F \u2013 1.47 \u00C5',
          'I \u2013 1.98 \u00C5',
          'N \u2013 1.55 \u00C5',
          'O \u2013 1.52 \u00C5',
          'S \u2013 1.80 \u00C5',
          'P \u2013 1.80 \u00C5'
        ]
      }
    ]
  },
  {
    id: 'int-detection-tools',
    title: 'Interaction detection',
    subsections: [
      {
        items: [
          'Reduce v4.14 \u2013 for adding hydrogen atoms to proteins and nucleic acids.',
          'HBPLUS v3.2 \u2013 for detecting hydrogen bonds and water-mediated contacts.',
          'NACCESS v2.1.1 \u2013 for solvent accessible surface area calculations.',
          'HBADD \u2013 for additional hydrogen bond analyses.'
        ]
      }
    ]
  },
  {
    id: 'int-overlap',
    title: 'Handling of overlapping classifications',
    description: 'When more than one interaction type is detected for a residue pair, we apply the following hierarchy:',
    subsections: [
      {
        items: [
          'If \u03C0\u2013\u03C0 stacking is present together with apolar van der Waals (vdW) contacts, only the \u03C0\u2013\u03C0 stacking is retained.',
          'If both a salt bridge and a hydrogen bond are identified for the same atom pair, the contact will be classified as a salt bridge.',
          'If hydrogen bonds, halogen bonds, or weak H-bonds coexist with polar vdW contacts, only the directional bonds are kept.'
        ],
        paragraphs: [
          'Clashes are defined when the observed interatomic distance is less than the sum of the van der Waals radii. If the interaction also falls into one of the standard categories (e.g., hydrogen bond, CH\u2013O/N bond, polar/apolar vdW, halogen bond, disulfide bond, salt bridge), it is reported with an asterisk alongside the respective interaction label.'
        ]
      }
    ]
  },
  {
    id: 'int-interface-area',
    title: 'Interface area and residues',
    description: [
      'Buried surface areas are calculated with NACCESS. Residues at the interface are defined as those having an ASA (Accessible Surface Area) decreased by > 1.0 \u00C5\u00B2 upon the complex formation.',
      'POLAR and NON POLAR interface percentages (%) refer to the calculated interface area (\u00C5\u00B2) for the complex and sum up to 100.',
      'In the ASA tables for chain 1 & 2, ASA values in the complex and in the isolated molecule (\u201Cfree\u201D), along with the difference between them are reported for each residue.'
    ],
    references: ['https://wolf.bms.umist.ac.uk/naccess/'],
    subsections: [
      {
        paragraphs: [
          'Reference: Hubbard, S. J. and Thornton, J. M. \u201CNACCESS\u201D Computer Program, 1993.'
        ]
      }
    ]
  }
]

const legendsSections = [
  {
    id: 'legends-abbreviations-units',
    title: 'Abbreviations & Units',
    description: [
      'Several abbreviations and symbols are used throughout the application. The following glossary explains the meaning of each symbol and the context in which it appears.'
    ],
    subsections: [
      {
        heading: 'Area & Conservation metrics',
        items: [
          'BSA \u2013 Buried Surface Area. The surface area of the protein\u2013protein interface that becomes inaccessible to solvent upon complex formation. Measured in \u00C5\u00B2 and displayed in the Interface Area chart.',
          'CR (Conserved Residues) \u2013 the number of unique residue pairs that appear in at least the specified percentage of trajectory frames. The subscript indicates the active pair conservation threshold (e.g. CR\u2085\u2080 at 50%).',
          'CA (Conserved Atomic interactions) \u2013 the number of pair\u2013type combinations (e.g., A-LYS8 \u2013 B-ASP45 via H-bond) that meet the interaction type conservation threshold.'
        ]
      },
      {
        heading: 'Units of measurement',
        items: [
          '\u00C5 (Ångström) \u2013 a unit of length equal to 10\u207B\u00B9\u2070 m. Used for interatomic distances and distance cutoff thresholds throughout the analysis.',
          'vdW (van der Waals) \u2013 refers to van der Waals radii. The sum of the vdW radii of two atoms is used as a reference distance for detecting clashes and apolar contacts.',
          'ns, ps, fs, \u03BCs \u2013 nanoseconds, picoseconds, femtoseconds, and microseconds. These time units may appear on chart axes if a time unit label was configured at job submission. If none is provided, axes default to frame numbers.'
        ]
      },
      {
        heading: 'Identifiers',
        items: [
          'PDB \u2013 Protein Data Bank, the standard file format for structural data. The application accepts trajectory files in .pdb format containing MODEL records.',
          'Atom type symbols \u2013 P (Phosphorus), N (Nitrogen), S (Sulfur), O (Oxygen), H (Hydrogen). These appear in atomic-level details in trajectory analysis panels.'
        ]
      }
    ]
  },
  {
    id: 'legends-residue-notation',
    title: 'Residue Notation',
    description: [
      'Residues are identified using a standardised notation that combines the amino acid name, sequence number, and chain identifier to ensure unambiguous references across all charts and panels.'
    ],
    subsections: [
      {
        heading: 'Individual residues',
        paragraphs: [
          'Residues are formatted as: RESNAMENUM\u2082CHAIN (for example, LYS8\u2082A or ASP45\u2082B).'
        ],
        items: [
          'RESNAME \u2013 the three-letter amino acid code (e.g., LYS for lysine, ASP for aspartic acid).',
          'NUM \u2013 the residue sequence number from the PDB file.',
          'CHAIN \u2013 the chain identifier (a single letter or character) from the PDB file.',
          'A hyphen prefixes the chain identifier for the second residue in a pair (e.g., B-ASP45) to signal that the residue belongs to a different chain.'
        ]
      },
      {
        heading: 'Residue pairs',
        paragraphs: [
          'Interactions are between two residues, displayed as: LYS8\u2082A \u2194 B-ASP45\u2082B.'
        ],
        items: [
          'The \u2194 symbol is used as the delimiter to visually separate the two residues in a cross-chain pair.',
          'This format is used consistently across the conservation matrix, trajectory analysis panels, ranking cards, and conservation analysis summaries.'
        ]
      }
    ]
  },
  {
    id: 'legends-conservation-modifiers',
    title: 'Conservation Modifiers & Suffixes',
    description: [
      'Special notations in the analysis results indicate additional properties of detected contacts or reflect the active threshold settings.'
    ],
    subsections: [
      {
        heading: 'Asterisk superscript',
        paragraphs: [
          'An asterisk (*) next to an interaction type label indicates that the same pair of atoms also qualifies as a clash\u2014that is, the interatomic distance falls below the sum of the van der Waals radii of the two atoms. This marks contacts that may be sterically strained or unusually close.'
        ]
      },
      {
        heading: 'Threshold subscripts',
        paragraphs: [
          'Conservation metrics display a subscript to indicate the threshold at which they are computed.'
        ],
        items: [
          'CR\u2085\u2080 \u2013 Conserved Residue Pairs computed at a 50% residue pair conservation threshold. The subscript changes to match the value selected via the Residue Pair Conservation Threshold slider (e.g., CR\u2087\u2080 at 70%).',
          'CA\u2085\u2080 \u2013 Conserved Atomic Interactions computed at a 50% interaction type conservation threshold. The subscript changes to match the Interaction Type Conservation Threshold slider.',
          'Changing the threshold sliders on the controls panel updates these subscripts in real time across all summary cards.'
        ]
      }
    ]
  },
  {
    id: 'legends-conservation-rankings',
    title: 'Conservation Analysis Rankings',
    description: [
      'The Conservation Analysis panel at the bottom of each chart page presents three ranked lists that summarise the most notable contacts at the interface.'
    ],
    subsections: [
      {
        heading: 'Most Conserved Residue Pairs',
        paragraphs: [
          'Ranking of residue pairs by their average conservation across all interaction types they participate in. A pair that forms multiple interaction types at high conservation will rank higher.'
        ],
        items: [
          'Each entry shows the residue pair, the number of frames it was detected in, and coloured interaction type tags.',
          'Coloured type tags use the global interaction palette. Hovering over a tag reveals the exact conservation: \u201cType \u2014 XX% (Y/Z frames)\u201d.',
          'Clicking the \u201c+N more\u201d button opens a modal with the complete ranked list.'
        ]
      },
      {
        heading: 'Longest Stretch with Conserved Residue Pair',
        paragraphs: [
          'Ranking of pairs by the maximum number of consecutive frames during which at least one interaction type persisted without interruption. This identifies sustained contacts, even if their overall frequency across the whole trajectory is moderate.'
        ],
        items: [
          'A long consecutive stretch suggests a structurally stable contact that may serve as an anchor point at the interface.'
        ]
      },
      {
        heading: 'Most Conserved Types',
        paragraphs: [
          'Ranking of interaction types by their average conservation across all pairs at the interface. This reveals which molecular forces (e.g., hydrogen bonds, \u03C0-\u03C0 stacking) dominate the interface overall.'
        ],
        items: [
          'A highly conserved type indicates a pervasive interaction mechanism at the interface, independent of the specific residues involved.'
        ]
      }
    ]
  }
]

const chartsSections = [
  {
    id: 'chart-conservation-matrix',
    title: 'Interaction Conservation Matrix',
    description: [
      'A comprehensive heatmap that visualises how consistently each residue pair interacts across all interaction types throughout the trajectory. The chart lets you see at a glance which contacts persist and which change over time.',
      'Alongside the matrix, an Atom Change Detection mode highlights where new interactions appear or existing ones break when you move from frame to frame.'
    ],
    image: IMG + 'screenshots/interaction-conservation-matrix.png',
    imageAlt: 'Interaction conservation matrix heatmap with color-coded interaction types',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'Rows represent individual residue pairs (e.g., A-LYS8 \u2013 B-ASP45). Each column corresponds to a specific interaction type and is coloured according to the global interaction palette. A filled cell means that the pair forms that interaction type in at least the minimum percentage of frames defined by the Interaction Type Conservation Threshold.',
          'Hovering over a cell reveals the exact conservation percentage for that pair\u2013type combination.'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'A densely filled row means a pair forms many different interaction types over the trajectory. A sparsely filled row means the pair is less versatile or short-lived. Data-backed interactions appear first in occurrence order. Deselected interactions are moved to the end of the legend with strikethrough text; hover over one to confirm that it is deselected in the shared filter. Active legend items can still be used to show or hide data-backed types.'
        ]
      },
      {
        heading: 'Filters: Conservation thresholds',
        paragraphs: [
          'Two sliders control which data are displayed.'
        ],
        items: [
          'Residue Pair Conservation Threshold \u2013 sets the minimum percentage of frames a residue pair must be present in to appear at all (0\u2013100%). Raising this removes infrequent pairs.',
          'Interaction Type Conservation Threshold \u2013 sets the minimum percentage of frames a specific interaction type must persist in for a given pair to show a cell (0\u2013100%).'
        ]
      },
      {
        heading: 'Atom Change Detection Mode',
        paragraphs: [
          'A selector above the chart lets you choose what the overlay dots are compared against. Changes are highlighted as orange dots with connecting lines on the heatmap. Three comparison modes are available:'
        ],
        items: [
          'Previous Frame \u2013 highlights atom-level differences between the current frame and the immediately preceding frame.',
          'Most Dominant Atom Pair \u2013 compares the current frame with the most frequently occurring atom pair for that cell across the whole trajectory.',
          'First Frame \u2013 compares the current frame with the first frame in which that interaction appears, using it as a baseline.'
        ]
      },
      {
        heading: 'Trajectory Analysis',
        paragraphs: [
          'Clicking any heatmap cell opens the Trajectory Analysis panel. This modal shows the binary timeline (present or absent) for that specific residue pair and interaction type across every frame of the simulation.',
          'The timeline bar at the top uses blue segments for frames where the interaction is present and gray for absent frames. Click on any segment to highlight it and see atom-level details for that frame\u2014which atoms are connected, bond distance, and the individual conservation of each atom pair.',
          'Statistical summary cards show the overall persistence, average distance, and the longest consecutive stretch where the interaction persists without interruption.'
        ],
        image: IMG + 'screenshots/trajectory-analysis.png',
        imageAlt: 'Trajectory analysis panel showing binary timeline and atom-level details'
      }
    ]
  },
  {
    id: 'chart-heatmap',
    title: 'Interaction Heatmap',
    description: [
      'A residue\u2013residue contact map that summarises the full interface between the two chains. Each cell represents a pair of residues, coloured by how frequently that pair interacts across the analysed frames.'
    ],
    image: IMG + 'screenshots/heatmap.png',
    imageAlt: 'Interaction heatmap contact map between Chain A and Chain B',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'The x-axis lists residues from Chain A and the y-axis lists residues from Chain B. The colour intensity of each cell encodes the interaction consistency\u2014the proportion of frames in which that pair is in contact\u2014ranging from light gray (rare) to deep blue (persistent).'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'A compact, continuous hotspot (a dark block or diagonal band) suggests a stable interface patch. Scattered dots indicate transient or localised contacts. Hover over a cell to see the pair name, list of interaction types, and the number of frames it appeared in.'
        ]
      },
      {
        heading: 'Controls',
        paragraphs: [
          'A toggle switch lets you choose how residue labels are displayed.'
        ],
        items: [
          'Full labels (default) \u2013 shows the full residue identifier (e.g., A-LYS8) for maximum clarity when there are few residues.',
          'Numbers only \u2013 shows only the sequence number for compactness on larger interfaces.',
          'The shared Residue Pair Conservation Threshold and Interaction Type Conservation Threshold sliders both apply to this heatmap. The pair threshold removes infrequent residue pairs; the type threshold removes interaction types that are insufficiently persistent within a retained pair.',
          'The main interaction type filter in the shared Controls Panel also applies to this heatmap.'
        ]
      }
    ]
  },
  {
    id: 'chart-interaction-trends',
    title: 'Interaction Trends',
    description: [
      'A line chart that tracks the evolution of interaction counts at the interface over the trajectory timeline. It shows how many contacts of each type exist frame by frame, making it easy to spot trends such as stable contacts, sudden disruptions, or gradual shifts in interaction composition.'
    ],
    image: IMG + 'screenshots/interaction-trends.png',
    imageAlt: 'Interaction trends line chart showing interaction counts over time',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'The dashed charcoal Total interactions line sums the selected interaction types after both conservation filters. A residue pair with multiple qualifying types contributes once per type. Hiding an individual line in the legend only changes its visibility; use the Interaction Type Filter to change the total. Each coloured line corresponds to one of the 18 interaction types, coloured consistently with the rest of the application. The x-axis represents frames (or a time unit such as ns or ps if configured). The y-axis shows the number of qualifying residue-pair interactions of that type in each frame after applying both conservation thresholds.'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'A flat, persistent line indicates a stable interaction throughout the simulation. Spikes suggest brief but intense events. A declining trend may indicate structural rearrangement. Multiple lines with similar trajectories suggest coupling between interaction types.',
          'Total interactions is listed first, followed by interaction types with qualifying data, with qualifying Proximal contacts at the end of that group and immediately before Atom Changes when the annotation is present. Selected types without qualifying data follow, while deselected types are placed at the end with strikethrough text and a hover explanation.'
        ]
      },
      {
        heading: 'Controls',
        items: [
          'Residue Pair Conservation Threshold slider \u2013 removes residue-pair contributions whose overall conservation is below the selected value and recalculates every frame of the trend.',
          'Interaction Type Conservation Threshold slider \u2013 removes pair\u2013type contributions whose type-specific conservation is below the selected value and recalculates every frame of the trend.',
          'Interaction Type Filter \u2013 the shared filter shown with the conservation sliders controls which interaction lines are included. Its selection is preserved when switching charts.',
          'Log scale toggle \u2013 available via the global Controls Panel, useful when interaction counts span several orders of magnitude.',
          'Time unit \u2013 the x-axis label reflects the configured time unit (frames, ns, ps) if one was provided during job submission.'
        ]
      }
    ]
  },
  {
    id: 'chart-distance-distribution',
    title: 'Distance Distribution',
    description: [
      'Violin plots showing the distribution of interatomic distances between residue pairs, broken down by interaction type. This view reveals not just the average separation of paired residues, but the spread and density of their distances over the full trajectory.'
    ],
    image: IMG + 'screenshots/distance-distribution.png',
    imageAlt: 'Distance distribution violin plots with global mean overlay',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'Each violin represents the distance distribution of a single residue pair for the selected interaction type. The width of the violin at a given distance indicates how frequently that distance occurs. A narrow, tall violin means the pair stays at a very consistent distance; a wide, short violin indicates more variability.'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'A dashed horizontal line marks the global mean distance across all displayed pairs. Individual mean markers (small dots) show where each pair\u2019s average falls. Pairs clustered near the global mean are typical of the interface, while outliers may represent unusually tight or loose contacts.'
        ]
      },
      {
        heading: 'Controls',
        items: [
          'Interaction Type Filter \u2013 the shared filter appears alongside both conservation sliders and determines which interaction types are available to this chart.',
          'Interaction Type Selector \u2013 colour-coded buttons above the chart choose the single interaction type whose distance distributions are displayed.',
          'Residue Pair Conservation Threshold slider \u2013 filters pairs by their overall conservation, from 0% to 100%.',
          'Interaction Type Conservation Threshold slider \u2013 filters the selected pair\u2013type distributions by the persistence of that interaction type, from 0% to 100%. The chart is limited to the top 50 qualifying pairs to maintain rendering performance.',
          'Hover tooltips \u2013 hovering over a violin displays the residue pair name and the number of frames contributing to the plot.'
        ]
      }
    ]
  },
  {
    id: 'chart-interface-area',
    title: 'Interface Area',
    description: [
      'Tracks the Buried Surface Area (BSA) at the protein\u2013protein interface across frames. BSA is a key indicator of interface stability and provides a macroscopic complement to the per-residue interaction data.'
    ],
    image: IMG + 'screenshots/interface-area.png',
    imageAlt: 'Buried Surface Area chart showing total, polar, and non-polar composition over frames',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'Each enabled measure shows total, polar, and non-polar area over time. Interface Area is calculated as BSA divided by two, including for existing results:'
        ],
        items: [
          'Total BSA (solid blue line) \u2013 the total buried surface area of the interface in \u00C5\u00B2.',
          'Polar BSA (orange line) \u2013 the portion of buried area contributed by polar residues.',
          'Non-Polar BSA (purple line) \u2013 the portion contributed by non-polar residues.'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'A stable total BSA across frames indicates a structurally stable interface. Divergence between polar and non-polar traces can indicate shifts in interface character, such as a growing hydrophobic core or an emerging polar patch.',
          'Toggle \"Mean \u00B1 Std Dev\" to display shaded bands around each line showing the average range. Statistics are off by default. When enabled, each legend entry shows its mean and standard deviation on a separate line.'
        ]
      },
      {
        heading: 'Controls',
        items: [
          'Mean \u00B1 Std Dev toggle \u2013 shows or hides the shaded standard deviation bands, giving a quick visual sense of variability.',
          'BSA and Interface Area switches \u2013 show either measure or both; at least one must remain enabled. BSA uses solid lines with filled markers and Interface Area uses dashed lines with hollow markers. Total, polar, and non-polar components use blue, orange, and purple respectively. Both measures use \u00C5\u00B2, and statistics follow the selected measures.'
        ]
      }
    ]
  },
  {
    id: 'chart-interface-patches',
    title: 'Interface Patches',
    description: [
      'Interface patches are clusters of residues that maintain persistent interactions across the trajectory. Rather than looking at pairs in isolation, this view groups spatially connected residues into interface patches, giving a higher-level picture of the stable core(s) of the interface.',
      'An interface patch is defined as a connected component of residues across two interacting chains, where connectivity is established via direct inter-chain residue–residue contacts.',
      'Integrated with the MolStar 3D viewer, you can highlight selected interface patches or pairs directly on the molecular structure to see their spatial arrangement.',
      'The CLI exports each interface patch as a downloadable bipartite network PNG under charts/interface_patches/. It also exports charts/interface_patch_3d.png: a Mol* snapshot of the cleaned first processed frame with the largest interface patch highlighted.'
    ],
    image: IMG + 'screenshots/interface-patches.png',
    imageAlt: 'Interface patches list with bipartite graph visualization',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'Each interface patch card lists its residues, the chains involved, and provides a mini bipartite graph (or table) of the internal pairs. Conservation bars indicate how frequently each contact persists.'
        ]
      },
      {
        heading: 'View modes',
        paragraphs: [
          'Two highlight modes are available via radio card buttons above the list:'
        ],
        items: [
          'Interface Patches \u2013 displays each interface patch as a card. Toggle between a graph view (SVG bipartite network) and a tabular view (residue, chain, residue number, and connected neighbours). Click an interface patch to highlight all its residues in the 3D viewer using ball-and-stick representation.',
          'Most Conserved Residue Pairs \u2013 a sortable, searchable table listing individual residue pairs ranked by their conservation percentage. Features checkboxes, conservation bars, and frame counts. Clicking a pair highlights those specific residues in the 3D viewer.'
        ]
      },
      {
        heading: '3D Visualisation',
        paragraphs: [
          'The MolStar viewer sits above the list. When you select an interface patch or pair, the corresponding residues are highlighted on the 3D structure. In Interface Patches mode, the representation is ball-and-stick to show the complete connectivity. In Pairs mode, it is a selection-based highlight.',
          'Clicking the same item again clears the selection.'
        ],
        image: IMG + 'screenshots/interface-patches-selection.png',
        imageAlt: 'Interface patches highlighted on the 3D MolStar viewer'
      },
      {
        heading: 'Controls',
        items: [
          'Interface Patch Conservation Threshold slider \u2013 rebuilds patches from residue-pair connections conserved in at least 50, 60, 70, 80, 90, or 100% of frames. It defaults to 70% and is independent of the pair-conservation control.',
          'Residue Pair Conservation Threshold slider \u2013 filters the individual pairs shown in Most Conserved Residue Pairs mode without changing interface-patch topology.'
        ]
      }
    ]
  },
  {
    id: 'chart-conservation-analysis',
    title: 'Conservation Analysis',
    description: [
      'The Conservation Analysis panel provides quantitative summary metrics about the stability of the interface. It appears at the bottom of each chart page and distills the full trajectory into two key numbers and three ranked lists.'
    ],
    image: IMG + 'screenshots/conservation-analysis.png',
    imageAlt: 'Conservation analysis panel showing CR, CA, and top-ranked interaction metrics',
    subsections: [
      {
        heading: 'What it shows',
        paragraphs: [
          'Two primary metrics are displayed as large summary cards:'
        ],
        items: [
          'CR (Conserved Residue count) \u2013 the number of unique residue pairs that appear in at least the specified percentage of trajectory frames. The subscript indicates the active pair conservation threshold (e.g. CR_{50} at 50%).',
          'CA (Conserved Atomic interactions) \u2013 the number of pair\u2013type combinations (e.g., A-LYS8 \u2013 B-ASP45 via H-bond) that meet the type conservation threshold.'
        ]
      },
      {
        heading: 'Insight rankings',
        paragraphs: [
          'Three ranked cards provide deeper insight into the most significant contacts:'
        ],
        items: [
          'Most Conserved Residue Pairs \u2013 residue pairs ranked by their average conservation across all interaction types. The top 3 are shown with frame counts and coloured interaction type tags. Click the \"+N more\" button for the full list.',
          'Longest Stretch with Conserved Residue Pair \u2013 pairs ranked by the maximum number of consecutive frames with any interaction maintained. This highlights contacts that persist without interruption, even if their overall frequency is moderate.',
          'Most Conserved Types \u2013 interaction types ranked by their average conservation across all pairs. Reveals which molecular forces dominate the interface.'
        ]
      },
      {
        heading: 'How to read it',
        paragraphs: [
          'Together these metrics let you quickly assess interface quality. A high CR with a high CA and long consecutive stretches indicates a tight, stable interface. A large discrepancy between CR and CA may suggest many pairs interact, but only through a narrow range of interaction types. The coloured type tags are consistent with the rest of the application\u2014hover for the exact conservation percentage.'
        ]
      }
    ]
  }
]

const cliSections = [
  {
    id: 'cli-overview',
    title: 'Introduction',
    description: [
      'The command-line tool analyses PDB structures and trajectories on your own computer. Results \u2014 CSV tables, PNG charts, and interface-patch summaries \u2014 are saved directly to your machine.',
      'Use it when you need to analyse more than 50 frames (the website limit), control frame ranges, or keep results locally for publications. By default, the CLI processes every frame in your PDB.',
      'The analysis runs inside Docker. Start it either with the small coco-md launcher (recommended: it builds the Docker command for you) or by typing the docker run command yourself. Both routes are described below.'
    ],
    subsections: []
  },
  {
    id: 'cli-install',
    title: 'Installation',
    description: [
      'Docker provides the CLI together with its analysis and chart-generation dependencies; you do not need to install Python packages or scientific libraries. The analysis image is about 1.2 GB and is downloaded once.'
    ],
    subsections: [
      {
        heading: 'Step 1: Install Docker Desktop',
        paragraphs: [
          'Download and install Docker Desktop for your operating system, then open it and wait until it is running. On Linux, an existing Docker Engine installation also works.'
        ],
        links: [{ label: 'Download Docker Desktop', url: 'https://www.docker.com/products/docker-desktop/' }]
      },
      {
        heading: 'Step 2: Install the coco-md launcher (macOS / Linux)',
        paragraphs: [
          'Open the Terminal app and run these two commands. They download the launcher to /usr/local/bin and make it executable; you will be asked for your password. Then download the analysis image with the third command.'
        ],
        codeBlocks: [
          { code: 'sudo curl -fsSL https://raw.githubusercontent.com/sattamaltwaim/COCOMAPS-MD/master/coco-md -o /usr/local/bin/coco-md' },
          { code: 'sudo chmod +x /usr/local/bin/coco-md' },
          { code: 'coco-md --update' }
        ],
        items: [
          'The launcher is a small Python 3 script. macOS and most Linux distributions already include Python 3.'
        ]
      },
      {
        heading: 'Step 2: Install the coco-md launcher (Windows)',
        paragraphs: [
          'Install Python 3 from python.org if you do not have it, ticking \u201CAdd python.exe to PATH\u201D in the installer. Then open PowerShell and run:'
        ],
        codeBlocks: [
          { code: 'New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\\bin"\nInvoke-WebRequest -Uri "https://raw.githubusercontent.com/sattamaltwaim/COCOMAPS-MD/master/coco-md" -OutFile "$env:USERPROFILE\\bin\\coco-md.py"' },
          { label: 'Add the folder to your PATH, then close and reopen PowerShell:', code: '[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";$env:USERPROFILE\\bin", "User")' },
          { label: 'Then download the analysis image:', code: 'coco-md.py --update' }
        ],
        items: [
          'On Windows the command is coco-md.py (with the extension) wherever the examples below show coco-md. If PowerShell does not recognise it, run python coco-md.py instead.'
        ]
      },
      {
        heading: 'Alternative: use Docker directly',
        paragraphs: [
          'If you prefer not to install the launcher, download the image with the command below and use the docker run commands shown in Usage. Keep --platform linux/amd64 in every command, including on Apple Silicon Macs: the bundled analysis programs require this platform.'
        ],
        codeBlocks: [
          { code: 'docker pull --platform linux/amd64 sattamaltwaim/cocomaps-md-cli:latest' }
        ]
      }
    ]
  },
  {
    id: 'cli-usage',
    title: 'Usage',
    description: [
      'Keep Docker running. Replace trajectory.pdb with your PDB filename and A B with the two chain IDs you want to analyse. Keep quotation marks around paths that contain spaces.'
    ],
    subsections: [
      {
        heading: 'Analyse a file with the launcher',
        paragraphs: [
          'Open a terminal in the folder containing your PDB, or pass the full path to the file, and run:'
        ],
        codeBlocks: [
          { code: 'coco-md trajectory.pdb -c A B -o results' },
          { label: 'A file elsewhere on your computer:', code: 'coco-md /Users/me/data/dimer.pdb -c A B -o /Users/me/data/dimer_results' }
        ],
        items: [
          'The launcher mounts the folders it needs, adds --platform linux/amd64, and passes every option through to the CLI. Relative and absolute paths both work.',
          'Run coco-md with no arguments to be asked for the file and settings step by step.'
        ]
      },
      {
        heading: 'Use defaults or customise settings',
        paragraphs: [
          'The CLI displays the detected frames, chains, and chosen settings. When asked whether to customise, press Enter to keep the defaults, or type y to edit them. Results are saved in the folder given with -o (here, a results folder beside your PDB). Use a new output folder name for each run: an existing folder is not cleared, and leftover files can be picked up by the next analysis.',
          'Always pass -o. If -o or the PDB path is left out, the CLI asks for it instead; the default output folder is systems/<pdb-name> inside your current folder.'
        ]
      },
      {
        heading: 'Change conservation thresholds or frame range',
        paragraphs: [
          'CR is the residue-pair conservation threshold and CA the interaction-type conservation threshold; they filter the conservation matrix, interaction heatmap, interaction trends, and distance distributions. Interface-patch charts and the Mol* snapshot always use pairs conserved in at least 70% of frames, and the interface area chart is not filtered. Frame-range options change which frames are analysed.'
        ],
        codeBlocks: [
          { label: 'Set CR to 50% and CA to 40%:', code: 'coco-md trajectory.pdb -c A B -o results_cr50_ca40 --pair-conservation 50 --interaction-conservation 40' },
          { label: 'Analyse frames 1 through 50, inclusive:', code: 'coco-md trajectory.pdb -c A B -o results_frames_1_50 -s 1 -e 50' },
          { label: 'Analyse every tenth frame:', code: 'coco-md trajectory.pdb -c A B -o results_every_10 -n 10' }
        ],
        items: [
          'Leave out -s, -e, and -n to process the full trajectory.'
        ]
      },
      {
        heading: 'Update to the latest version',
        paragraphs: [
          'The launcher reminds you after a run when your local image is more than 30 days old.'
        ],
        codeBlocks: [
          { code: 'coco-md --update' }
        ]
      },
      {
        heading: 'Run Docker directly (without the launcher)',
        paragraphs: [
          'These are the commands the launcher runs for you. First move into the folder containing your PDB; the /data prefix refers to that folder inside Docker. For a filename containing spaces, quote the complete input path, such as "/data/my trajectory.pdb". On Windows use PowerShell, not Command Prompt.'
        ],
        codeBlocks: [
          { label: 'macOS / Linux:', code: 'cd "/path/to/pdb-folder"\ndocker run --rm -it --platform linux/amd64 -v "$PWD:/data" sattamaltwaim/cocomaps-md-cli:latest /data/trajectory.pdb -c A B -o /data/results' },
          { label: 'Windows PowerShell:', code: 'Set-Location "C:\\path\\to\\pdb-folder"\ndocker run --rm -it --platform linux/amd64 -v "${PWD}:/data" sattamaltwaim/cocomaps-md-cli:latest /data/trajectory.pdb -c A B -o /data/results' },
          { label: 'Thresholds and frame options go after the PDB path, for example:', code: 'docker run --rm -it --platform linux/amd64 -v "${PWD}:/data" sattamaltwaim/cocomaps-md-cli:latest /data/trajectory.pdb -c A B -o /data/results_cr50_ca40 --pair-conservation 50 --interaction-conservation 40' },
          { label: 'Update the image:', code: 'docker pull --platform linux/amd64 sattamaltwaim/cocomaps-md-cli:latest' }
        ],
        items: [
          'Keep the -it flags: the customise prompt, -C, and the prompts for a missing -o or PDB path need them. The launcher adds them automatically when run from a terminal.'
        ]
      }
    ]
  },
  {
    id: 'cli-results',
    title: 'Progress and results',
    description: [
      'Frame processing and chart generation report completed work in the terminal. Spinners and elapsed time indicate ongoing work during longer operations. Stage counts describe completed steps, not an estimate of the time remaining.'
    ],
    subsections: [
      {
        heading: 'Where to find your results',
        codeBlocks: [
          { code: 'results/\n\u251C\u2500\u2500 trajectory.pdb              # Original input copy\n\u251C\u2500\u2500 viewer.pdb                  # Cleaned first processed frame\n\u251C\u2500\u2500 _metadata.json              # Frame count, chains, job ID\n\u251C\u2500\u2500 _interactions.csv           # Residue-pair interactions\n\u251C\u2500\u2500 _atom_pairs.csv             # Atom-pair data\n\u251C\u2500\u2500 _area.csv                   # Surface-area data\n\u251C\u2500\u2500 _trends.csv                 # Interaction trends\n\u251C\u2500\u2500 _water_mediated.csv         # Water-mediated contacts (when present)\n\u251C\u2500\u2500 _metal_mediated.csv         # Metal-mediated contacts (when present)\n\u251C\u2500\u2500 _interface_patches.json     # Interface-patch data\n\u2514\u2500\u2500 charts/\n    \u251C\u2500\u2500 conservation_matrix.png\n    \u251C\u2500\u2500 interaction_heatmap.png\n    \u251C\u2500\u2500 interaction_trends.png\n    \u251C\u2500\u2500 interface_area.png\n    \u251C\u2500\u2500 interface_patch_3d.png\n    \u251C\u2500\u2500 distance_distribution/\n    \u2502   \u2514\u2500\u2500 dist_*.png\n    \u2514\u2500\u2500 interface_patches/\n        \u2514\u2500\u2500 *.png' }
        ],
        paragraphs: [
          'Typical output structure is shown below. The original PDB keeps its own filename. Chart files depend on enabled charts and available interaction data.'
        ],
        items: [
          'Open results/charts/ to find PNG figures: conservation matrix, interaction heatmap, interaction trends, interface area, distance distributions, and interface-patch charts when data are available.',
          'charts/interface_patch_3d.png is the Mol* snapshot of the cleaned first processed frame with the largest conserved interface patch highlighted.',
          'CSV files in the results folder contain the interaction, atom-pair, area, and trend data, plus water- and metal-mediated contact tables when those interactions occur. JSON files contain the run metadata (frame count, chains, job ID) and interface-patch information.',
          'viewer.pdb is the cleaned structure used for the Mol* snapshot. Temporary frame_* directories are removed after aggregation and viewer preparation, before chart export.'
        ]
      }
    ]
  },
  {
    id: 'cli-troubleshooting',
    title: 'Troubleshooting',
    description: [],
    subsections: [
      {
        heading: 'Zero BSA or Interface Area values',
        paragraphs: [
          'BSA and Interface Area require the bundled NACCESS executable. The CLI checks for its surface-area summary after the frames are analysed and stops if it is missing. When that happens no CSV tables or charts are written, and the temporary frame_* folders remain in the output folder.'
        ],
        items: [
          'Run coco-md --update (or the docker pull command in Usage), then rerun the analysis in a new output folder.',
          'When running Docker directly, keep --platform linux/amd64 in your docker run command.',
          'If NACCESS still fails, retain the terminal error message when reporting the problem.'
        ]
      },
      {
        heading: 'Other common problems',
        items: [
          'coco-md command not found: the launcher is not installed or not on your PATH. Reinstall it with the commands in Installation (on Windows, run coco-md.py or python coco-md.py), or use the docker run command in Usage instead.',
          'Cannot connect to Docker: open Docker Desktop and wait until it is running, then retry.',
          'PDB file not found: check that your terminal is in the folder containing the PDB, or pass the full path. With docker run, the filename after /data/ must match exactly.',
          'Chain not found: use the available chain IDs printed by the CLI; chain IDs are case-sensitive.',
          'Mol* image missing: check the terminal for a snapshot warning. A job with no detected interface patch produces no snapshot at all. Other causes are an older image without the Mol* renderer (run coco-md --update) or the snapshot exceeding its 120-second limit.',
          'Prompts do not appear, or the run stops with EOFError: when running Docker directly, the customise prompt, -C, and the prompts for a missing -o or PDB path need the -it flags. The launcher adds them automatically when run from a terminal.',
          'Custom parameters (-p): the launcher accepts any path; with docker run the JSON file must be inside the mounted folder, for example -p /data/params.json. Unknown keys are ignored, and a file that cannot be read is reported but does not stop the run.',
          'Proximal contacts are excluded from the charts by default; use -C to include them.',
          'Old version still running: neither the launcher nor docker run refreshes an image you already have. Run coco-md --update or the docker pull command in Usage.',
          'Files owned by root (Linux): the container writes as root. Use sudo chown -R $USER results to take ownership.'
        ]
      }
    ]
  },
  {
    id: 'cli-options',
    title: 'Command-line reference',
    description: [
      'Add options after the PDB path. Leave them unchanged for a standard run. Show the full help with the launcher, or through Docker directly:'
    ],
    subsections: [
      {
        codeBlocks: [
          { code: 'coco-md --help' },
          { code: 'docker run --rm --platform linux/amd64 sattamaltwaim/cocomaps-md-cli:latest --help' },
          { code: 'Options (append after the PDB path):\n\n  -c A B         Chain IDs to analyse (default: first two chain IDs in the file, alphabetically)\n  -o DIR         Output directory (launcher: any folder; docker run: /data/<folder>).\n                 If omitted the CLI asks; default systems/<pdb-name>\n  -r             Add hydrogens with Reduce before analysis (default: off)\n  -i CUTOFF      Interface cutoff in \u00C5 (default: 5.0)\n  -w CUTOFF      Water bridge cutoff in \u00C5 (default: same as -i)\n  -s N           Start frame, 1-indexed (default: first)\n  -e N           End frame, 1-indexed inclusive (default: last)\n  -n N           Frame step \u2014 analyse every Nth frame (default: 1)\n  --pair-conservation N\n                 CR threshold % for charts (0\u2013100, default: 50; alias: -t)\n  --interaction-conservation N\n                 CA threshold % for charts (0\u2013100, default: 50)\n  -u UNIT        Time axis label for charts (default: Frame)\n  -p FILE        JSON file with CoCoMaps parameter overrides\n  -C             Enter interactive parameter customisation before running\n  --update       Launcher only: download the latest analysis image\n  -h, --help     Show command-line help' }
        ]
      }
    ]
  },
]

const tabs = [
  {
    id: 'usage',
    label: 'Usage',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>',
    sections: usageSections
  },
  {
    id: 'charts',
    label: 'Charts',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M9 21V9"/></svg>',
    sections: chartsSections
  },
  {
    id: 'interactions',
    label: 'Interactions',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="8" cy="12" r="4"/><circle cx="16" cy="12" r="4"/></svg>',
    sections: interactionSections
  },
  {
    id: 'legends',
    label: 'Legends',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></svg>',
    sections: legendsSections
  },
  {
    id: 'cli',
    label: 'CLI',
    icon: '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M11 15h5"/></svg>',
    sections: cliSections
  }
]

function switchTab(tabId) {
  activeTab.value = tabId
  sidebarOpen.value = false
  router.replace({ query: { tab: tabId }, hash: '' })
  nextTick(() => {
    updateActiveFromScroll()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  })
}

function scrollToSection(sectionId) {
  const el = document.getElementById(sectionId)
  if (el) {
    activeSection.value = sectionId
    el.scrollIntoView({ behavior: 'smooth' })
    sidebarOpen.value = false
  }
}

function copyCode(code, event) {
  navigator.clipboard.writeText(code)
  const btn = event.currentTarget
  btn.classList.add('copied')
  setTimeout(() => btn.classList.remove('copied'), 1500)
}

function restoreFromURL() {
  const tabParam = route.query.tab
  if (tabParam && tabs.some(t => t.id === tabParam)) {
    activeTab.value = tabParam
  }
  nextTick(() => {
    updateActiveFromScroll()
    if (route.hash) {
      const id = route.hash.slice(1)
      const el = document.getElementById(id)
      if (el) {
        setTimeout(() => {
          el.scrollIntoView({ behavior: 'smooth' })
          setTimeout(() => updateActiveFromScroll(), 400)
        }, 100)
      }
    }
  })
}

onMounted(() => {
  window.addEventListener('scroll', onScroll, { passive: true })
  window.addEventListener('resize', onResize, { passive: true })
  restoreFromURL()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onScroll)
  window.removeEventListener('resize', onResize)
  if (scrollRaf != null) cancelAnimationFrame(scrollRaf)
})

watch(() => route.query.tab, (newTab) => {
  if (newTab && newTab !== activeTab.value && tabs.some(t => t.id === newTab)) {
    activeTab.value = newTab
    nextTick(() => updateActiveFromScroll())
  }
})

watch(activeSection, (id) => {
  if (!id) return
  nextTick(() => {
    const link = document.querySelector(`.docs-sidebar a[href="#${CSS.escape(id)}"]`)
    if (link) link.scrollIntoView({ block: 'nearest' })
  })
})
</script>

<style scoped>
.help-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f7;
}

/* ── Header ── */
.page-header {
  padding: 60px 40px 32px;
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

/* ── Tab Bar ── */
.docs-tabs {
  display: flex;
  justify-content: center;
  gap: 8px;
  padding: 16px 40px 24px;
  position: sticky;
  top: 57px;
  z-index: 50;
  background: #f5f5f7;
}

.docs-tab {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 22px;
  font-size: 15px;
  font-weight: 600;
  color: #6e6e73;
  background: #ffffff;
  border: 2px solid #e8e8ed;
  border-radius: 980px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-family: inherit;
}

.docs-tab:hover {
  color: #1d1d1f;
  border-color: #d2d2d7;
  background: #fafafa;
}

.docs-tab.active {
  color: #ffffff;
  background: #1d1d1f;
  border-color: #1d1d1f;
}

.tab-icon {
  display: inline-flex;
  align-items: center;
}

.docs-tab.active .tab-icon :deep(svg) {
  stroke: #ffffff;
}

/* ── Docs Layout ── */
.docs-layout {
  display: flex;
  gap: 0;
  max-width: 1320px;
  margin: 0 auto;
  padding: 0 40px 80px;
  width: 100%;
  position: relative;
}

/* ── Sidebar ── */
.docs-sidebar {
  width: 240px;
  flex-shrink: 0;
  position: sticky;
  top: 120px;
  align-self: flex-start;
  max-height: calc(100vh - 140px);
  overflow-y: auto;
  padding-right: 24px;
  scrollbar-width: thin;
  scrollbar-color: #d2d2d7 transparent;
}

.docs-sidebar::-webkit-scrollbar {
  width: 4px;
}

.docs-sidebar::-webkit-scrollbar-thumb {
  background: #d2d2d7;
  border-radius: 2px;
}

.docs-sidebar-panel {
  display: none;
}

.docs-sidebar-panel.active {
  display: block;
}

.sidebar-heading {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #86868b;
  margin: 0 0 12px;
  padding: 0 12px;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  font-size: 14px;
  font-weight: 500;
  color: #6e6e73;
  text-decoration: none;
  border-radius: 8px;
  border-left: 3px solid transparent;
  transition: all 0.15s ease;
  margin-bottom: 2px;
}

.sidebar-link:hover {
  color: #1d1d1f;
  background: rgba(0, 0, 0, 0.03);
}

.sidebar-link.active {
  color: #1d1d1f;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.04);
  border-left-color: #1d1d1f;
}

.sidebar-color-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* ── Mobile Sidebar ── */
.sidebar-backdrop {
  display: none;
}

.sidebar-toggle {
  display: none;
}

/* ── Content ── */
.docs-content {
  flex: 1;
  min-width: 0;
}

.docs-panel {
  display: none;
}

.docs-panel.active {
  display: block;
}

.docs-section {
  scroll-margin-top: 140px;
  margin-bottom: 32px;
}

.docs-section-card {
  background: #ffffff;
  border-radius: 20px;
  padding: 40px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

/* ── Section Header with color bar ── */
.section-header {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 8px;
}

.section-color-bar {
  width: 4px;
  height: 32px;
  border-radius: 2px;
  flex-shrink: 0;
}

.section-header h2 {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0;
  letter-spacing: -0.02em;
}

.section-description {
  font-size: 17px;
  line-height: 1.6;
  color: #6e6e73;
  margin: 0 0 20px;
}

.section-description:last-of-type {
  margin-bottom: 28px;
}

/* ── Section Image ── */
.section-image {
  margin: 0 0 28px;
  text-align: center;
  background: #fafafa;
  border: 1px solid #f0f0f2;
  border-radius: 14px;
  padding: 24px;
}

.section-image img {
  max-width: 100%;
  max-height: 340px;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
}

/* ── Subsections ── */
.docs-subsection {
  margin-bottom: 28px;
}

.docs-subsection:last-child {
  margin-bottom: 0;
}

.docs-card-text h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1d1d1f;
  margin: 0 0 12px;
}

.docs-card-text p {
  font-size: 16px;
  line-height: 1.65;
  color: #424245;
  margin: 0 0 12px;
}

.docs-card-text p:last-child {
  margin-bottom: 0;
}

.docs-card-text ul {
  margin: 8px 0 0;
  padding-left: 24px;
}

.docs-card-text li {
  font-size: 16px;
  line-height: 1.65;
  color: #424245;
  margin-bottom: 6px;
}

/* ── Criteria List (ordered) ── */
.criteria-list {
  margin: 12px 0 0;
  padding-left: 24px;
}

.criteria-list li {
  font-size: 15px;
  line-height: 1.7;
  color: #424245;
  margin-bottom: 8px;
  padding-left: 4px;
}

.criteria-list li::marker {
  color: #86868b;
  font-weight: 600;
}

/* ── Code Blocks ── */
.code-blocks {
  margin: 12px 0 16px;
}

.code-block {
  margin-bottom: 10px;
}

.code-block:last-child {
  margin-bottom: 0;
}

.code-label {
  font-size: 14px;
  color: #6e6e73;
  margin: 0 0 6px;
}

.code-container {
  position: relative;
  background: #1d1d1f;
  border-radius: 10px;
  overflow: hidden;
}

.code-container pre {
  margin: 0;
  padding: 14px 48px 14px 16px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.code-container code {
  font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', Menlo, Monaco, 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.6;
  color: #f5f5f7;
  white-space: pre;
}

.copy-btn {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  background: rgba(255, 255, 255, 0.08);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  color: #a1a1a6;
  transition: background 0.15s ease, color 0.15s ease;
}

.copy-btn:hover {
  background: rgba(255, 255, 255, 0.18);
  color: #ffffff;
}

.copy-btn.copied {
  background: rgba(52, 199, 89, 0.2);
}

.copy-btn .icon-check {
  display: none;
}

.copy-btn.copied .icon-copy {
  display: none;
}

.copy-btn.copied .icon-check {
  display: inline;
  stroke: #34c759;
}

/* ── Subsection Links ── */
.subsection-links {
  margin: 8px 0 14px;
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.subsection-link {
  display: inline-flex;
  align-items: center;
  font-size: 15px;
  font-weight: 500;
  color: #0071e3;
  text-decoration: none;
  padding: 6px 14px;
  background: #f0f5ff;
  border-radius: 8px;
  transition: background 0.15s ease;
}

.subsection-link:hover {
  background: #dce8ff;
}

/* ── Status List ── */
.status-list {
  list-style: none;
  margin: 12px 0 0;
  padding: 0;
}

.status-list-item {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 8px 0;
  font-size: 16px;
  line-height: 1.65;
  color: #424245;
  border-bottom: 1px solid #f0f0f2;
}

.status-list-item:last-child {
  border-bottom: none;
}

.status-indicator {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  position: relative;
  top: 2px;
}

.status-text strong {
  color: #1d1d1f;
}

/* ── References Footer ── */
.section-references {
  margin-top: 0;
  padding-top: 16px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.ref-label {
  font-size: 13px;
  font-weight: 600;
  color: #86868b;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.ref-link {
  font-size: 13px;
  color: #0071e3;
  text-decoration: none;
  padding: 3px 10px;
  background: #f0f5ff;
  border-radius: 6px;
  transition: background 0.15s ease, color 0.15s ease;
  word-break: break-all;
}

.ref-link:hover {
  background: #dce8ff;
  color: #0056b3;
}

/* ── Media Layout (text + image) ── */
.docs-card-media {
  display: flex;
  align-items: flex-start;
  gap: 32px;
}

.docs-card-media .docs-card-text {
  flex: 1;
  min-width: 0;
}

.docs-card-image {
  flex-shrink: 0;
  width: 340px;
}

.docs-card-image img {
  width: 100%;
  height: auto;
  border-radius: 12px;
  background: #fafafa;
  border: 1px solid #f0f0f2;
}

/* ── Responsive ── */
@media (max-width: 992px) {
  .page-header {
    padding: 40px 24px 24px;
  }

  .page-header h1 {
    font-size: 36px;
  }

  .docs-tabs {
    padding: 0 24px 20px;
    gap: 6px;
    flex-wrap: wrap;
  }

  .docs-tab {
    padding: 8px 16px;
    font-size: 14px;
  }

  .docs-layout {
    padding: 0 24px 60px;
  }

  .docs-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: 280px;
    height: 100vh;
    max-height: 100vh;
    background: #ffffff;
    z-index: 200;
    padding: 24px;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.12);
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    border-radius: 0;
  }

  .docs-sidebar.open {
    transform: translateX(0);
  }

  .sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.3);
    z-index: 199;
    animation: fadeIn 0.2s ease;
  }

  .sidebar-toggle {
    display: flex;
    align-items: center;
    justify-content: center;
    position: fixed;
    bottom: 24px;
    left: 24px;
    width: 48px;
    height: 48px;
    background: #1d1d1f;
    color: #ffffff;
    border: none;
    border-radius: 50%;
    cursor: pointer;
    z-index: 198;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    transition: transform 0.15s ease, background 0.15s ease;
  }

  .sidebar-toggle:hover {
    background: #000000;
    transform: scale(1.05);
  }

  .docs-section-card {
    padding: 28px;
  }

  .docs-card-media {
    flex-direction: column;
  }

  .docs-card-image {
    width: 100%;
    max-width: 400px;
  }

  .section-image img {
    max-height: 260px;
  }
}

@media (max-width: 600px) {
  .docs-tabs {
    gap: 4px;
  }

  .docs-tab {
    padding: 7px 12px;
    font-size: 13px;
    gap: 5px;
  }

  .tab-icon {
    display: none;
  }

  .docs-section-card {
    padding: 20px;
    border-radius: 16px;
  }

  .section-header h2 {
    font-size: 22px;
  }

  .docs-card-text h3 {
    font-size: 18px;
  }

  .section-image {
    padding: 16px;
  }

  .section-image img {
    max-height: 200px;
  }

  .section-references {
    flex-direction: column;
    align-items: flex-start;
  }

  .code-container pre {
    padding: 12px 40px 12px 12px;
  }

  .code-container code {
    font-size: 12px;
  }
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
</style>

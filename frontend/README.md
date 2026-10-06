# Frontend

Vue 3 single-page application for visualizing COCOMAPS-MD results. Communicates with the Flask [backend](../backend/) via REST API.

## Running

```bash
cd frontend
npm install
npm run dev        # → http://localhost:5173
```

The Vite dev server proxies `/api` requests to `http://localhost:5001` (Flask backend).

## Routes

| Path | View | Description |
|------|------|-------------|
| `/` | `LandingPage` | Upload PDB, select chains, configure analysis, track processing |
| `/analysis/:jobId` | `AnalysisView` | Main analysis dashboard with charts and controls |
| `/jobs` | `JobsPage` | Sortable/searchable list of all jobs (active, completed, failed) |
| `/about` | `AboutPage` | Short overview of COCOMAPS-MD |
| `/references` | `ReferencesPage` | Citations (CoCoMaps 2.0), BibTeX, software dependencies |

## Architecture

```
src/
├── views/                      # Route-level pages
├── components/
│   ├── layout/                 # App chrome (navbar, footer)
│   ├── landing/                # Upload flow (chain selector, advanced settings, tooltips)
│   ├── analysis/               # Dashboard (charts shell, controls, Mol*, modals, sidebar)
│   └── charts/                 # Chart visualizations (Highcharts, Plotly, etc.)
├── composables/                # Vue composables
│   └── useConservationStatistics.js
├── services/
│   └── api.js                  # Axios API client (all backend endpoints)
├── stores/
│   ├── systemsStore.js         # Jobs/systems list, current system, loadSystems, setCurrentSystem
│   ├── analysisStore.js        # Interactions, area, trends, interface patches + filteredInteractions getter
│   └── chartUiStore.js         # Chart type, thresholds, interaction-type filters, time unit
├── utils/
│   ├── constants.js            # 18 interaction types (id, label, keywords)
│   ├── chartHelpers.js         # Color palette, type matching, residue formatting
│   └── highchartsConfig.js     # Shared Highcharts export configuration
├── router/
│   └── index.js                # Vue Router (5 routes, base: /BioTools/COCOMAPS-MD/)
├── App.vue                     # Root component
└── main.js                     # App entry (Pinia, Router, Highcharts modules)
```

## Key Components

### Analysis Dashboard (`AnalysisView.vue`)
System sidebar, chart selector tabs, dynamic chart container, conservation threshold slider, interaction type filters, stats panel, and conservation analysis summary.

### Charts (6 types, switchable via tabs)

| Chart | Library | Description |
|-------|---------|-------------|
| Interaction Conservation Matrix | Highcharts heatmap | Residue pair × frame timeline |
| Filtered Heatmap | Highcharts heatmap | Residue × residue conservation matrix |
| Interaction Trends | Highcharts line | Interaction type counts per frame |
| Interface Area | Highcharts area | BSA and/or Interface Area (BSA ÷ 2), each with total/polar/non-polar series and optional ±σ bands; at least one measure stays enabled |
| Distance Distribution | Plotly violin | Per-interaction-type distance distributions |
| Interface Patches | Custom | Cached 50–100% interface-patch topology + graph/table views |

### Deep-Dive Modals
- **InteractionTrajectoryModal** — Distance trajectory chart, interaction type timeline, atom connections per frame, frame-by-frame data table
- **AtomPairExplorer** — Atom pair frequency chart, frame timeline, transitions, conservation threshold slider

### 3D Structure
**MolStarViewer** — Embeds Mol\* for viewing frame PDB structures with residue highlighting.

## Data Flow

1. `LandingPage` uploads PDB via `api.uploadFileWithOptions()`, polls `api.getStatus()` until complete
2. On completion, redirects to `/analysis/:jobId`
3. `AnalysisView` loads systems, resolves jobId → systemId, calls `systemsStore.setCurrentSystem()`
4. `setCurrentSystem` loads interactions, area, trends, and the interface-patch edge catalogue in parallel via `analysisStore`
5. `filteredInteractions` getter applies conservation threshold + interaction type filters
6. Charts and panels reactively update via Pinia store

The Interface Patches view derives connected components from its edge catalogue at 50, 60, 70, 80, 90, and 100% conservation. All six results are cached in the browser; the independent patch threshold defaults to 70% and does not trigger API requests.

## Job Privacy

Job IDs are stored in each user's browser via `localStorage` (key: `cocomapsmd:submittedJobIds`). The Jobs page only shows jobs whose IDs are present in that list, so each user sees only their own submissions. Analysis URLs remain publicly shareable — anyone with a direct `/analysis/:jobId` link can view the results.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `/api` in production, `http://localhost:5001/api` in dev | Backend API base URL |
| `base` (vite.config.js) | `/BioTools/COCOMAPS-MD/` | Deploy path prefix |

## Tech Stack

- **Vue 3** + Composition API (`<script setup>`)
- **Pinia** for state management
- **Vue Router** with HTML5 history mode
- **Highcharts** + `highcharts-vue` for interactive charts (heatmaps, line, area)
- **Plotly.js** for violin plots
- **Mol\*** for 3D molecular visualization
- **Axios** for HTTP requests
- **Vite** for dev server and builds
- **Sass** for component styles

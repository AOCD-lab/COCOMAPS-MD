# Backend

Flask REST API that serves PDB analysis data to the Vue.js frontend. Reads pre-computed system-level CSVs and metadata produced by the [engine](../engine/).

## Running

From the **project root**:
```bash
python run_backend.py
```

The API will be available at `http://localhost:5001`.

## API Endpoints

### Systems

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/systems` | List all available systems (name, frames, chains, job info) |
| `GET` | `/api/systems/<id>` | Get details for a specific system |

Job aliases created from the frontend's "Your Jobs" page are stored only in
that browser's local storage. The API does not expose a system rename endpoint.

### Data

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/systems/<id>/interactions` | Aggregated interactions with consistency scores and type persistence |
| `GET` | `/api/systems/<id>/area` | Buried surface area per frame (total, polar, non-polar) |
| `GET` | `/api/systems/<id>/trends` | Interaction type counts per frame (18 types) |
| `GET` | `/api/systems/<id>/atom-pairs?resName1=...&resNum1=...&chain1=...&resName2=...&resNum2=...&chain2=...` | Atom-level detail for a specific residue pair |
| `POST` | `/api/systems/<id>/atom-pairs/batch` | Atom-level detail for multiple residue pairs in one request |
| `GET` | `/api/systems/<id>/interaction-distances` | Distance data for all interactions across all frames |
| `GET` | `/api/systems/<id>/distance-distributions?interaction_types=H-bond,Salt-bridge` | Distance distributions filtered by interaction type |
| `GET` | `/api/systems/<id>/interface-patches` | Interface patch data |
| `GET` | `/api/systems/<id>/frame/<n>/pdb` | Serve a frame's PDB (for Mol\*). For `n=1`, serves root `viewer.pdb` when present (web upload: first selected frame with distant waters/metals/simple ions removed); else `frame_1.pdb` / `frame_1.pd_h.pdb` |

### Upload & Processing

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/upload` | Persist a PDB file and add it to the analysis queue |
| `GET` | `/api/status/<job_id>` | Poll processing status (progress %, step label) |
| `GET` | `/api/jobs` | List all jobs (active, completed, failed) |

#### Upload form fields

| Field | Default | Description |
|-------|---------|-------------|
| `file` | — | PDB file (required) |
| `job_name` | filename stem | Display name for the system |
| `email` | — | Owner email (stored in metadata). If set and SMTP is configured, a link to the results is emailed when the job completes |
| `chain1` / `chain2` | `A` / `B` | Chain IDs |
| `interface_cutoff` | `5.0` | Interface selection cutoff (Å) |
| `start_frame` | `1` | First frame (1-indexed) |
| `end_frame` | `-1` | Last frame (-1 = all) |
| `frame_step` | `1` | Analyze every Nth frame |
| `reduce` | `false` | Use reduce version of CoCoMaps |

## Email notifications

When a job finishes successfully and an email address was provided, the backend
sends a message containing the job ID and the link to the results
(`<COCOMAPS_PUBLIC_URL>/analysis/<jobId>`). Sending is best-effort and runs in a
background thread: SMTP problems are logged and never change the job status.

SMTP settings come from environment variables, wired through `docker-compose.yml`
(values can live in the gitignored `.env`; see `.env.example`):

| Variable | Default | Description |
|----------|---------|-------------|
| `SMTP_HOST` | — | SMTP server. **Empty = notifications disabled** |
| `SMTP_PORT` | `587` | SMTP port |
| `SMTP_SECURITY` | `starttls` | `starttls`, `ssl` (implicit TLS, e.g. 465) or `none` |
| `SMTP_USER` / `SMTP_PASSWORD` | — | Credentials (no login if `SMTP_USER` is empty) |
| `SMTP_FROM` | `SMTP_USER` | Sender address, e.g. `COCOMAPS-MD <no-reply@example.org>` |
| `SMTP_TIMEOUT` | `20` | Socket timeout in seconds |
| `COCOMAPS_PUBLIC_URL` | — | Public base URL including the path prefix, e.g. `https://example.org/BioTools/COCOMAPS-MD`. Required to build the link |

Implementation: [`mailer.py`](mailer.py), hooked in `process_queued_job` in
[`routes/upload.py`](routes/upload.py).

## Modules

### [`app.py`](app.py)
Flask application factory. Enables CORS, sets the 200 MB upload limit, starts
the analysis queue once per process, and registers the three route blueprints
under `/api`.

### [`routes/systems.py`](routes/systems.py)
System discovery and management. Scans `systems/` for directories containing `frame_N/` folders, reads chain patterns from CSV filenames, and pulls job metadata from `_metadata.json`.

### [`routes/data.py`](routes/data.py)
Data retrieval — the largest module (721 lines). Reads from the aggregated CSVs (`_interactions.csv`, `_area.csv`, `_trends.csv`, `_atom_pairs.csv`) and the threshold-independent edge catalogue in `_interface_patches.json`. Computes consistency scores, type persistence, atom-pair statistics, and distance distributions on the fly.

### [`routes/upload.py`](routes/upload.py)
Persistent FIFO upload and processing queue. Uploaded inputs are staged under
`systems/.queued/<job_id>/input.pdb`; two worker threads run `engine.run_pipeline()`
concurrently by default. Queue state is atomically persisted to `.jobs.json`.
Queued and interrupted jobs are recovered after a backend restart. After a
successful web job writes `viewer.pdb`, the copied raw source trajectory at
`systems/<system_id>/input.pdb` is deleted to keep completed systems small.

## Configuration

CoCoMaps runs as a local Python package (`cocomaps/`) with binary dependencies in `deps/`.

Environment variables (via `.env` or environment):
- `COCOMAPS_DEPS_DIR` — Path to binary deps directory (default: `<project_root>/deps/`)
- `COCOMAPS_JOB_WORKERS` — Maximum concurrent analysis jobs (default: `2`)
- `COCOMAPS_USE_REDUCE` — Default reduce mode (`true`/`false`, default: `false`)
- Per-upload override: send `reduce=true` or `reduce=false` in the upload form

The in-process queue assumes one backend process. Additional submissions remain
queued without a queue-length or submission-rate limit. `/api/upload` returns
`503 Service Unavailable` with `Retry-After: 5` only when staging, persistence,
or enqueueing fails. The upload size limit remains 200 MB.

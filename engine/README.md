# Engine

Core analysis pipeline for processing PDB structures through [CoCoMaps](http://www.molnac.unisa.it/BioTools/cocomaps/) and detecting conserved interaction patterns across molecular dynamics (MD) trajectory frames.

## What It Does

This package takes a multi-model PDB file and:

1. **Splits** it into individual frames
2. **Selects** interface residues, bridging waters, and metals between two protein chains
3. **Runs** CoCoMaps interaction analysis on each frame via Docker
4. **Detects** interface patches — residue clusters that persist across frames
5. **Aggregates** all per-frame results into system-level CSVs and metadata

After a successful web upload, the backend also writes a **Mol\* viewer PDB** (`viewer.pdb`) — see [`viewer_pdb.py`](viewer_pdb.py) and the detailed notes in [`../docs/README.md`](../docs/README.md). The CLI pipeline does not run this step automatically; run it yourself if you need the viewer file locally.

## Modules

### [`analyze_pdb.py`](analyze_pdb.py)
Main pipeline orchestrator and CLI entry point. Handles all file I/O: frame splitting, PDB writing, Docker execution, and progress reporting.

**Key functions:**
- `run_pipeline()` — Full pipeline entry point (used by both CLI and web backend)
- `process_frames()` — Splits PDB into frames with optional interface selection
- `run_cocomaps_analysis()` — Executes CoCoMaps Docker containers on each frame
- `create_input_jsons()` — Generates CoCoMaps configuration files

**CLI usage:**
```bash
# Basic analysis
python -m engine.analyze_pdb systems/my_protein.pdb

# Custom cutoff and chains
python -m engine.analyze_pdb systems/my_protein.pdb --interface-cutoff 7.0 -c A B

# With hydrogen addition (slower)
python -m engine.analyze_pdb systems/my_protein.pdb --use-reduce
```

### [`viewer_pdb.py`](viewer_pdb.py)
Builds **`viewer.pdb`** at the system root for the Mol\* 3D viewer: one structure using the **first processed frame** of the **original** system PDB, filtered for the selected interface chains.

**What to keep:** Non-solvent/non-ion residues from the two selected chains are kept. Waters, metals, and configured simple ions are kept only when they are within 5.0 Angstroms of both user-selected chains; unselected chains and distant bulk solvent/ions are dropped.

**When it runs:** **`write_viewer_frame_pdb(system_dir, chain_a=..., chain_b=...)`** is called from the Flask upload handler after `run_pipeline()` succeeds (`backend/routes/upload.py`). It is **not** part of `python -m engine.analyze_pdb`.

**Manual / CLI runs:** After the pipeline has produced `_interactions.csv` and the usual `frame_*` outputs:

```bash
python -c "from engine.viewer_pdb import write_viewer_frame_pdb; write_viewer_frame_pdb('systems/my_system', verbose=True)"
# or backfill many systems:
python scripts/build_viewer_pdbs.py --systems-dir systems --force
```

### [`interface_selector.py`](interface_selector.py)
Pure selection logic — no file I/O. Identifies which atoms to keep for analysis.

- **Interface residues**: Residues within a distance cutoff of the partner chain
- **Bridging waters**: Water molecules within cutoff of *both* chains
- **Interface metals**: Metal ions bridging both chains (same criteria as waters)

Uses MDAnalysis distance arrays for efficient computation across all atom pairs.

### [`interface_patches.py`](interface_patches.py)
Detects interface patches: connected components of residues across two interacting chains, where connectivity is established via direct inter-chain residue-residue contacts.

**Algorithm:**
1. Count how many frames each direct A–B residue pair interacts in
2. Write one compact edge catalogue containing pairs with `count / total_frames ≥ 50%`
3. In the frontend, filter those edges at 50, 60, 70, 80, 90, or 100% conservation
4. Extract connected components of at least 3 residues at the selected threshold — these are the interface patches; an isolated residue pair is excluded
5. Cache all six frontend patch topologies; the default threshold is 70%

The generated `_interface_patches.json` is a threshold-independent graph catalogue. It contains residue endpoints, frame counts, conservation values, and frame metadata; no CSV format is changed.

**Standalone CLI:**
```bash
python interface_patches.py systems/1ULL --threshold 0.80 --min-size 3
```

### [`aggregate_csv.py`](aggregate_csv.py)
Combines per-frame CoCoMaps output into system-level files:

| Output File | Content |
|-------------|---------|
| `_interactions.csv` | One row per residue pair per frame, with normalized interaction types |
| `_area.csv` | Buried surface area (BSA) per frame: total, polar, non-polar |
| `_trends.csv` | Interaction type counts per frame (H-bonds, salt bridges, π-π, etc.) |
| `_atom_pairs.csv` | Atom-level detail: specific atoms, distances, angles per interaction |
| `_water_mediated.csv` | All frames: CoCoMaps Water_Mediated rows + `frame` (Water Identity column for viewer) |
| `_metal_mediated.csv` | All frames: CoCoMaps Metal_Mediated rows + `frame` (Metal Identity) |
| `_metadata.json` | Frame count, chain pattern, and auto-generated job ID with expiry |

Handles 17+ interaction types with a normalization layer to map various CoCoMaps labels to canonical names.

### [`job_id.py`](job_id.py)
Generates unique job identifiers in the format `YYYYDDD-RRRRRRRR` (year + day-of-year + 8 random alphanumeric characters). Manages creation timestamps and 60-day expiry for metadata.

## Pipeline Flow

```
Input PDB
    │
    ▼
process_frames()          Split into frame_1/, frame_2/, ...
    │                     Select interface atoms per frame
    ▼
create_input_jsons()      Write CoCoMaps config for each frame
    │
    ▼
run_cocomaps_analysis()   Docker: CoCoMaps on each frame → CSVs
    │
    ▼
run_interface_patches()   Graph analysis → _interface_patches.json
    │
    ▼
aggregate_system()        Combine all frames → system-level CSVs
    │
    ▼ (web upload only)
write_viewer_frame_pdb()  viewer.pdb for Mol*
    │
    ▼ (web upload only)
remove input.pdb           Drop copied raw trajectory after viewer.pdb exists
```

## Configuration

Settings are loaded from a `.env` file in the project root:

| Variable | Default | Description |
|----------|---------|-------------|
| `COCOMAPS_USE_REDUCE` | `false` | Add hydrogens before analysis |
| `COCOMAPS_IMAGE_REDUCE` | `andrpet/cocomaps-backend:0.0.19` | Docker image (with reduce) |
| `COCOMAPS_IMAGE_NO_REDUCE` | `sattamaltwaim/cocomaps-backend:no-reduce` | Docker image (without reduce) |
| `DEFAULT_INTERFACE_CUTOFF` | `5.0` | Distance cutoff in Ångströms |
| `DEFAULT_CHAINS` | `A,B` | Chain IDs to analyze |
| `SELECT_INTERFACE` | `true` | Enable interface selection |

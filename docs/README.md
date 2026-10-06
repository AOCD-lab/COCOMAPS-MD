# Mol* Viewer PDB Generation

This README explains only the PDB file that is shown in Mol*: the
`viewer.pdb` written by [`engine/viewer_pdb.py`](../engine/viewer_pdb.py) after
a web upload finishes analysis.

The product is intentionally simple:

```text
systems/<system_id>/viewer.pdb
```

It is the first selected frame from the original uploaded trajectory, with
non-solvent/non-ion structure limited to the user-selected chains, and only
interface waters/metals/simple ions retained.

## Desired Viewer Structure

Given user-selected chains such as `A` and `B`, Mol* should receive:

- The first processed frame, selected from the original uploaded trajectory.
- The two user-selected chains.
- DNA/RNA residues, ligands, cofactors, and other non-solvent residues only
  when they belong to one of the selected chains.
- Waters, metals, and simple ions only if they are within `5.0` Angstroms of
  both selected chains.

Mol* should not receive:

- Unselected third/fourth/etc. chains.
- Waters farther than `5.0` Angstroms from either selected chain.
- Metals farther than `5.0` Angstroms from either selected chain.
- Simple ions farther than `5.0` Angstroms from either selected chain.
- Any trajectory frame except the first selected/processed one.

In other words: keep the selected-chain first-frame structure, but remove
unselected chains and bulk solvent/ions that are not close to the
user-selected interface.

## Where It Runs

The web upload worker calls `write_viewer_frame_pdb()` in
[`backend/routes/upload.py`](../backend/routes/upload.py), after
`engine.run_pipeline()` succeeds:

```python
write_viewer_frame_pdb(
    system_dir,
    chain_a=chain1,
    chain_b=chain2,
    start_frame=start_frame,
    end_frame=end_frame if end_frame != -1 else -1,
    frame_step=frame_step,
    verbose=False,
)
```

`chain1` and `chain2` are the chains the user selected in the upload form.

The default viewer solvent cutoff is:

```python
DEFAULT_VIEWER_SOLVENT_CUTOFF = 5.0
```

The CLI does not automatically run this step unless a caller invokes
`write_viewer_frame_pdb()` manually.

## Required Inputs

The writer expects a completed system directory with:

```text
systems/<system_id>/
  <original_uploaded_name>.pdb
  _interactions.csv
```

`_interactions.csv` is used as a completion gate. The writer does not need to
read interaction rows for the current viewer filtering behavior, but if the file
is missing, it assumes the system is not ready and skips writing `viewer.pdb`.

The original uploaded PDB is required because the viewer structure is based on
the original first selected frame, not on the interface-trimmed `frame_1.pdb`.

## Choosing the Frame

The writer reads the original uploaded PDB copied into the system root and
splits it into raw frames using the same rules as frame processing:

1. Prefer `MODEL` / `ENDMDL` blocks.
2. If no `MODEL` blocks exist, split by `END` records.

Then it applies the same upload frame interval:

```python
end = end_frame if end_frame != -1 and end_frame <= num_frames else num_frames
start_frame = max(start_frame, 0)
frame_step = max(frame_step, 1)
frames_to_process = list(range(start_frame, end, frame_step))
first_raw_idx = frames_to_process[0]
raw_text = raw_frames[first_raw_idx]
```

Important details:

- `start_frame` is zero-based by the time it reaches `viewer_pdb.py`.
- `end_frame == -1` means all frames.
- `frame_step` is the sampling interval.
- `viewer.pdb` uses only `frames_to_process[0]`.

Example:

```text
Original trajectory: 100 frames
User interval: start frame 21, step 5
Backend start_frame: 20
frames_to_process: [20, 25, 30, ...]
viewer.pdb source frame: original trajectory frame 21
```

The generated `frame_1/frame_1.pdb` from analysis also corresponds to that same
first selected raw frame, but `viewer.pdb` is built from the original raw frame
copy so all non-solvent context remains present.

## Residues Subject to Removal

Only these residue classes are candidates for removal:

### Waters

```text
HOH, H2O, WAT, TIP, TIP3, TIP4, T3P, TP3, SOL, SPC, DOD, OH2
```

### Metals

Metals come from `METALS` in
[`engine/interface_selector.py`](../engine/interface_selector.py), normalized
to uppercase. This includes names such as:

```text
NA, MG, CA, MN, FE, CO, NI, CU, ZN
```

### Simple Ions

```text
CL, CL-, CLA, IOD, I, BR, F, SOD, POT, NA+
```

Every other residue type is kept without a distance check only if it belongs to
one of the selected chains. Non-solvent residues on unselected chains are
discarded from the viewer structure.

## Distance Reference

The writer loads the selected raw frame into MDAnalysis:

```python
universe = mda.Universe(tmp_path)
```

It then builds reference coordinates for the two selected chains:

```python
_selected_chain_reference_positions(universe, chain_a, chain_b)
```

The reference selection uses this priority:

1. Heavy atoms from non-water/non-metal/non-simple-ion residues in `chain_a` and
   `chain_b`.
2. If there are no heavy atoms, all non-water/non-metal/non-simple-ion atoms in
   `chain_a` and `chain_b`.
3. If there are still no atoms, all atoms in `chain_a` and `chain_b`.

This avoids a water or ion with chain ID `A` or `B` counting as part of the
selected chain reference.

The chain identifier is read from PDB `chainID`; if that is blank, the code
falls back to MDAnalysis `segid`.

## Keep-or-Remove Rule

For each residue in the original first selected frame:

```python
if residue is not water/metal/simple ion:
    keep it
else:
    keep it only if it is within 5.0 Angstroms of chain_a
    AND within 5.0 Angstroms of chain_b
```

The implementation checks squared Euclidean distances for the candidate residue
against each selected chain's reference positions. Waters use oxygen atoms when
available; other removable residues use their atom positions.

The practical rule is:

```text
remove candidate residue only when:
  distance(candidate, chain_a) > 5.0
  OR
  distance(candidate, chain_b) > 5.0
```

So a water, ion, or metal is kept only if it is close to both selected chains,
matching the pipeline's bridging-water/interface-metal behavior.

## Writing `viewer.pdb`

The writer accumulates whole MDAnalysis residue atom groups in original residue
order:

```python
groups = []
for residue in universe.residues:
    if removable residue and not within cutoff:
        continue
    groups.append(residue.atoms)
```

Then it combines those groups and writes:

```python
out_path = system_path / "viewer.pdb"
combined.write(str(out_path))
```

The output is therefore:

```text
first selected original frame
selected-chain non-solvent residues
plus waters/metals/simple ions within 5.0 Angstroms of both selected chains
```

## Skip Conditions

`write_viewer_frame_pdb()` returns `False` without writing `viewer.pdb` when:

- `_interactions.csv` is missing.
- No original root-level PDB can be found.
- The original PDB cannot be split into any frames.
- The upload frame interval produces no selected frames.
- No atoms are found for the selected chains.
- No residue groups remain after filtering.

The upload worker catches exceptions from this step and logs a warning instead
of failing the entire analysis job.

## How Mol* Receives It

Mol* does not call `viewer_pdb.py` directly.

1. The upload worker writes:

   ```text
   systems/<system_id>/viewer.pdb
   ```

2. `MolStarViewer.vue` fetches:

   ```text
   /api/analysis/<jobId>/frame/1/pdb
   ```

3. `backend/routes/data.py` serves `viewer.pdb` for frame 1 when it exists:

   ```python
   if frame_num == 1 and (system_path / "viewer.pdb").exists():
       pdb_file = system_path / "viewer.pdb"
   ```

4. `MolStarViewer.vue` passes the PDB text into Mol*:

   ```javascript
   const data = await plugin.builders.data.rawData({ data: pdbText })
   const trajectory = await plugin.builders.structure.parseTrajectory(data, 'pdb')
   const model = await plugin.builders.structure.createModel(trajectory)
   const structure = await plugin.builders.structure.createStructure(model)
   ```

5. Mol* renders polymer as cartoon, ligand as ball-and-stick, and water as
   ball-and-stick with lower opacity.

## Current Main Path

The active writer path uses:

- `_find_original_pdb()`
- `_parse_raw_frames()`
- `_selected_chain_reference_positions()`
- `_is_viewer_filtered_residue()`
- `_residue_within_cutoff()`
- MDAnalysis residue-group writing

Older mediated-identity helper functions still exist in `viewer_pdb.py`, but
`write_viewer_frame_pdb()` no longer uses them for the viewer output.

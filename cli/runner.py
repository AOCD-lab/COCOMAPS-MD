"""
Analysis pipeline runner with rich progress bars.
"""
import os
import sys
import json
import time
import shutil
import subprocess
from pathlib import Path

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel

from cli.constants import DEFAULT_COCOMAPS_PARAMS
from cli.frame_io import scan_frames, iter_selected_frames, raw_frame_file

console = Console()

# Prefer the runtime shipped inside the publishable CLI folder. The repository
# root fallback keeps editable development checkouts backwards compatible.
_CLI_DIR = Path(__file__).resolve().parent
_BUNDLED_RUNTIME = _CLI_DIR / '_runtime'
_RUNTIME_ROOT = _BUNDLED_RUNTIME if _BUNDLED_RUNTIME.is_dir() else _CLI_DIR.parent
if str(_RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(_RUNTIME_ROOT))

COCOMAPS_DIR = _RUNTIME_ROOT / 'cocomaps'
_STUBS_DIR = str(_RUNTIME_ROOT / 'stubs')
os.environ.setdefault('COCOMAPS_DEPS_DIR', str(_RUNTIME_ROOT / 'deps'))


def _naccess_succeeded(frame_path: str | Path, process_output: str = '') -> bool:
    """Return whether the current CoCoMaps frame produced an NACCESS summary."""
    if '[WARNING] Naccess error:' in process_output:
        return False
    output_root = Path(frame_path) / 'naccess_outputs'
    return any(output_root.glob('**/Rsa_stats.csv'))



def run_pipeline(
    pdb_file: str,
    output_dir: str,
    chain_a: str = 'A',
    chain_b: str = 'B',
    start_frame: int = 0,
    end_frame: int = -1,
    frame_step: int = 1,
    use_reduce: bool = False,
    select_interface: bool = True,
    interface_cutoff: float = 5.0,
    water_cutoff: float = 5.0,
    cocomaps_params: dict | None = None,
) -> str:
    """
    Run the full analysis pipeline with rich progress bars.

    Returns the output directory path.
    """
    if cocomaps_params is None:
        cocomaps_params = dict(DEFAULT_COCOMAPS_PARAMS)

    chains = [chain_a, chain_b]
    overall_start = time.time()

    console.print()
    console.print(Panel(
        "[bold]Starting PDB Analysis Pipeline[/bold]",
        title="Pipeline",
        border_style="green",
    ))

    # ──────────────────────────────────────────────────────────────────────
    # STEP 1: Split / process frames
    # ──────────────────────────────────────────────────────────────────────
    console.print("\n[bold cyan]STEP 1/5[/bold cyan] — Splitting PDB into frames …")

    # Count without retaining the trajectory; stream the same raw frame text.
    frame_mode, total_frames_raw = scan_frames(pdb_file)

    # ── Validate chains exist in the first frame ──
    if total_frames_raw > 0:
        import tempfile as _tmpmod
        import MDAnalysis as _mda_chk
        _tmp_chk = _tmpmod.NamedTemporaryFile(suffix='.pdb', delete=False, mode='w')
        first_frames = iter_selected_frames(pdb_file, frame_mode, 0, 1, 1)
        try:
            first_frame = next(first_frames)
        finally:
            first_frames.close()
        _tmp_chk.write(first_frame)
        if not first_frame.rstrip().endswith('END'):
            _tmp_chk.write('END\n')
        _tmp_chk.close()
        _chk_u = _mda_chk.Universe(_tmp_chk.name)
        _detected = sorted(set(_chk_u.atoms.chainIDs))
        if not _detected or _detected == ['']:
            _detected = sorted(set(_chk_u.atoms.segids))
        _chk_u.trajectory.close()
        del _chk_u
        os.unlink(_tmp_chk.name)

        missing = [c for c in (chain_a, chain_b) if c not in _detected]
        if missing:
            chain_list = ", ".join(_detected) if _detected else "none detected"
            console.print(
                f"\n[red]Error: chain{'s' if len(missing) > 1 else ''} "
                f"{', '.join(repr(c) for c in missing)} not found in PDB.[/red]"
            )
            console.print(f"  Available chains: [bold]{chain_list}[/bold]")
            raise SystemExit(1)

    # Determine slice
    if end_frame == -1 or end_frame > total_frames_raw:
        end_frame = total_frames_raw
    if start_frame < 0:
        start_frame = 0
    frame_step = max(1, frame_step)

    frames_to_process = range(start_frame, end_frame, frame_step)
    num_frames = len(frames_to_process)

    os.makedirs(output_dir, exist_ok=True)

    # Optionally copy original PDB
    original_name = Path(pdb_file).name
    dest = os.path.join(output_dir, original_name)
    if not os.path.exists(dest):
        shutil.copy(pdb_file, dest)

    # Rename waters helper
    from engine import rename_waters_to_hoh

    import MDAnalysis as mda

    # Keep one pipeline progress display alive across all five stages. Frame
    # work gets a child bar; indivisible stages retain a spinner and elapsed
    # time without claiming a made-up percentage.
    pipeline_progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        console=console,
    )
    pipeline_progress.start()
    pipeline_task = pipeline_progress.add_task("Pipeline stages", total=5)
    frame_task = pipeline_progress.add_task("Splitting frames", total=num_frames)
    for idx, raw_text in enumerate(iter_selected_frames(
        pdb_file, frame_mode, start_frame, end_frame, frame_step
    )):
        output_frame_num = idx + 1
        frame_folder = os.path.join(output_dir, f"frame_{output_frame_num}")
        os.makedirs(frame_folder, exist_ok=True)
        frame_file = os.path.join(frame_folder, f"frame_{output_frame_num}.pdb")

        # Use local temporary storage; selections and PDB writing are unchanged.
        with raw_frame_file(raw_text) as tmp_frame:
            u = mda.Universe(tmp_frame)
            try:
                if select_interface:
                    from engine import get_atom_selections, select_interface_atoms
                    selections = get_atom_selections(u, chain_a, chain_b)
                    result = select_interface_atoms(
                        u, selections, chain_a, chain_b, interface_cutoff, water_cutoff
                    )
                    output_atoms = result['atoms']
                else:
                    output_atoms = u.atoms

                rename_waters_to_hoh(output_atoms)

                if len(output_atoms) > 0:
                    output_atoms.write(frame_file)
                else:
                    with open(frame_file, 'w') as f:
                        f.write("REMARK   Empty frame - no interface atoms found\nEND\n")
            finally:
                u.trajectory.close()

        pipeline_progress.update(frame_task, advance=1)

    pipeline_progress.remove_task(frame_task)
    pipeline_progress.update(
        pipeline_task,
        advance=1,
        description="Pipeline stages — frame splitting complete",
    )
    console.print(f"  [green]✓[/green] Split into {num_frames} frames")

    # ──────────────────────────────────────────────────────────────────────
    # STEP 2: Create input JSON files (with merged CoCoMaps params)
    # ──────────────────────────────────────────────────────────────────────
    console.print("\n[bold cyan]STEP 2/5[/bold cyan] — Creating CoCoMaps input files …")

    input_file_name = os.environ.get("INPUT_FILE_NAME", "example_input.json")

    for i in range(1, num_frames + 1):
        frame_folder = os.path.join(output_dir, f"frame_{i}")
        pdb_path = os.path.abspath(os.path.join(frame_folder, f"frame_{i}.pdb"))
        json_data = {
            "pdb_file": pdb_path,
            "REDUCE_BOOL": use_reduce,
            "chains_set_1": [chain_a],
            "chains_set_2": [chain_b],
            "ranges_1": [[0, 100000]],
            "ranges_2": [[0, 100000], [0, 100000]],
            **cocomaps_params,
        }

        json_path = os.path.join(frame_folder, input_file_name)
        with open(json_path, 'w') as f:
            json.dump(json_data, f, indent=4)

    console.print(f"  [green]✓[/green] Created {num_frames} input JSON files")
    pipeline_progress.update(
        pipeline_task, advance=1, description="Pipeline stages — inputs prepared"
    )

    # ──────────────────────────────────────────────────────────────────────
    # STEP 3: Run CoCoMaps locally on each frame
    # ──────────────────────────────────────────────────────────────────────
    console.print("\n[bold cyan]STEP 3/5[/bold cyan] — Running CoCoMaps analysis …")

    begin_py = str(COCOMAPS_DIR / 'begin.py')
    successful = 0
    failed = 0
    naccess_failed = []

    frame_task = pipeline_progress.add_task("Analyzing frames", total=num_frames)
    for i in range(1, num_frames + 1):
        pipeline_progress.update(
            frame_task, description=f"Analyzing frame {i}/{num_frames}"
        )
        frame_folder = f"frame_{i}"
        frame_path = os.path.join(output_dir, frame_folder)
        input_json = os.path.abspath(os.path.join(frame_path, input_file_name))

        command = [sys.executable, begin_py, input_json]
        env = os.environ.copy()
        env['PYTHONPATH'] = _STUBS_DIR + os.pathsep + env.get('PYTHONPATH', '')

        from engine.analyze_pdb import _ensure_hbplus_stub
        _ensure_hbplus_stub(frame_path, frame_folder)

        try:
            result = subprocess.run(
                command, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                cwd=frame_path, env=env,
            )
            from engine.cocomaps_chain_csv import remap_frame_distance_outputs

            remap_frame_distance_outputs(Path(frame_path), chain_a, chain_b)
            if _naccess_succeeded(frame_path, result.stdout or ''):
                successful += 1
            else:
                failed += 1
                naccess_failed.append(i)
                console.print(
                    f"  [red]✗[/red] Frame {i}: NACCESS did not produce surface-area results"
                )

        except subprocess.CalledProcessError as e:
            failed += 1
            console.print(f"  [red]✗[/red] Frame {i} failed: {(e.output or '')[:100]}")

        pipeline_progress.update(frame_task, advance=1)

    pipeline_progress.remove_task(frame_task)
    pipeline_progress.update(
        pipeline_task,
        advance=1,
        description="Pipeline stages — frame analysis complete",
    )
    console.print(f"  [green]✓[/green] CoCoMaps: {successful}/{num_frames} successful, {failed} failed")

    if naccess_failed:
        frames = ', '.join(str(frame) for frame in naccess_failed)
        console.print(Panel(
            "[bold red]NACCESS failed; area charts were not generated.[/bold red]\n"
            f"Affected frame(s): {frames}\n"
            "If you use Docker, pull or rebuild the latest image for linux/amd64.",
            title="Surface-area analysis failed",
            border_style="red",
        ))
        pipeline_progress.stop()
        raise SystemExit(1)

    # ──────────────────────────────────────────────────────────────────────
    # STEP 4: Interface patch analysis
    # ──────────────────────────────────────────────────────────────────────
    console.print("\n[bold cyan]STEP 4/5[/bold cyan] — Running interface patch analysis …")

    try:
        pipeline_progress.update(pipeline_task, description="Pipeline stages — analyzing interface patches")
        from engine import run_interface_patches
        run_interface_patches(
            output_dir,
            min_consistency=0.70,
            min_interface_patch_size=3,
            verbose=False,
        )
        console.print("  [green]✓[/green] Interface patch analysis complete")
    except Exception as e:
        console.print(f"  [yellow]Warning: Interface patches failed: {e}[/yellow]")
    pipeline_progress.update(pipeline_task, advance=1)

    # ──────────────────────────────────────────────────────────────────────
    # STEP 5: Aggregate CSV files
    # ──────────────────────────────────────────────────────────────────────
    console.print("\n[bold cyan]STEP 5/5[/bold cyan] — Aggregating system CSV files …")

    try:
        pipeline_progress.update(pipeline_task, description="Pipeline stages — aggregating results")
        from engine import aggregate_system
        aggregate_system(output_dir, verbose=False)
        console.print("  [green]✓[/green] CSV aggregation complete")
    except Exception as e:
        console.print(f"  [yellow]Warning: Aggregation failed: {e}[/yellow]")
    pipeline_progress.update(pipeline_task, advance=1, description="Pipeline stages complete")

    pipeline_progress.stop()

    # Build the same cleaned first-frame structure served to Mol* by the web
    # application. Keep it in the standalone CLI result for snapshot export.
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=True,
    ) as status_progress:
        status_progress.add_task("Preparing cleaned Mol* structure", total=None)
        try:
            from engine.viewer_pdb import write_viewer_frame_pdb
            if write_viewer_frame_pdb(
                output_dir,
                chain_a=chain_a,
                chain_b=chain_b,
                start_frame=start_frame,
                end_frame=end_frame,
                frame_step=frame_step,
                verbose=False,
            ):
                console.print("  [green]✓[/green] Cleaned Mol* first frame written")
            else:
                console.print("  [yellow]Warning: Cleaned Mol* first frame was not written[/yellow]")
        except Exception as e:
            console.print(f"  [yellow]Warning: Mol* viewer PDB failed: {e}[/yellow]")

    # ── Summary ──
    total_time = time.time() - overall_start
    console.print()
    console.print(Panel(
        f"[bold green]Pipeline complete![/bold green]\n"
        f"Total time: {total_time:.1f}s ({total_time / 60:.1f} min)\n"
        f"Frames analyzed: {successful}/{num_frames}\n"
        f"Output: {output_dir}",
        title="Complete",
        border_style="green",
    ))

    return output_dir

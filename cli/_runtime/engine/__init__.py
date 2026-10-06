"""
PDB analysis engine — frame processing, CoCoMaps orchestration, interface patches, aggregation.

Public API for CLI and backend:
  - run_pipeline, process_frames, rename_waters_to_hoh, create_input_jsons, run_cocomaps_analysis
  - job_id: generate_job_id, ensure_job_fields, isoformat_utc
  - interface_selector: get_atom_selections, select_interface_atoms, get_selection_summary
  - interface_patches: run_interface_patches, count_interface_patches
  - aggregate_csv: aggregate_system
"""
from engine.job_id import generate_job_id, ensure_job_fields, isoformat_utc

__all__ = [
    "run_pipeline",
    "process_frames",
    "rename_waters_to_hoh",
    "create_input_jsons",
    "run_cocomaps_analysis",
    "generate_job_id",
    "ensure_job_fields",
    "isoformat_utc",
    "get_atom_selections",
    "select_interface_atoms",
    "get_selection_summary",
    "run_interface_patches",
    "count_interface_patches",
    "aggregate_system",
]


def __getattr__(name):
    if name in ("run_pipeline", "process_frames", "rename_waters_to_hoh", "create_input_jsons", "run_cocomaps_analysis"):
        from engine.analyze_pdb import (
            run_pipeline,
            process_frames,
            rename_waters_to_hoh,
            create_input_jsons,
            run_cocomaps_analysis,
        )
        return locals()[name]
    if name in ("get_atom_selections", "select_interface_atoms", "get_selection_summary"):
        from engine.interface_selector import (
            get_atom_selections,
            select_interface_atoms,
            get_selection_summary,
        )
        return locals()[name]
    if name in ("run_interface_patches", "count_interface_patches"):
        from engine.interface_patches import run_interface_patches, count_interface_patches
        return locals()[name]
    if name == "aggregate_system":
        from engine.aggregate_csv import aggregate_system
        return aggregate_system
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

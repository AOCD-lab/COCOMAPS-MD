"""Filesystem path helpers for system directories."""
import json
from pathlib import Path


def get_systems_dir(app) -> Path:
    """Return the configured systems directory."""
    data_folder = app.config.get("DATA_FOLDER") or app.config["UPLOAD_FOLDER"]
    return Path(data_folder) / "systems"


def get_system_path(app, system_id) -> Path | None:
    """
    Resolve a user-provided system ID to a safe systems/<id> child path.

    System IDs are directory names, not paths. Reject hidden names, empty names,
    path separators, and anything that resolves outside the systems directory.
    """
    if not isinstance(system_id, str):
        return None
    name = system_id.strip()
    if not name or name.startswith(".") or "/" in name or "\\" in name:
        return None

    systems_dir = get_systems_dir(app).resolve()
    candidate = (systems_dir / name).resolve()
    if candidate.parent != systems_dir:
        return None
    return candidate


def is_example_system_path(system_path: Path) -> bool:
    """Return True when a system directory is explicitly marked as a public example."""
    meta = system_path / "_metadata.json"
    if not meta.is_file():
        return False
    try:
        with open(meta, "r", encoding="utf-8") as f:
            data = json.load(f)
        return bool(data.get("isExample"))
    except (OSError, json.JSONDecodeError, AttributeError):
        return False


def get_system_path_for_job_id(app, job_id) -> Path | None:
    """
    Resolve a public, shareable analysis job ID to its system directory.

    Job IDs are capabilities: knowing one is enough to view that analysis, but
    callers should not be able to enumerate uploaded system directories.
    """
    if not isinstance(job_id, str):
        return None
    value = job_id.strip()
    if not value or "/" in value or "\\" in value or value.startswith("."):
        return None

    systems_dir = get_systems_dir(app).resolve()
    if not systems_dir.is_dir():
        return None

    matches = []

    for child in sorted(systems_dir.iterdir(), key=lambda path: path.name):
        if not child.is_dir() or child.name.startswith(".") or child.name.startswith("__"):
            continue
        meta = child / "_metadata.json"
        if not meta.is_file():
            continue
        try:
            with open(meta, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("jobId") == value:
            matches.append(child)

    if not matches:
        return None

    matches.sort(key=lambda child: (not is_example_system_path(child), child.name))
    return matches[0]

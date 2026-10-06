"""
Routes for system management
"""
from flask import Blueprint, jsonify, current_app
import os
import re
from datetime import datetime
import json

from backend.system_paths import (
    get_system_path,
    get_system_path_for_job_id,
    get_systems_dir,
    is_example_system_path,
)

bp = Blueprint('systems', __name__)


def _get_chain_pattern(frame_folder):
    """
    Detect the chain pattern (e.g., 'A_B', 'A_C') from CSV files in frame folder.
    Returns tuple (chain1, chain2) or ('A', 'B') as default fallback.
    """
    pattern = re.compile(r'\.pd[b_h\.]*_([A-Z])_([A-Z])_final_file\.csv$')
    for f in frame_folder.iterdir():
        if f.is_file():
            match = pattern.search(f.name)
            if match:
                return (match.group(1), match.group(2))
    return ("A", "B")  # fallback default


def _get_display_name(system_path, default_name):
    """Get display name from metadata file if it exists"""
    metadata_file = system_path / '.metadata.json'
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r') as f:
                metadata = json.load(f)
                return metadata.get('displayName', default_name)
        except:
            pass
    return default_name


def _get_frame_count_from_metadata(system_path, fallback_count):
    """Get totalFrames from _metadata.json when it exists, else return fallback (from frame folder count)."""
    meta = system_path / '_metadata.json'
    if meta.exists():
        try:
            with open(meta, 'r', encoding='utf-8') as f:
                data = json.load(f)
            tf = data.get('totalFrames')
            if tf is not None and isinstance(tf, (int, float)) and tf > 0:
                return int(tf)
        except Exception:
            pass
    return fallback_count


def _get_job_info_from_metadata(system_path):
    """
    Read job-related fields from _metadata.json when available.
    Returns dict with keys: jobId, jobCreatedAt, jobExpiresAt (values may be None).
    """
    meta = system_path / '_metadata.json'
    result = {
        'jobId': None,
        'jobCreatedAt': None,
        'jobExpiresAt': None,
    }
    if not meta.exists():
        return result

    try:
        with open(meta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, dict):
            result['jobId'] = data.get('jobId')
            result['jobCreatedAt'] = data.get('jobCreatedAt')
            result['jobExpiresAt'] = data.get('jobExpiresAt')
    except Exception:
        # Ignore metadata errors; job fields remain None.
        pass

    return result


def _get_chain_pattern_from_metadata(system_path):
    """Get chainPattern from _metadata.json as tuple (chain1, chain2), if available."""
    meta = system_path / '_metadata.json'
    if not meta.exists():
        return None

    try:
        with open(meta, 'r', encoding='utf-8') as f:
            data = json.load(f)
        chain_pattern = data.get('chainPattern') if isinstance(data, dict) else None
        if isinstance(chain_pattern, str):
            parts = [part.strip() for part in chain_pattern.split('_') if part.strip()]
            if len(parts) >= 2:
                return (parts[0], parts[1])
    except Exception:
        pass
    return None


def _is_example_system(system_path):
    """Check if a system is a bundled example (has isExample: true in _metadata.json)."""
    return is_example_system_path(system_path)


def _system_payload(system_path, public_id=None):
    """Build the public API representation for a system directory."""
    frame_folders = [f for f in system_path.iterdir() if f.is_dir() and f.name.startswith('frame_')]
    frame_count = _get_frame_count_from_metadata(system_path, len(frame_folders))

    chain1, chain2 = _get_chain_pattern_from_metadata(system_path) or ("A", "B")
    if frame_folders:
        first_frame = sorted(frame_folders, key=lambda f: f.name)[0]
        chain1, chain2 = _get_chain_pattern(first_frame)

    job_info = _get_job_info_from_metadata(system_path)
    system_id = public_id or system_path.name

    return {
        'id': system_id,
        'name': _get_display_name(system_path, system_path.name),
        'path': system_id,
        'frames': frame_count,
        'chain1': chain1,
        'chain2': chain2,
        'dateCreated': datetime.fromtimestamp(os.path.getmtime(system_path)).isoformat(),
        'status': 'ready',
        'jobId': job_info['jobId'],
        'jobCreatedAt': job_info['jobCreatedAt'],
        'jobExpiresAt': job_info['jobExpiresAt'],
        'isExample': _is_example_system(system_path),
    }


def _set_display_name(system_path, display_name, owner_email=None):
    """Set display name and optionally owner email in .metadata.json"""
    metadata_file = system_path / '.metadata.json'
    metadata = {}
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
        except Exception:
            pass
    metadata['displayName'] = display_name
    if owner_email is not None:
        metadata['ownerEmail'] = owner_email
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2)
        f.write('\n')


@bp.route('/systems', methods=['GET'])
def list_systems():
    """List all available systems"""
    try:
        systems_folder = get_systems_dir(current_app)
        
        # Check if systems folder exists
        if not systems_folder.exists():
            return jsonify([])
        
        systems = []
        
        for item in systems_folder.iterdir():
            if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('__'):
                if not _is_example_system(item):
                    continue
                systems.append(_system_payload(item))
        
        # Sort by name
        systems.sort(key=lambda x: x['name'])
        
        return jsonify(systems)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.route('/systems/<system_id>', methods=['GET'])
def get_system(system_id):
    """Get details for a specific system"""
    try:
        system_path = get_system_path(current_app, system_id)
        
        if (
            system_path is None
            or not system_path.exists()
            or not system_path.is_dir()
            or not _is_example_system(system_path)
        ):
            return jsonify({'error': 'System not found'}), 404

        return jsonify(_system_payload(system_path))
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@bp.route('/analysis/<job_id>', methods=['GET'])
def get_analysis_by_job_id(job_id):
    """Get a shareable, unlisted analysis by its public job ID."""
    try:
        system_path = get_system_path_for_job_id(current_app, job_id)
        if system_path is None or not system_path.exists() or not system_path.is_dir():
            return jsonify({'error': 'Analysis not found'}), 404
        return jsonify(_system_payload(system_path, public_id=job_id))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

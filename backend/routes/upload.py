"""
Routes for PDB file upload and processing
"""
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from pathlib import Path
import os
import queue
import shutil
import sys
import uuid
import json
import threading
from datetime import datetime
from distutils.util import strtobool

# Ensure project root is on path for engine package
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

bp = Blueprint('upload', __name__)

# In-memory cache of job statuses (also persisted to disk)
_jobs = {}
_jobs_source_path = None
_jobs_lock = threading.Lock()

ALLOWED_EXTENSIONS = {'pdb'}

MAX_WEB_FRAMES = 50
DEFAULT_JOB_WORKERS = 2
UNFINISHED_STATUSES = {'queued', 'processing', 'splitting', 'analyzing', 'resuming'}

# ---------------------------------------------------------------------------
# Persistent job helpers
# ---------------------------------------------------------------------------

def _jobs_file_path(app):
    """Return the path to the persistent .jobs.json file."""
    data_folder = app.config.get('DATA_FOLDER', app.config['UPLOAD_FOLDER'])
    systems_folder = os.path.join(data_folder, 'systems')
    os.makedirs(systems_folder, exist_ok=True)
    return os.path.join(systems_folder, '.jobs.json')


def _systems_folder(app):
    data_folder = app.config.get('DATA_FOLDER', app.config['UPLOAD_FOLDER'])
    systems_folder = os.path.join(data_folder, 'systems')
    os.makedirs(systems_folder, exist_ok=True)
    return systems_folder


def _queued_job_dir(app, job_id):
    return os.path.join(_systems_folder(app), '.queued', job_id)


def _queued_input_path(app, job_id):
    return os.path.join(_queued_job_dir(app, job_id), 'input.pdb')


def _system_dir(app, system_id):
    return os.path.join(_systems_folder(app), system_id)


def _load_jobs(app):
    """Load jobs from disk into memory (called once at startup)."""
    global _jobs, _jobs_source_path
    path = _jobs_file_path(app)
    if os.path.exists(path):
        try:
            with open(path, 'r') as f:
                _jobs = json.load(f)
        except Exception:
            _jobs = {}
    else:
        _jobs = {}
    _jobs_source_path = path


def _persist_jobs(app):
    """Atomically write the in-memory jobs dict to disk."""
    path = _jobs_file_path(app)
    temp_path = f"{path}.tmp-{uuid.uuid4().hex}"
    try:
        with open(temp_path, 'w') as f:
            json.dump(_jobs, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


def _update_job(app, job_id, **fields):
    """Update a job's fields and persist to disk."""
    with _jobs_lock:
        if job_id in _jobs:
            _jobs[job_id].update(fields)
            _persist_jobs(app)


def _public_job(job):
    """Return job state without private execution-only fields."""
    public = dict(job)
    public.pop('email', None)
    public.pop('system_id', None)
    return public


def _init_jobs_for_app(app):
    """Ensure jobs are loaded for this app (idempotent)."""
    with _jobs_lock:
        if _jobs_source_path != _jobs_file_path(app):
            _load_jobs(app)


def _safe_remove_job_input(app, job_id):
    shutil.rmtree(_queued_job_dir(app, job_id), ignore_errors=True)


def _safe_remove_partial_output(app, system_id):
    if not isinstance(system_id, str) or not system_id or '/' in system_id or '\\' in system_id:
        raise ValueError('Invalid system ID in queued job')
    systems_folder = Path(_systems_folder(app)).resolve()
    system_path = (systems_folder / system_id).resolve()
    if system_path.parent != systems_folder:
        raise ValueError('Invalid system output path in queued job')
    if system_path.exists():
        shutil.rmtree(system_path)


def _safe_remove_copied_input_pdb(app, system_id):
    """Remove the copied raw upload from a completed system directory."""
    if not isinstance(system_id, str) or not system_id or '/' in system_id or '\\' in system_id:
        raise ValueError('Invalid system ID in queued job')
    systems_folder = Path(_systems_folder(app)).resolve()
    system_path = (systems_folder / system_id).resolve()
    if system_path.parent != systems_folder:
        raise ValueError('Invalid system output path in queued job')

    input_path = system_path / 'input.pdb'
    if input_path.is_file() or input_path.is_symlink():
        input_path.unlink()
        return True
    return False


class AnalysisQueue:
    """Persistent FIFO dispatcher with a fixed number of worker threads."""

    def __init__(self, app, worker_count=DEFAULT_JOB_WORKERS, executor=None):
        self.app = app
        self.worker_count = max(1, int(worker_count))
        self.executor = executor or process_queued_job
        self.pending = queue.Queue()
        self._start_lock = threading.Lock()
        self._queued_ids = set()
        self._queued_ids_lock = threading.Lock()
        self._started = False
        self.workers = []

    def start(self):
        with self._start_lock:
            if self._started:
                return
            self._recover_unfinished_jobs()
            self._started = True
            for index in range(self.worker_count):
                worker = threading.Thread(
                    target=self._worker_loop,
                    name=f'analysis-worker-{index + 1}',
                    daemon=True,
                )
                worker.start()
                self.workers.append(worker)

    def enqueue(self, job_id):
        with self._queued_ids_lock:
            if job_id in self._queued_ids:
                return
            self._queued_ids.add(job_id)
        try:
            self.pending.put_nowait(job_id)
        except Exception:
            with self._queued_ids_lock:
                self._queued_ids.discard(job_id)
            raise

    def _worker_loop(self):
        while True:
            job_id = self.pending.get()
            try:
                _update_job(
                    self.app,
                    job_id,
                    status='processing',
                    step_label='Processing',
                    progress=0,
                )
                self.executor(self.app, job_id)
            except Exception as exc:
                try:
                    _update_job(
                        self.app,
                        job_id,
                        status='failed',
                        step_label='Failed',
                        error=str(exc),
                    )
                except Exception as persist_exc:
                    print(f"[jobs] Could not persist failure for {job_id}: {persist_exc}")
            finally:
                with self._queued_ids_lock:
                    self._queued_ids.discard(job_id)
                self.pending.task_done()

    def _recover_unfinished_jobs(self):
        _init_jobs_for_app(self.app)
        recovered = []
        with _jobs_lock:
            for job_id, job in sorted(
                _jobs.items(),
                key=lambda item: item[1].get('created_at', ''),
            ):
                if job.get('status') not in UNFINISHED_STATUSES:
                    continue
                input_path = _queued_input_path(self.app, job_id)
                if not os.path.isfile(input_path):
                    job.update(
                        status='failed',
                        step_label='Failed',
                        error='Queued input file is missing after backend restart.',
                    )
                    continue
                if job.get('status') != 'queued':
                    try:
                        _safe_remove_partial_output(self.app, job.get('system_id'))
                    except Exception as exc:
                        job.update(
                            status='failed',
                            step_label='Failed',
                            error=f'Could not safely retry interrupted job: {exc}',
                        )
                        continue
                job.update(status='queued', step_label='Queued', progress=0)
                job.pop('error', None)
                recovered.append(job_id)
            _persist_jobs(self.app)
        for job_id in recovered:
            self.enqueue(job_id)


def get_analysis_queue(app):
    """Return the single queue manager owned by this Flask app."""
    if hasattr(app, '_get_current_object'):
        app = app._get_current_object()
    manager = app.extensions.get('analysis_queue')
    if manager is None:
        worker_count = app.config.get(
            'JOB_WORKER_COUNT',
            os.environ.get('COCOMAPS_JOB_WORKERS', DEFAULT_JOB_WORKERS),
        )
        manager = AnalysisQueue(app, worker_count=worker_count)
        app.extensions['analysis_queue'] = manager
    if app.config.get('JOB_QUEUE_AUTOSTART', not app.testing):
        manager.start()
    return manager


# ---------------------------------------------------------------------------
# File helpers
# ---------------------------------------------------------------------------

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def count_pdb_frames(filepath):
    """Count frames in a PDB file using the same logic as CLI inspect_pdb.

    Counts MODEL records first; falls back to END records for files that
    delimit frames with END instead of MODEL/ENDMDL.
    """
    model_count = 0
    end_count = 0
    with open(filepath, 'r') as fh:
        for line in fh:
            rec = line[:6].strip()
            if rec == 'MODEL':
                model_count += 1
            elif rec == 'END':
                end_count += 1
    if model_count > 0:
        return model_count
    if end_count > 1:
        return end_count
    return 1


def compute_effective_frames(total_frames, start_frame, end_frame, frame_step):
    """Return the number of frames that will actually be processed."""
    eff_end = total_frames if (end_frame == -1 or end_frame > total_frames) else end_frame
    eff_start = max(0, start_frame)
    step = max(1, frame_step)
    return len(range(eff_start, eff_end, step))


def _notify_job_completed(email, job_name, analysis_job_id, expires_at):
    """Send the "results ready" email in a background thread (best-effort).

    SMTP can be slow or unreachable; running it off the worker thread keeps the
    analysis queue moving and guarantees a mail problem never changes job status.
    """
    if not email:
        return

    def _send():
        try:
            from backend.mailer import send_job_completed_email
            sent = send_job_completed_email(email, job_name, analysis_job_id, expires_at)
            print(f"[jobs] Completion email {'sent' if sent else 'not sent'} for {analysis_job_id}")
        except Exception as mail_err:
            print(f"[jobs] Warning: completion email failed for {analysis_job_id}: {mail_err}")

    threading.Thread(target=_send, name='completion-email', daemon=True).start()


def process_queued_job(app, job_id):
    """Execute one persisted queue record and remove its staged input afterward."""
    with app.app_context():
        try:
            with _jobs_lock:
                job = dict(_jobs[job_id])

            pdb_file = _queued_input_path(app, job_id)
            pdb_name = job['pdb_name']
            system_dir = _system_dir(app, job['system_id'])
            use_reduce = bool(job.get('reduce', False))
            chain1 = job.get('chain1', 'A')
            chain2 = job.get('chain2', 'B')
            interface_cutoff = float(job.get('interface_cutoff', 5.0))
            start_frame = int(job.get('start_frame', 0))
            end_frame = int(job.get('end_frame', -1))
            frame_step = int(job.get('frame_step', 1))
            job_name = job.get('job_name')
            email = job.get('email')

            # Run the full pipeline (engine package)
            from engine import run_pipeline

            def progress_callback(step_label, progress):
                _update_job(app, job_id, step_label=step_label, progress=progress)

            frame_count, error = run_pipeline(
                pdb_file,
                system_dir,
                chain_a=chain1,
                chain_b=chain2,
                interface_cutoff=interface_cutoff,
                water_cutoff=interface_cutoff,
                use_reduce=use_reduce,
                start_frame=start_frame,
                end_frame=end_frame if end_frame != -1 else -1,
                frame_step=frame_step,
                progress_callback=progress_callback,
                verbose=False,
            )

            if error:
                _update_job(app, job_id, status='failed', step_label='Failed', error=error)
                return

            _update_job(app, job_id, frames=frame_count)

            # Mol* viewer: full first selected frame, dropping waters/metals/simple ions
            # that are not within 5 Angstroms of both user-selected chains.
            try:
                from engine.viewer_pdb import write_viewer_frame_pdb
                write_viewer_frame_pdb(
                    system_dir,
                    chain_a=chain1,
                    chain_b=chain2,
                    start_frame=start_frame,
                    end_frame=end_frame if end_frame != -1 else -1,
                    frame_step=frame_step,
                    verbose=False,
                )
            except Exception as viewer_err:
                print(f"[jobs] Warning: viewer PDB not written: {viewer_err}")

            # Frame folders no longer needed after aggregation + viewer PDB
            try:
                from engine.analyze_pdb import cleanup_frame_folders
                cleanup_frame_folders(system_dir, verbose=False)
            except Exception as cleanup_err:
                print(f"[jobs] Warning: frame cleanup failed: {cleanup_err}")

            # The raw uploaded trajectory can be very large. After viewer.pdb is
            # available, the frontend only needs aggregate outputs + viewer.pdb.
            if os.path.isfile(os.path.join(system_dir, 'viewer.pdb')):
                try:
                    _safe_remove_copied_input_pdb(app, job['system_id'])
                except Exception as input_cleanup_err:
                    print(f"[jobs] Warning: raw input PDB cleanup failed: {input_cleanup_err}")
            else:
                print("[jobs] Warning: viewer.pdb missing; keeping raw input PDB for recovery")

            # Attach public analysis jobId (from _metadata.json) so frontend can link to /analysis/<jobId>
            analysis_job_id = None
            expires_at = None
            metadata_path = os.path.join(system_dir, '_metadata.json')
            if os.path.isfile(metadata_path):
                try:
                    with open(metadata_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    analysis_job_id = meta.get('jobId') if isinstance(meta.get('jobId'), str) else None
                    expires_at = meta.get('jobExpiresAt') if isinstance(meta.get('jobExpiresAt'), str) else None
                except Exception:
                    pass

            # Write user-facing metadata (display name, email) to .metadata.json
            display_name = job_name if (job_name and job_name.strip()) else pdb_name
            try:
                from backend.routes.systems import _set_display_name
                _set_display_name(Path(system_dir), display_name, owner_email=email or None)
            except Exception as meta_err:
                print(f"[jobs] Warning: could not write .metadata.json: {meta_err}")

            # Done! Store public jobId so API and frontend use it as the canonical link.
            _update_job(app, job_id,
                        status='completed',
                        progress=100,
                        step_label='Completed',
                        analysis_job_id=analysis_job_id)

            # Optional notification with the link to the results. Only sent once the
            # job is persisted as completed, so the link is guaranteed to work.
            _notify_job_completed(email, display_name, analysis_job_id, expires_at)

        except Exception as e:
            _update_job(app, job_id,
                        status='failed',
                        step_label='Failed',
                        error=str(e))
        finally:
            _safe_remove_job_input(app, job_id)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

def _service_unavailable(message='Server is temporarily unable to queue this job. Please retry.'):
    response = jsonify({'error': message})
    response.status_code = 503
    response.headers['Retry-After'] = '5'
    return response


@bp.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type. Only PDB files allowed'}), 400

    job_id = str(uuid.uuid4())
    staged = False
    try:
        filename = secure_filename(file.filename)
        pdb_name = Path(filename).stem

        # Stage accepted uploads on the persistent systems volume so queued jobs
        # survive backend/container restarts.
        queued_dir = _queued_job_dir(current_app, job_id)
        filepath = _queued_input_path(current_app, job_id)
        os.makedirs(queued_dir, exist_ok=False)
        staged = True
        file.save(filepath)

        file_size = os.path.getsize(filepath)

        # Reject empty uploads (avoids "No frames to process" from empty temp file)
        if file_size == 0:
            _safe_remove_job_input(current_app, job_id)
            return jsonify({
                'error': 'Uploaded file is empty. Check file size limits or try uploading again.'
            }), 400

        # Now safe to read form (file already saved)
        job_name = (request.form.get('job_name') or '').strip() or pdb_name
        email = (request.form.get('email') or '').strip()
        if email:
            from backend.mailer import is_valid_email
            if not is_valid_email(email):
                _safe_remove_job_input(current_app, job_id)
                return jsonify({'error': 'Invalid email address.'}), 400
        chain1 = request.form.get('chain1', 'A')
        chain2 = request.form.get('chain2', 'B')
        try:
            interface_cutoff = float(request.form.get('interface_cutoff', 5.0))
        except (ValueError, TypeError):
            interface_cutoff = 5.0
        try:
            start_frame = int(request.form.get('start_frame', 1)) - 1
            end_frame = int(request.form.get('end_frame', -1))
            if end_frame is not None and end_frame <= 0:
                end_frame = -1
        except (ValueError, TypeError):
            start_frame = 0
            end_frame = -1
        try:
            frame_step = int(request.form.get('frame_step', 1))
            if frame_step < 1:
                frame_step = 1
        except (ValueError, TypeError):
            frame_step = 1
        reduce_param = request.form.get('reduce', request.args.get('reduce'))
        use_reduce = False
        if reduce_param is not None:
            try:
                use_reduce = bool(strtobool(str(reduce_param)))
            except ValueError:
                use_reduce = False

        # ── Backend frame-count verification ──
        total_frames_in_file = count_pdb_frames(filepath)
        effective = compute_effective_frames(total_frames_in_file, start_frame, end_frame, frame_step)

        if effective > MAX_WEB_FRAMES:
            suggested_step = -(-total_frames_in_file // MAX_WEB_FRAMES)  # ceil division
            _safe_remove_job_input(current_app, job_id)
            return jsonify({
                'error': (
                    f'Too many frames to process ({effective}). '
                    f'The web app allows at most {MAX_WEB_FRAMES} frames per job. '
                    f'Your file contains {total_frames_in_file} frames — use a step size '
                    f'of at least {suggested_step} to stay within the limit, '
                    f'or use the CLI for unlimited trajectory length.'
                )
            }), 400

        queue_manager = get_analysis_queue(current_app)
        _init_jobs_for_app(current_app)

        # Reserve a unique system ID and durably record everything workers need
        # to execute or recover this job.
        with _jobs_lock:
            reserved_ids = {
                job.get('system_id')
                for job in _jobs.values()
                if isinstance(job, dict)
            }
            base_system_dir = _system_dir(current_app, pdb_name)
            system_id = pdb_name
            if os.path.exists(base_system_dir) or system_id in reserved_ids:
                system_id = f'{pdb_name}_{job_id[:8]}'

            job_record = {
                'job_id': job_id,
                'pdb_name': pdb_name,
                'system_id': system_id,
                'status': 'queued',
                'progress': 0,
                'step_label': 'Queued',
                'frames': 0,
                'reduce': use_reduce,
                'chain1': chain1,
                'chain2': chain2,
                'interface_cutoff': interface_cutoff,
                'start_frame': start_frame,
                'end_frame': end_frame,
                'frame_step': frame_step,
                'job_name': job_name,
                'email': email,
                'startFrame': start_frame + 1,
                'endFrame': end_frame if end_frame != -1 else 'all',
                'frameStep': frame_step,
                'created_at': datetime.now().isoformat()
            }
            _jobs[job_id] = job_record
            try:
                _persist_jobs(current_app)
            except Exception:
                _jobs.pop(job_id, None)
                raise

        try:
            queue_manager.enqueue(job_id)
        except Exception:
            with _jobs_lock:
                _jobs.pop(job_id, None)
                _persist_jobs(current_app)
            _safe_remove_job_input(current_app, job_id)
            return _service_unavailable()

        return jsonify({
            'success': True,
            'job_id': job_id,
            'id': pdb_name,
            'message': 'Upload successful. Job queued.'
        })

    except (OSError, IOError) as e:
        if staged:
            _safe_remove_job_input(current_app, job_id)
        print(f"[jobs] Could not stage or persist upload {job_id}: {e}")
        return _service_unavailable()
    except Exception as e:
        if staged:
            _safe_remove_job_input(current_app, job_id)
        return jsonify({'error': str(e)}), 500


@bp.route('/status/<job_id>', methods=['GET'])
def get_status(job_id):
    """Get processing status by job ID (UUID) or legacy pdb_name"""
    _init_jobs_for_app(current_app)

    with _jobs_lock:
        # Try direct job_id lookup first
        if job_id in _jobs:
            return jsonify(_public_job(_jobs[job_id]))

        # Fallback: search by pdb_name for backwards compatibility
        for jid, job in _jobs.items():
            if job.get('pdb_name') == job_id:
                return jsonify(_public_job(job))

    return jsonify({'error': 'Not found'}), 404


@bp.route('/jobs', methods=['GET'])
def list_jobs():
    """Do not expose the global job list for unlisted user submissions."""
    return jsonify({
        'error': 'Global job listing is disabled. Use /api/jobs/lookup with known job IDs.'
    }), 404


@bp.route('/jobs/lookup', methods=['POST'])
def lookup_jobs():
    """Return job records only for IDs the caller already knows."""
    payload = request.get_json(silent=True) or {}
    ids = payload.get('ids', [])
    if not isinstance(ids, list):
        return jsonify({'error': 'ids must be an array'}), 400

    wanted = {
        value.strip()
        for value in ids[:200]
        if isinstance(value, str) and value.strip()
    }
    if not wanted:
        return jsonify([])

    _init_jobs_for_app(current_app)
    matches = []
    seen = set()
    with _jobs_lock:
        for job_id, job in _jobs.items():
            public_job_id = job.get('analysis_job_id')
            if job_id not in wanted and public_job_id not in wanted:
                continue
            if job_id in seen:
                continue
            seen.add(job_id)
            matches.append(_public_job(job))

    matches.sort(key=lambda j: j.get('created_at', ''), reverse=True)
    return jsonify(matches)

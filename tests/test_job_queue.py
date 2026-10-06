import json
import os
import threading

from backend.routes import upload


def _write_jobs(app, records):
    systems_dir = os.path.join(app.config["DATA_FOLDER"], "systems")
    os.makedirs(systems_dir, exist_ok=True)
    for job_id in records:
        queued_dir = upload._queued_job_dir(app, job_id)
        os.makedirs(queued_dir, exist_ok=True)
        with open(upload._queued_input_path(app, job_id), "w") as f:
            f.write("ATOM\nEND\n")
    with open(os.path.join(systems_dir, ".jobs.json"), "w") as f:
        json.dump(records, f)
    upload._load_jobs(app)


def _record(job_id, status="queued", created_at="2026-01-01T00:00:00"):
    return {
        "job_id": job_id,
        "pdb_name": job_id,
        "system_id": job_id,
        "status": status,
        "progress": 0,
        "step_label": status.title(),
        "created_at": created_at,
    }


def test_queue_runs_only_two_jobs_and_leaves_third_queued(app):
    records = {
        "job-1": _record("job-1", created_at="2026-01-01T00:00:01"),
        "job-2": _record("job-2", created_at="2026-01-01T00:00:02"),
        "job-3": _record("job-3", created_at="2026-01-01T00:00:03"),
    }
    _write_jobs(app, records)

    started = []
    release = threading.Event()
    first_two_started = threading.Event()
    lock = threading.Lock()

    def executor(_app, job_id):
        with lock:
            started.append(job_id)
            if len(started) == 2:
                first_two_started.set()
        release.wait(timeout=2)
        upload._update_job(_app, job_id, status="completed", step_label="Completed")

    manager = upload.AnalysisQueue(app, worker_count=2, executor=executor)
    manager.start()

    assert first_two_started.wait(timeout=2)
    assert set(started) == {"job-1", "job-2"}
    assert upload._jobs["job-3"]["status"] == "queued"

    release.set()
    manager.pending.join()
    assert set(started[:2]) == {"job-1", "job-2"}
    assert started[2] == "job-3"


def test_app_owns_one_two_worker_queue_manager(app):
    first = upload.get_analysis_queue(app)
    second = upload.get_analysis_queue(app)

    assert first is second
    assert first.worker_count == 2


def test_recovery_requeues_queued_and_interrupted_jobs_only(app):
    records = {
        "queued": _record("queued", status="queued", created_at="2026-01-01T00:00:01"),
        "running": _record("running", status="processing", created_at="2026-01-01T00:00:02"),
        "completed": _record("completed", status="completed", created_at="2026-01-01T00:00:03"),
        "failed": _record("failed", status="failed", created_at="2026-01-01T00:00:04"),
    }
    _write_jobs(app, records)
    partial = upload._system_dir(app, "running")
    os.makedirs(partial)
    with open(os.path.join(partial, "partial.txt"), "w") as f:
        f.write("partial")

    manager = upload.AnalysisQueue(app, worker_count=2, executor=lambda *_: None)
    manager._recover_unfinished_jobs()

    recovered = [manager.pending.get_nowait(), manager.pending.get_nowait()]
    assert recovered == ["queued", "running"]
    assert upload._jobs["queued"]["status"] == "queued"
    assert upload._jobs["running"]["status"] == "queued"
    assert upload._jobs["completed"]["status"] == "completed"
    assert upload._jobs["failed"]["status"] == "failed"
    assert not os.path.exists(partial)


def test_recovery_marks_missing_queued_input_failed(app):
    records = {"missing": _record("missing")}
    _write_jobs(app, records)
    os.unlink(upload._queued_input_path(app, "missing"))

    manager = upload.AnalysisQueue(app, worker_count=1, executor=lambda *_: None)
    manager._recover_unfinished_jobs()

    assert manager.pending.empty()
    assert upload._jobs["missing"]["status"] == "failed"
    assert "missing" in upload._jobs["missing"]["error"].lower()

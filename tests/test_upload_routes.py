"""Tests for the upload / jobs API routes."""
import io
import json
import os
import shutil
import pytest
from unittest.mock import patch

from backend.routes import upload


def _make_pdb_file(content=b"ATOM      1  N   ALA A   1       1.0   2.0   3.0  1.00  0.00           N\nEND\n"):
    """Return a tuple (data, filename) suitable for ``client.post(data=...)``."""
    return (io.BytesIO(content), "test.pdb")


class TestUploadRoute:
    def test_missing_file_returns_400(self, client):
        resp = client.post("/api/upload")
        assert resp.status_code == 400
        data = resp.get_json()
        assert "error" in data

    def test_empty_file_returns_400(self, client):
        resp = client.post(
            "/api/upload",
            data={"file": (io.BytesIO(b""), "empty.pdb")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "empty" in data["error"].lower() or "error" in data

    def test_invalid_extension_returns_400(self, client):
        resp = client.post(
            "/api/upload",
            data={"file": (io.BytesIO(b"hello"), "test.txt")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400

    def test_upload_with_reduce_true(self, client):
        resp = client.post(
            "/api/upload",
            data={
                "file": _make_pdb_file(),
                "reduce": "true",
                "chain1": "A",
                "chain2": "B",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "job_id" in data

        job = upload._jobs[data["job_id"]]
        assert job["status"] == "queued"
        assert job["reduce"] is True
        assert os.path.isfile(upload._queued_input_path(client.application, data["job_id"]))

    def test_upload_with_reduce_false(self, client):
        resp = client.post(
            "/api/upload",
            data={
                "file": _make_pdb_file(),
                "reduce": "false",
                "chain1": "A",
                "chain2": "B",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        job = upload._jobs[resp.get_json()["job_id"]]
        assert job["reduce"] is False

    def test_upload_reduce_default_is_false(self, client):
        resp = client.post(
            "/api/upload",
            data={
                "file": _make_pdb_file(),
                "chain1": "A",
                "chain2": "B",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        job = upload._jobs[resp.get_json()["job_id"]]
        assert job["reduce"] is False

    def test_busy_workers_still_accept_upload_as_queued(self, client):
        resp = client.post(
            "/api/upload",
            data={"file": _make_pdb_file()},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        assert upload._jobs[resp.get_json()["job_id"]]["status"] == "queued"

    def test_enqueue_failure_returns_503_and_rolls_back(self, app, client):
        class FailingQueue:
            def enqueue(self, job_id):
                raise RuntimeError("queue unavailable")

        app.extensions["analysis_queue"] = FailingQueue()
        resp = client.post(
            "/api/upload",
            data={"file": _make_pdb_file()},
            content_type="multipart/form-data",
        )

        assert resp.status_code == 503
        assert resp.headers["Retry-After"] == "5"
        assert upload._jobs == {}
        queued_root = os.path.join(app.config["DATA_FOLDER"], "systems", ".queued")
        assert not os.path.exists(queued_root) or not os.listdir(queued_root)

    def test_persist_failure_returns_503_and_rolls_back(self, app, client):
        with patch("backend.routes.upload._persist_jobs", side_effect=OSError("disk full")):
            resp = client.post(
                "/api/upload",
                data={"file": _make_pdb_file()},
                content_type="multipart/form-data",
            )

        assert resp.status_code == 503
        assert resp.headers["Retry-After"] == "5"
        assert upload._jobs == {}

    def test_staging_failure_returns_503(self, client):
        with patch(
            "werkzeug.datastructures.FileStorage.save",
            side_effect=OSError("volume unavailable"),
        ):
            resp = client.post(
                "/api/upload",
                data={"file": _make_pdb_file()},
                content_type="multipart/form-data",
            )

        assert resp.status_code == 503
        assert resp.headers["Retry-After"] == "5"
        queued_root = os.path.join(client.application.config["DATA_FOLDER"], "systems", ".queued")
        assert not os.path.exists(queued_root) or not os.listdir(queued_root)

    def test_queue_startup_failure_returns_503(self, app, client):
        class FailingStartupQueue:
            def start(self):
                raise OSError("queue volume unavailable")

        app.config["JOB_QUEUE_AUTOSTART"] = True
        app.extensions["analysis_queue"] = FailingStartupQueue()

        resp = client.post(
            "/api/upload",
            data={"file": _make_pdb_file()},
            content_type="multipart/form-data",
        )

        assert resp.status_code == 503
        assert resp.headers["Retry-After"] == "5"


class TestStatusRoute:
    def test_unknown_job_returns_404(self, client):
        resp = client.get("/api/status/nonexistent-id")
        assert resp.status_code == 404


class TestProcessingCleanup:
    def test_completed_job_removes_copied_source_pdb_but_keeps_viewer(self, app):
        job_id = "cleanup-job"
        system_id = "cleanup_system"
        queued_dir = upload._queued_job_dir(app, job_id)
        os.makedirs(queued_dir, exist_ok=True)
        queued_input = upload._queued_input_path(app, job_id)
        with open(queued_input, "w", encoding="utf-8") as f:
            f.write("ATOM      1  N   ALA A   1       1.0   2.0   3.0  1.00  0.00           N\nEND\n")

        upload._jobs = {
            job_id: {
                "job_id": job_id,
                "pdb_name": "cleanup",
                "system_id": system_id,
                "status": "queued",
                "progress": 0,
                "step_label": "Queued",
                "chain1": "A",
                "chain2": "B",
                "created_at": "2026-01-01T00:00:00",
            }
        }
        upload._jobs_source_path = upload._jobs_file_path(app)

        def fake_run_pipeline(pdb_file, system_dir, **_kwargs):
            os.makedirs(system_dir, exist_ok=True)
            shutil.copy(pdb_file, os.path.join(system_dir, "input.pdb"))
            with open(os.path.join(system_dir, "_metadata.json"), "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "totalFrames": 1,
                        "chainPattern": "A_B",
                        "jobId": "2026001-CLEANUP1",
                    },
                    f,
                )
            return 1, None

        def fake_write_viewer(system_dir, **_kwargs):
            with open(os.path.join(system_dir, "viewer.pdb"), "w", encoding="utf-8") as f:
                f.write("ATOM      1  N   ALA A   1       1.0   2.0   3.0  1.00  0.00           N\nEND\n")
            return True

        with patch("engine.run_pipeline", side_effect=fake_run_pipeline), patch(
            "engine.viewer_pdb.write_viewer_frame_pdb", side_effect=fake_write_viewer
        ):
            upload.process_queued_job(app, job_id)

        system_dir = upload._system_dir(app, system_id)
        assert upload._jobs[job_id]["status"] == "completed"
        assert not os.path.exists(os.path.join(system_dir, "input.pdb"))
        assert os.path.isfile(os.path.join(system_dir, "viewer.pdb"))
        assert not os.path.exists(queued_dir)


class TestJobsRoute:
    def test_global_list_jobs_is_disabled(self, client):
        resp = client.get("/api/jobs")
        assert resp.status_code == 404

    def test_lookup_jobs_returns_only_known_ids(self, client):
        upload._jobs = {}
        upload._jobs_source_path = upload._jobs_file_path(client.application)
        upload._jobs["known-job"] = {
            "job_id": "known-job",
            "pdb_name": "known",
            "system_id": "known",
            "status": "queued",
            "created_at": "2026-01-01T00:00:00",
        }
        upload._jobs["other-job"] = {
            "job_id": "other-job",
            "pdb_name": "other",
            "system_id": "other",
            "status": "queued",
            "created_at": "2026-01-02T00:00:00",
        }

        resp = client.post("/api/jobs/lookup", json={"ids": ["known-job"]})
        assert resp.status_code == 200
        data = resp.get_json()
        assert [job["job_id"] for job in data] == ["known-job"]
        assert "system_id" not in data[0]

    def test_lookup_completed_job_by_analysis_id(self, client):
        upload._jobs = {}
        upload._jobs_source_path = upload._jobs_file_path(client.application)
        upload._jobs["upload-job"] = {
            "job_id": "upload-job",
            "pdb_name": "known",
            "system_id": "known",
            "status": "completed",
            "analysis_job_id": "2026001-KNOWNJOB",
            "created_at": "2026-01-01T00:00:00",
        }

        resp = client.post("/api/jobs/lookup", json={"ids": ["2026001-KNOWNJOB"]})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) == 1
        assert data[0]["job_id"] == "upload-job"
        assert data[0]["analysis_job_id"] == "2026001-KNOWNJOB"


@pytest.mark.parametrize("frames,step,end,status", [
    (50, 1, -1, 200), (51, 1, -1, 400), (53, 1, -1, 400),
    (100, 2, -1, 200), (101, 2, -1, 400),
    (100, 1, 50, 200), (100, 1, 51, 400),
])
def test_strict_web_frame_limit(client, frames, step, end, status):
    with patch.object(upload, 'count_pdb_frames', return_value=frames):
        response = client.post('/api/upload', data={
            'file': _make_pdb_file(), 'chain1': 'A', 'chain2': 'B',
            'frame_step': str(step), 'end_frame': str(end),
        }, content_type='multipart/form-data')
    assert response.status_code == status
    if status == 400:
        assert 'at most 50 frames per job' in response.get_json()['error']


class TestUploadEmailValidation:
    def test_invalid_email_returns_400(self, client):
        resp = client.post(
            "/api/upload",
            data={
                "file": (io.BytesIO(b"ATOM\nEND\n"), "test.pdb"),
                "email": "not-an-email",
            },
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "email" in resp.get_json()["error"].lower()

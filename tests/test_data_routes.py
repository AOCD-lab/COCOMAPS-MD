"""Tests for the data retrieval API routes."""
import json
import os
import shutil

import pytest


class TestInteractions:
    def test_returns_data(self, client):
        resp = client.get("/api/systems/test_system/interactions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, (list, dict))

    def test_unknown_system_404(self, client):
        resp = client.get("/api/systems/nonexistent/interactions")
        assert resp.status_code == 404

    def test_traversal_system_id_404(self, client):
        resp = client.get("/api/systems/%2e%2e/interactions")
        assert resp.status_code == 404

    def test_analysis_job_id_route_returns_data(self, client):
        resp = client.get("/api/analysis/2026001-TESTJOB1/interactions")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["system"] == "2026001-TESTJOB1"
        assert data["interactions"]

    def test_uploaded_system_id_route_is_hidden_but_job_id_works(self, client, fake_system):
        systems_root = os.path.dirname(fake_system)
        private_dir = os.path.join(systems_root, "private_upload")
        shutil.copytree(fake_system, private_dir)
        meta_path = os.path.join(private_dir, "_metadata.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["isExample"] = False
        meta["jobId"] = "2026001-PRIVATE1"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        assert client.get("/api/systems/private_upload/interactions").status_code == 404
        assert client.get("/api/analysis/2026001-PRIVATE1/interactions").status_code == 200


class TestArea:
    def test_returns_data(self, client):
        resp = client.get("/api/systems/test_system/area")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, (list, dict))


class TestTrends:
    def test_returns_data(self, client):
        resp = client.get("/api/systems/test_system/trends")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, (list, dict))


class TestInterfacePatches:
    def test_missing_file_returns_empty(self, client):
        resp = client.get("/api/systems/test_system/interface-patches")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["defaultThreshold"] == 0.7
        assert data["minimumThreshold"] == 0.5
        assert data["minimumPatchSize"] == 3
        assert data["edges"] == []

    def test_returns_interface_patches_payload(self, client, fake_system):
        with open(os.path.join(fake_system, "_interface_patches.json"), "w", encoding="utf-8") as f:
            json.dump({
                "schemaVersion": 2,
                "defaultThreshold": 0.7,
                "minimumThreshold": 0.5,
                "minimumPatchSize": 2,
                "totalFrames": 10,
                "edges": [{"source": {"chain": "A", "resNum": 1}, "target": {"chain": "B", "resNum": 2}, "frameCount": 7}],
            }, f)

        resp = client.get("/api/systems/test_system/interface-patches")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["defaultThreshold"] == 0.7
        assert data["minimumThreshold"] == 0.5
        assert data["minimumPatchSize"] == 3
        assert data["totalFrames"] == 10
        assert data["edges"][0]["frameCount"] == 7


class TestFramePdb:
    def test_frame_1_serves_root_viewer_pdb_without_frame_folder(self, client, fake_system):
        shutil.rmtree(os.path.join(fake_system, "frame_1"))
        viewer_path = os.path.join(fake_system, "viewer.pdb")
        with open(viewer_path, "w", encoding="utf-8") as f:
            f.write(
                "ATOM      1  N   ALA A   1       1.000   2.000   3.000  1.00  0.00           N\n"
                "END\n"
            )

        resp = client.get("/api/systems/test_system/frame/1/pdb")

        assert resp.status_code == 200
        assert b"ALA A   1" in resp.data

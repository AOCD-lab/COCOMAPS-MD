"""Tests for the systems API routes."""
import json
import os
import shutil

import pytest


class TestListSystems:
    def test_returns_list(self, client):
        resp = client.get("/api/systems")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data, list)

    def test_fake_system_appears(self, client):
        resp = client.get("/api/systems")
        data = resp.get_json()
        ids = [s["id"] for s in data]
        assert "test_system" in ids

    def test_system_has_expected_fields(self, client):
        resp = client.get("/api/systems")
        data = resp.get_json()
        system = next(s for s in data if s["id"] == "test_system")
        assert "name" in system
        assert "frames" in system

    def test_uploaded_systems_are_not_listed(self, client, fake_system):
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

        resp = client.get("/api/systems")
        data = resp.get_json()
        ids = [s["id"] for s in data]
        assert "test_system" in ids
        assert "private_upload" not in ids


class TestSystemDetail:
    def test_known_system(self, client):
        resp = client.get("/api/systems/test_system")
        assert resp.status_code == 200

    def test_analysis_by_job_id(self, client):
        resp = client.get("/api/analysis/2026001-TESTJOB1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["id"] == "2026001-TESTJOB1"
        assert data["jobId"] == "2026001-TESTJOB1"

    def test_analysis_by_job_id_prefers_public_example_on_duplicate_job_id(self, client, fake_system):
        systems_root = os.path.dirname(fake_system)
        private_dir = os.path.join(systems_root, "aaa_private_duplicate")
        shutil.copytree(fake_system, private_dir)
        shutil.rmtree(os.path.join(private_dir, "frame_1"))
        meta_path = os.path.join(private_dir, "_metadata.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["chainPattern"] = "X_Y"
        meta["isExample"] = False
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        resp = client.get("/api/analysis/2026001-TESTJOB1")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["isExample"] is True
        assert data["chain1"] == "A"
        assert data["chain2"] == "B"

    def test_chain_pattern_comes_from_metadata_without_frame_folder(self, client, fake_system):
        shutil.rmtree(os.path.join(fake_system, "frame_1"))
        meta_path = os.path.join(fake_system, "_metadata.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["chainPattern"] = "A_C"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f)

        resp = client.get("/api/systems/test_system")

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["chain1"] == "A"
        assert data["chain2"] == "C"

    def test_unknown_system_404(self, client):
        resp = client.get("/api/systems/no_such_system")
        assert resp.status_code == 404

    def test_traversal_system_id_404(self, client):
        resp = client.get("/api/systems/%2e%2e")
        assert resp.status_code == 404


class TestRenameDisabled:
    def test_rename_endpoint_is_not_exposed(self, client, fake_system):
        resp = client.post(
            "/api/systems/test_system/rename",
            json={"name": "Renamed System"},
        )
        assert resp.status_code == 404

        meta_path = os.path.join(fake_system, ".metadata.json")
        assert not os.path.exists(meta_path)

    def test_traversal_rename_is_not_exposed(self, client, fake_system):
        root = os.path.dirname(os.path.dirname(fake_system))
        escaped_meta = os.path.join(root, ".metadata.json")

        resp = client.post(
            "/api/systems/%2e%2e/rename",
            json={"name": "Escaped"},
        )

        assert resp.status_code == 404
        assert not os.path.exists(escaped_meta)

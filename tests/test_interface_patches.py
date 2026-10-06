"""Tests for interface-patch discovery, analysis, and artifact generation."""
import json
import os
from pathlib import Path

import pytest

from engine.interface_patches import (
    _find_final_files,
    count_interface_patches,
    run_interface_patches,
)


@pytest.fixture()
def system_with_no_reduce(tmp_dir):
    """System where CoCoMaps ran without reduce (standard .pdb naming)."""
    frame = os.path.join(tmp_dir, "frame_1")
    os.makedirs(frame)
    csv_path = os.path.join(frame, "frame_1.pdb_A_B_final_file.csv")
    with open(csv_path, "w") as f:
        f.write("Res. Name 1,Res. Number 1,Chain 1,Res. Name 2,Res. Number 2,Chain 2,Type of Interactions\n")
        f.write("ALA,1,A,GLY,1,B,H-bond\n")
        f.write("SER,2,A,GLY,1,B,H-bond\n")
    return tmp_dir


@pytest.fixture()
def system_with_reduce(tmp_dir):
    """System where CoCoMaps ran with reduce (pd_h.pdb naming)."""
    frame = os.path.join(tmp_dir, "frame_1")
    os.makedirs(frame)
    csv_path = os.path.join(frame, "frame_1.pd_h.pdb_A_B_final_file.csv")
    with open(csv_path, "w") as f:
        f.write("Res. Name 1,Res. Number 1,Chain 1,Res. Name 2,Res. Number 2,Chain 2,Type of Interactions\n")
        f.write("ALA,1,A,GLY,1,B,H-bond\n")
    return tmp_dir


class TestFindFinalFiles:
    def test_finds_no_reduce_naming(self, system_with_no_reduce):
        files = _find_final_files(Path(system_with_no_reduce))
        assert len(files) == 1
        assert "frame_1.pdb_A_B_final_file.csv" in files[0].name

    def test_finds_reduce_naming(self, system_with_reduce):
        files = _find_final_files(Path(system_with_reduce))
        assert len(files) == 1
        assert "pd_h.pdb" in files[0].name

    def test_empty_dir_returns_empty(self, tmp_dir):
        os.makedirs(os.path.join(tmp_dir, "frame_1"))
        files = _find_final_files(Path(tmp_dir))
        assert files == []


class TestInterfacePatches:
    def test_count_uses_interface_patch_fields(self, system_with_no_reduce):
        patches, pair_counts, total_frames = count_interface_patches(
            system_with_no_reduce,
        )

        assert total_frames == 1
        assert len(pair_counts) == 2
        assert len(patches) == 1
        assert patches[0]["Interface_patch_id"] == 1
        assert patches[0]["Interface_patch_size"] == 3

    def test_run_writes_interface_patches_artifact(self, system_with_no_reduce):
        patches = run_interface_patches(
            system_with_no_reduce,
            verbose=False,
        )

        artifact = Path(system_with_no_reduce) / "_interface_patches.json"
        assert len(patches) == 1
        assert artifact.exists()
        assert json.loads(artifact.read_text()) == {
            "schemaVersion": 2,
            "defaultThreshold": 0.7,
            "minimumThreshold": 0.5,
            "minimumPatchSize": 3,
            "totalFrames": 1,
            "edges": [
                {
                    "source": {"chain": "A", "resNum": 1, "resName": "ALA"},
                    "target": {"chain": "B", "resNum": 1, "resName": "GLY"},
                    "frameCount": 1,
                    "conservation": 1.0,
                },
                {
                    "source": {"chain": "A", "resNum": 2, "resName": "SER"},
                    "target": {"chain": "B", "resNum": 1, "resName": "GLY"},
                    "frameCount": 1,
                    "conservation": 1.0,
                },
            ],
        }

    def test_single_residue_pair_is_not_a_patch(self, system_with_reduce):
        patches, pair_counts, total_frames = count_interface_patches(
            system_with_reduce, min_interface_patch_size=2,
        )
        assert total_frames == 1
        assert len(pair_counts) == 1
        assert patches == []

        exported = run_interface_patches(
            system_with_reduce, min_interface_patch_size=2, verbose=False,
        )
        assert exported == []
        artifact = json.loads((Path(system_with_reduce) / "_interface_patches.json").read_text())
        assert artifact["minimumPatchSize"] == 3

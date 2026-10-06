"""Tests for engine.aggregate_csv — verify aggregation handles both
reduce (pd_h.pdb) and no-reduce file naming.
"""
import csv
import os

import pytest

from engine.aggregate_csv import _extract_atom_pair_from_row, aggregate_system


def _write_cocomaps_frame(frame_dir, frame_num, chain_pattern="A_B", use_reduce=False):
    """Write minimal stub CSVs that aggregate_system expects per frame."""
    stem = f"frame_{frame_num}.pd_h.pdb" if use_reduce else f"frame_{frame_num}.pdb"

    # final_file.csv
    final = os.path.join(frame_dir, f"{stem}_{chain_pattern}_final_file.csv")
    with open(final, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Res. Name 1", "Res. Number 1", "Chain 1",
                     "Res. Name 2", "Res. Number 2", "Chain 2",
                     "Type of Interactions"])
        w.writerow(["ALA", "1", "A", "GLY", "1", "B", "H-bond"])

    # Rsa_stats.csv
    rsa = os.path.join(frame_dir, f"{stem}_{chain_pattern}_complex.pdb_Rsa_stats.csv")
    with open(rsa, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Property", "Value"])
        w.writerow(["Buried area upon the complex formation / Interface area (Å²)", "100.0"])
        w.writerow(["Buried area upon the complex formation (%)", "10.0"])
        w.writerow(["POLAR Buried area upon the complex formation / Interface area (Å²)", "40.0"])
        w.writerow(["POLAR Interface (%)", "4.0"])
        w.writerow(["NON POLAR Buried area upon the complex formation / Interface area (Å²)", "60.0"])
        w.writerow(["NON POLAR Interface (%)", "6.0"])

    # summary_table.csv
    summary = os.path.join(frame_dir, f"{stem}_{chain_pattern}_summary_table.csv")
    with open(summary, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Property", "Value"])
        w.writerow(["Number of H-bonds", "5"])


@pytest.fixture()
def system_no_reduce(tmp_dir):
    frame_dir = os.path.join(tmp_dir, "frame_1")
    os.makedirs(frame_dir)
    _write_cocomaps_frame(frame_dir, 1, use_reduce=False)
    return tmp_dir


@pytest.fixture()
def system_reduce(tmp_dir):
    frame_dir = os.path.join(tmp_dir, "frame_1")
    os.makedirs(frame_dir)
    _write_cocomaps_frame(frame_dir, 1, use_reduce=True)
    return tmp_dir


class TestAggregateCSV:
    def test_aggregation_no_reduce(self, system_no_reduce):
        aggregate_system(system_no_reduce, verbose=False)
        assert os.path.isfile(os.path.join(system_no_reduce, "_interactions.csv"))
        assert os.path.isfile(os.path.join(system_no_reduce, "_metadata.json"))

    def test_aggregation_reduce(self, system_reduce):
        aggregate_system(system_reduce, verbose=False)
        assert os.path.isfile(os.path.join(system_reduce, "_interactions.csv"))
        assert os.path.isfile(os.path.join(system_reduce, "_metadata.json"))

    def test_aggregation_writes_pi_atoms_in_residue_order(self, system_reduce):
        frame_dir = os.path.join(system_reduce, "frame_1")
        cation_pi = os.path.join(
            frame_dir, "frame_1.pd_h.pdb_A_B_Cation_pi.csv"
        )
        with open(cation_pi, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Res. Name 1", "Res. Number 1", "Chain 1",
                "Res. Name 2", "Res. Number 2", "Chain 2", "Distance (Å)",
                "Cation Atom", "Cation From", "Ring From",
            ])
            writer.writerow([
                "U", "104", "A", "ARG", "130", "B", "3.87",
                "NE", "ARG-130", "U-104",
            ])

        aggregate_system(system_reduce, verbose=False)

        with open(os.path.join(system_reduce, "_atom_pairs.csv"), newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert rows[0]["atom1"] == "Pi-Ring"
        assert rows[0]["atom2"] == "NE"


@pytest.mark.parametrize(
    ("interaction_type", "role_columns", "expected_atoms"),
    [
        (
            "Cation-π interactions",
            {"Cation Atom": "NE", "Cation From": "ARG-130", "Ring From": "U-104"},
            ("Pi-Ring", "NE"),
        ),
        (
            "Anion-π interactions",
            {"Anion Atom": "OD1", "Anion From": "ASP-130", "Ring From": "U-104"},
            ("Pi-Ring", "OD1"),
        ),
        (
            "Amino-π interactions",
            {"Polar Atom": "NZ", "Polar From": "LYS-130", "Ring From": "U-104"},
            ("Pi-Ring", "NZ"),
        ),
        (
            "CH-π interactions",
            {"C Atom": "CE", "H Atom": "HE3", "C Atom From": "LYS", "Ring From": "U-104"},
            ("Pi-Ring", "CE(HE3)"),
        ),
        (
            "π-π interactions",
            {},
            ("Pi-Ring", "Pi-Ring"),
        ),
    ],
)
def test_pi_atom_roles_are_aligned_with_residue_sides(
    interaction_type, role_columns, expected_atoms
):
    row = {
        "Res. Name 1": "U",
        "Res. Number 1": "104",
        "Chain 1": "A",
        "Res. Name 2": "ARG" if "Cation" in interaction_type else "LYS",
        "Res. Number 2": "130",
        "Chain 2": "B",
        "Distance (Å)": "3.87",
        **role_columns,
    }

    atom1, atom2, distance, _angle = _extract_atom_pair_from_row(row, interaction_type)

    assert (atom1, atom2) == expected_atoms
    assert distance == 3.87


def test_pi_atom_roles_support_ring_on_second_residue():
    row = {
        "Res. Name 1": "C",
        "Res. Number 1": "105",
        "Chain 1": "A",
        "Res. Name 2": "PHE",
        "Res. Number 2": "160",
        "Chain 2": "B",
        "Distance (Å)": "3.57",
        "C Atom": "C4'",
        "H Atom": "H4'",
        "C Atom From": "C",
        "Ring From": "PHE-160",
    }

    atom1, atom2, _distance, _angle = _extract_atom_pair_from_row(
        row, "CH-π interactions"
    )

    assert (atom1, atom2) == ("C4'(H4')", "Pi-Ring")

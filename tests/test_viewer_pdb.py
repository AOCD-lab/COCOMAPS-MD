from pathlib import Path

from engine.viewer_pdb import write_viewer_frame_pdb


def _pdb_line(record, serial, atom, resname, chain, resid, x, y, z, element):
    return (
        f"{record:<6}{serial:5d} {atom:<4} {resname:>3} {chain:1}{resid:4d}"
        f"    {x:8.3f}{y:8.3f}{z:8.3f}{1.00:6.2f}{0.00:6.2f}"
        f"          {element:>2}\n"
    )


def _write_system(system_dir: Path, pdb_text: str):
    system_dir.mkdir()
    (system_dir / "_interactions.csv").write_text(
        "resName1,resNum1,chain1,resName2,resNum2,chain2,frame,types\n",
        encoding="utf-8",
    )
    (system_dir / f"{system_dir.name}.pdb").write_text(pdb_text, encoding="utf-8")


def _residue_keys(pdb_path: Path):
    keys = set()
    with open(pdb_path, encoding="utf-8") as f:
        for line in f:
            if line[:6].strip() not in {"ATOM", "HETATM"}:
                continue
            keys.add((line[17:20].strip(), line[21:22].strip(), int(line[22:26])))
    return keys


def _x_coords_for_residue(pdb_path: Path, resname: str, chain: str, resid: int):
    coords = []
    with open(pdb_path, encoding="utf-8") as f:
        for line in f:
            if line[:6].strip() not in {"ATOM", "HETATM"}:
                continue
            if (
                line[17:20].strip() == resname
                and line[21:22].strip() == chain
                and int(line[22:26]) == resid
            ):
                coords.append(float(line[30:38]))
    return coords


def test_viewer_pdb_keeps_selected_chains_and_removes_far_solvent_ions(tmp_path):
    system_dir = tmp_path / "viewer_case"
    pdb_text = "".join(
        [
            "MODEL        1\n",
            _pdb_line("ATOM", 1, "N", "ALA", "A", 1, 0.0, 0.0, 0.0, "N"),
            _pdb_line("ATOM", 2, "CA", "ALA", "A", 1, 1.0, 0.0, 0.0, "C"),
            _pdb_line("ATOM", 3, "N", "GLY", "B", 1, 8.0, 0.0, 0.0, "N"),
            _pdb_line("ATOM", 4, "CA", "GLY", "B", 1, 9.0, 0.0, 0.0, "C"),
            _pdb_line("ATOM", 5, "N", "SER", "C", 1, 100.0, 0.0, 0.0, "N"),
            _pdb_line("HETATM", 6, "C1", "LIG", "L", 1, 150.0, 0.0, 0.0, "C"),
            _pdb_line("HETATM", 7, "C1", "LIG", "A", 2, 150.0, 0.0, 0.0, "C"),
            _pdb_line("HETATM", 8, "O", "HOH", "W", 10, 4.0, 0.0, 0.0, "O"),
            _pdb_line("HETATM", 9, "O", "HOH", "W", 11, 2.0, 0.0, 0.0, "O"),
            _pdb_line("HETATM", 10, "CL", "CL", "I", 20, 5.0, 0.0, 0.0, "CL"),
            _pdb_line("HETATM", 11, "CL", "CL", "I", 21, 50.0, 0.0, 0.0, "CL"),
            _pdb_line("HETATM", 12, "NA", "NA", "I", 22, 12.0, 0.0, 0.0, "NA"),
            _pdb_line("HETATM", 13, "MG", "MG", "I", 23, 60.0, 0.0, 0.0, "MG"),
            _pdb_line("HETATM", 14, "O", "SPC", "W", 12, 40.0, 0.0, 0.0, "O"),
            _pdb_line("HETATM", 15, "CL", "CLA", "I", 24, 40.0, 0.0, 0.0, "CL"),
            "ENDMDL\n",
            "END\n",
        ]
    )
    _write_system(system_dir, pdb_text)

    assert write_viewer_frame_pdb(system_dir, chain_a="A", chain_b="B") is True

    keys = _residue_keys(system_dir / "viewer.pdb")
    assert ("ALA", "A", 1) in keys
    assert ("GLY", "B", 1) in keys
    assert ("LIG", "A", 2) in keys
    assert ("SER", "C", 1) not in keys
    assert ("LIG", "L", 1) not in keys
    assert ("HOH", "W", 10) in keys
    assert ("CL", "I", 20) in keys
    assert ("HOH", "W", 11) not in keys
    assert ("CL", "I", 21) not in keys
    assert ("NA", "I", 22) not in keys
    assert ("MG", "I", 23) not in keys
    assert ("SPC", "W", 12) not in keys
    assert ("CLA", "I", 24) not in keys


def test_viewer_pdb_uses_first_selected_raw_frame_for_coordinates_and_filtering(tmp_path):
    system_dir = tmp_path / "sampled_case"
    pdb_text = "".join(
        [
            "MODEL        1\n",
            _pdb_line("ATOM", 1, "N", "ALA", "A", 1, 0.0, 0.0, 0.0, "N"),
            _pdb_line("ATOM", 2, "N", "GLY", "B", 1, 20.0, 0.0, 0.0, "N"),
            _pdb_line("HETATM", 3, "O", "HOH", "W", 10, 3.0, 0.0, 0.0, "O"),
            "ENDMDL\n",
            "MODEL        2\n",
            _pdb_line("ATOM", 1, "N", "ALA", "A", 1, 100.0, 0.0, 0.0, "N"),
            _pdb_line("ATOM", 2, "N", "GLY", "B", 1, 108.0, 0.0, 0.0, "N"),
            _pdb_line("HETATM", 3, "O", "HOH", "W", 10, 104.0, 0.0, 0.0, "O"),
            _pdb_line("HETATM", 4, "O", "HOH", "W", 11, 0.0, 0.0, 0.0, "O"),
            "ENDMDL\n",
            "END\n",
        ]
    )
    _write_system(system_dir, pdb_text)

    assert write_viewer_frame_pdb(
        system_dir,
        chain_a="A",
        chain_b="B",
        start_frame=1,
        end_frame=-1,
        frame_step=1,
    ) is True

    viewer = system_dir / "viewer.pdb"
    assert min(_x_coords_for_residue(viewer, "ALA", "A", 1)) > 90.0
    keys = _residue_keys(viewer)
    assert ("HOH", "W", 10) in keys
    assert ("HOH", "W", 11) not in keys

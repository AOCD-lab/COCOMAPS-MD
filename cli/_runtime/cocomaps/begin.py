"""
Main execution script for the biomolecular interaction analysis pipeline.

This script serves as the command-line entry point, orchestrating the complete
workflow for detecting inter-chain interactions in protein/RNA complexes.

Workflow overview:
- Parses a user-provided JSON configuration file containing analysis parameters
  and geometric thresholds.
- Optionally converts CIF files to PDB format and adds hydrogens using REDUCE.
- Handles multi-model PDBs by isolating the first model when present.
- Iterates over all chain pair combinations specified in the configuration.

Intended usage:
    python begin.py config.json
"""

import argparse
import shutil
import sys
import time
import os
import shlex
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Bio.PDB import PDBParser, PDBIO

from update_constants import tc
from cif_conversion import Cif_conversion
from read_pdb_regex import read_pdb
from constants import NACCESS_FILE_NAME, REDUCE_COMMAND


def _archive_naccess_outputs(
    compound_pdb: str,
    chain1_pdb: str,
    chain2_pdb: str,
    chain1_id: str,
    chain2_id: str,
) -> None:
    """
    Copy NACCESS sidecars (.rsa/.asa) and summary CSVs from ``naccess_working`` into
    ``<pdb_dir>/naccess_outputs/<compound_stem>_<c1>_<c2>/``.
    """
    compound_res = str(Path(compound_pdb).resolve())
    chain1_res = str(Path(chain1_pdb).resolve())
    chain2_res = str(Path(chain2_pdb).resolve())
    pdb_dir = Path(compound_res).parent
    tag = f"{Path(compound_res).stem}_{chain1_id}_{chain2_id}"
    dest = pdb_dir / "naccess_outputs" / tag
    dest.mkdir(parents=True, exist_ok=True)
    copied = 0

    def copy_sidecar(pdb_path_resolved: str, label: str) -> None:
        nonlocal copied
        stem = Path(pdb_path_resolved).stem
        parent = Path(pdb_path_resolved).parent
        for ext in (".rsa", ".asa"):
            for base in (parent, Path.cwd().resolve()):
                src = base / f"{stem}{ext}"
                if src.is_file():
                    shutil.copy2(src, dest / f"{label}_{stem}{ext}")
                    copied += 1
                    break

    copy_sidecar(compound_res, "compound")
    copy_sidecar(chain1_res, "chain1")
    copy_sidecar(chain2_res, "chain2")

    # CSV paths match ``naccess_working`` (same string as ``compound_pdb_path`` passed in).
    for suffix, out_name in (
        (f"_{NACCESS_FILE_NAME}", NACCESS_FILE_NAME),
        ("_ASA_table_chain1.csv", "ASA_table_chain1.csv"),
        ("_ASA_table_chain2.csv", "ASA_table_chain2.csv"),
    ):
        for cand in (compound_pdb, compound_res):
            src = Path(cand + suffix)
            if src.is_file():
                shutil.copy2(src, dest / out_name)
                copied += 1
                break

    if copied:
        print(f"[naccess] Saved {copied} file(s) under {dest}")


def parse_arguments():
    """
    Parses command-line arguments and returns them as variables.

    Returns:
        json_file_path (str): Path to the json file with all the threshold values
    """
    parser = argparse.ArgumentParser(
        description="Biomolecular interaction analysis from a JSON configuration."
    )

    parser.add_argument(
        "json_file_path", type=str, help="Path to the JSON configuration file"
    )

    args = parser.parse_args()

    return args.json_file_path


if __name__ == "__main__":
    start = time.time()
    json_file_path = parse_arguments()
    tc.read_json_file(json_file_path)

    if not tc.pdb_file:
        print("[FATAL] JSON must set pdb_file to the input structure path.", file=sys.stderr)
        sys.exit(1)

    # Resolve structure path so intermediates and NACCESS sidecars (.rsa/.asa) sit next to
    # the intended input file. Relative pdb_file is taken relative to the JSON config directory.
    _json_parent = Path(json_file_path).resolve().parent
    _pdb_in = Path(tc.pdb_file).expanduser()
    if not _pdb_in.is_absolute():
        tc.pdb_file = str((_json_parent / _pdb_in).resolve())
    else:
        tc.pdb_file = str(_pdb_in.resolve())
    if not tc.chains_set_1 or not tc.chains_set_2:
        print(
            "[FATAL] JSON must define non-empty chains_set_1 and chains_set_2.",
            file=sys.stderr,
        )
        sys.exit(1)

    from workflow import process
    from utils import get_chains_ranges_lines, chain_selection_pdbs_making

    if tc.pdb_file.endswith(".cif"):
        cif_conv = Cif_conversion(tc.pdb_file)
        cif_conv.convert_cif_add_h()
        tc.pdb_file = cif_conv.pdb_file_path

    def check_model_file(pdb_file):
        fl = open(pdb_file, "r")
        all_file = fl.read()
        if "MODEL        1" in all_file:
            new_fl = open(pdb_file, "w")
            end_ind = all_file.index("ENDMDL")
            model_lines = all_file[:end_ind]
            new_fl.write(model_lines)
            new_fl.close()
            return pdb_file
        else:
            return None

    def format_pdb(pdb_file_path):
        parser = PDBParser(QUIET=True)
        structure = parser.get_structure("molecule", pdb_file_path)

        io = PDBIO()
        io.set_structure(structure)
        io.save(pdb_file_path)
        return pdb_file_path

    def initial_check(pdb_file_path):
        fl = open(pdb_file_path, "r")
        lines = fl.readlines()
        fl.close()
        for line in lines:
            if line.startswith("ATOM"):
                if line[-1].isalpha():
                    return None
                else:
                    pdb_file_path = format_pdb(pdb_file_path)
                    return pdb_file_path

    new_pdb = initial_check(tc.pdb_file)
    if new_pdb:
        tc.pdb_file = new_pdb
    new_pdb = check_model_file(tc.pdb_file)
    if new_pdb:
        tc.pdb_file = new_pdb

    if tc.REDUCE_BOOL:
        head, tail = os.path.split(tc.pdb_file)
        new_tail = f"{'.'.join(tail.split('.'))[:-1]}_h.{tail.split('.')[-1]}"
        new_pdb = os.path.join(head, new_tail)
        reduce_command_temp = REDUCE_COMMAND % (
            shlex.quote(tc.pdb_file),
            shlex.quote(new_pdb),
        )
        os.system(reduce_command_temp)
        tc.pdb_file = new_pdb
    parsed, lines = read_pdb(tc.pdb_file, False)

    chain_combinations = []
    for ind1, chain1 in enumerate(tc.chains_set_1):
        for ind2, chain2 in enumerate(tc.chains_set_2):
            if chain1 != chain2:
                try:
                    if (chain1, chain2) not in chain_combinations and (
                        chain2,
                        chain1,
                    ) not in chain_combinations:
                        range_chain_1 = tc.ranges_1[ind1]
                        range_chain_2 = tc.ranges_2[ind2]

                        chain_combinations.append((chain1, chain2))
                        chain_combinations.append((chain2, chain1))
                        (
                            chains_lines,
                            chains_mapping,
                            all_pdb_parsed_lines,
                            all_pdb_formatted_path,
                            compound_pdb_path,
                            chain1_pdb_path,
                            chain2_pdb_path,
                        ) = get_chains_ranges_lines(
                            parsed_lines=parsed,
                            ranges1=range_chain_1,
                            ranges2=range_chain_2,
                            chains=[chain1, chain2],
                            pdb_path=tc.pdb_file,
                        )
                        chain1_pdb_path, chain2_pdb_path, compound_pdb_path = (
                            chain_selection_pdbs_making(chain1, chain2, tc.pdb_file)
                        )

                        process(
                            tc.pdb_file,
                            [chain1, chain2],
                            chains_lines,
                            chains_mapping,
                            all_pdb_parsed_lines,
                            all_pdb_formatted_path,
                            compound_pdb_path,
                            chain1_pdb_path,
                            chain2_pdb_path,
                        )
                        _archive_naccess_outputs(
                            compound_pdb_path,
                            chain1_pdb_path,
                            chain2_pdb_path,
                            str(chain1),
                            str(chain2),
                        )
                except Exception as e:
                    print(f"[ERROR] Chain pair {chain1}/{chain2}: {e}", file=sys.stderr)

    end = time.time()
    print(end - start)

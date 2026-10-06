from backend.routes.data import _build_atom_pairs_response_from_rows


def _cation_pi_row():
    return {
        "resName1": "U",
        "resNum1": "104",
        "chain1": "A",
        "resName2": "ARG",
        "resNum2": "130",
        "chain2": "B",
        "frame": "2",
        "interactionType": "Cation-π interactions",
        "atom1": "Pi-Ring",
        "atom2": "NE",
        "distance": "3.87",
        "angle": "",
    }


def test_atom_pair_response_preserves_aggregated_residue_order():
    response = _build_atom_pairs_response_from_rows(
        [_cation_pi_row()], "U", "104", "A", "ARG", "130", "B", 10
    )

    frame_pair = response["atomPairsByFrame"]["2"][0]
    assert response["residuePair"]["id1"] == "U104_A"
    assert response["residuePair"]["id2"] == "ARG130_B"
    assert (frame_pair["atom1"], frame_pair["atom2"]) == ("Pi-Ring", "NE")
    assert frame_pair["atomPair"] == "Pi-Ring-NE"


def test_atom_pair_response_swaps_atoms_for_reversed_request_order():
    response = _build_atom_pairs_response_from_rows(
        [_cation_pi_row()], "ARG", "130", "B", "U", "104", "A", 10
    )

    frame_pair = response["atomPairsByFrame"]["2"][0]
    assert response["residuePair"]["id1"] == "ARG130_B"
    assert response["residuePair"]["id2"] == "U104_A"
    assert (frame_pair["atom1"], frame_pair["atom2"]) == ("NE", "Pi-Ring")
    assert frame_pair["atomPair"] == "NE-Pi-Ring"
